import warnings

import pandas as pd

from pipelines.common.accounts import lookup_alias
from pipelines.common.cards import UNKNOWN_CARD_ALIAS
from pipelines.common.keys import add_txn_key
from pipelines.common.schema import OUTPUT_COLS
from pipelines.erste_hu.extract import RawExport
from pipelines.erste_hu.settings import AMOUNT_RE, CARD_RE, COLUMN_MAP, DROP_COLUMNS, FX_RE, KEY_COLS


def parse_amount(s: pd.Series):
    clean = s.str.replace('[\\s\u00a0\u202f]', '', regex=True).str.replace(',', '.', regex=False)

    bad = ~clean.str.match(AMOUNT_RE)
    if bad.any():
        raise ValueError(f'Unexpected amount format in {bad.sum()} rows, e.g. {s[bad].iloc[0]!r}')

    return pd.to_numeric(clean)

def parse_types(df: pd.DataFrame) -> pd.DataFrame:

    df['amount'] = parse_amount(df['amount'])#.round(2)
    df['booking_date'] = pd.to_datetime(df['booking_date'], format='%Y.%m.%d')
    df['transaction_ts'] = pd.to_datetime(df['transaction_ts'].replace('', pd.NA), format='%Y.%m.%d %H:%M:%S')
    df['spend_date'] = df['transaction_ts'].dt.normalize().fillna(df['booking_date'])

    return df

def add_fx_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Foreign currency details
    fx = df['booking_info'].str.extract(FX_RE)
    df['fx_orig_amount'] = pd.to_numeric(fx['fx_orig_amount'])
    df['fx_orig_currency'] = fx['fx_orig_currency']
    df['fx_rate'] = pd.to_numeric(fx['fx_rate'])
    df['is_fx_payment'] = df['fx_rate'].notna()

    implied = df['fx_orig_amount'] * df['fx_rate']
    tol = 1 + 0.005 * df['fx_orig_amount']

    ok = ((df['amount'].abs() - implied).abs() <= tol).astype('boolean').where(df['is_fx_payment'])
    df['fx_amount_ok'] = ok

    same_currency = df['fx_orig_currency'].eq(df['currency'])
    if ok.eq(False).any() or same_currency.any():
        raise ValueError("FX parsing check failed: booking_info tail does not match the amount. The text format may have changed.")

    return df

def add_card_alias(df: pd.DataFrame, cards: pd.DataFrame, file_name: str) -> pd.DataFrame:

    c = df['booking_info'].str.extract(CARD_RE)
    ref = c['card_first6'] + '-' + c['card_last4']

    alias = ref.map(dict(zip(cards['card_ref'], cards['alias']))).astype(object)
    unknown = ref.notna() & alias.isna()

    if unknown.any():
        alias[unknown] = UNKNOWN_CARD_ALIAS
        warnings.warn(f'{file_name}: {int(unknown.sum())} payment(s) with cards {sorted(set(ref[unknown]))} '
                      f'not in cards.csv, labelled {UNKNOWN_CARD_ALIAS}'
                      f'Add them them and re-run the pipeline')
        # raise ValueError(f'Unknown card(s) {sorted(set(ref[unknown]))}: add them to cards.csv')

    df['card_alias'] = alias

    return df

def add_internal_transfer_flag(df: pd.DataFrame, accounts: pd.DataFrame) -> pd.DataFrame:
    own = {n.replace('-', '') for n in accounts['account_number']}
    df['is_internal_transfer'] = df['partner_iban'].str[4:].isin(own)

    return df

def check_booking_dates(df: pd.DataFrame, raw: RawExport) -> None:
    outside = ~df['booking_date'].between(pd.Timestamp(raw.start), pd.Timestamp(raw.end))

    if outside.any():
        raise ValueError(f'{raw.file_name}: {int(outside.sum())} booking date(s) outside the date range in the file name')

def file_stem(alias: str, raw: RawExport) -> str:
    return f'{alias}_{raw.start}_{raw.end}'

def transform(raw: RawExport, accounts: pd.DataFrame, cards: pd.DataFrame) -> pd.DataFrame:

    alias = lookup_alias(raw.account_number, accounts)
    df = raw.df.rename(columns=COLUMN_MAP)

    if set(df['account_number']) - {raw.account_number}:
        raise ValueError(f'{raw.file_name}: account number inside file differs from the file name')

    df = parse_types(df)
    check_booking_dates(df, raw)
    df = add_fx_columns(df)
    df = add_card_alias(df, cards, raw.file_name)
    df = df.replace("", pd.NA).drop(columns=DROP_COLUMNS)
    df = add_internal_transfer_flag(df, accounts)
    df = add_txn_key(df, KEY_COLS)

    df['account_alias'] = alias
    df['source_file'] = file_stem(alias, raw)

    df = df.sort_values(['booking_date', 'transaction_ts', 'txn_key']).reset_index(drop=True)

    if not df['txn_key'].is_unique:
        raise ValueError('txn_key collision')

    return df[OUTPUT_COLS]