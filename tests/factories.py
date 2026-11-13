"""Fabricated test data only. Never put real account numbers, card numbers, names or transactions here."""

from pathlib import Path

import pandas as pd

from pipelines.erste_hu.extract import RawExport
from pipelines.erste_hu.settings import COLUMN_MAP

HUF_ACCOUNT = '12345678-00000000-12345678'
EUR_ACCOUNT = '12345678-00000002-87654321'

# Bank-masked card token as it appears at the start of booking info, and its card_ref
HUF_CARD_TOKEN = '123456xxxxxx7890'
HUF_CARD_REF = '123456-7890'
UNLISTED_CARD_TOKEN = '999999xxxxxx0000'

# Public test card number (Visa); passes the Luhn check, belongs to no one
TEST_PAN = '4111111111111111'

NBSP = ' '
NARROW_NBSP = ' '

ENGLISH_TO_HUNGARIAN = {english: hungarian for hungarian, english in COLUMN_MAP.items()}


def make_row(**overrides: str) -> dict[str, str]:
    """One export row with English keys; every value is a string, as read_csv(dtype=str) gives."""
    row = {
        'user_name': 'Test User',
        'account_number': HUF_ACCOUNT,
        'booking_date': '2026.09.15',
        'amount': '-1000',
        'currency': 'HUF',
        'partner_name': 'Test Shop',
        'partner_iban': '',
        'partner_account': '',
        'partner_bank_code': '',
        'booking_info': '',
        'transaction_id': '',
        'transaction_ts': '',
    }
    unknown = set(overrides) - set(row)
    if unknown:
        raise KeyError(f'make_row: unknown fields {unknown}')
    row.update(overrides)
    return row


def card_row(token: str = HUF_CARD_TOKEN, info: str = 'TEST SHOP BUDAPEST vásár.', **overrides: str) -> dict[str, str]:
    """A card payment: masked card token at the start of booking info, transaction time filled."""
    defaults = {
        'booking_info': f'{token} {info}',
        'transaction_ts': '2026.09.14 18:30:00',
    }
    return make_row(**(defaults | overrides))


def make_df(rows: list[dict[str, str]]) -> pd.DataFrame:
    """Rows -> DataFrame with the Hungarian column names that extract() returns."""
    df = pd.DataFrame(rows, columns=list(ENGLISH_TO_HUNGARIAN), dtype=str)
    return df.rename(columns=ENGLISH_TO_HUNGARIAN)


def make_raw(rows: list[dict[str, str]], account: str = HUF_ACCOUNT,
             start: str = '2026-09-01', end: str = '2026-09-30') -> RawExport:
    return RawExport(df=make_df(rows), account_number=account, start=start, end=end,
                     file_name=f'{account}_{start}_{end}.csv')


def make_accounts() -> pd.DataFrame:
    return pd.DataFrame({'account_number': [HUF_ACCOUNT, EUR_ACCOUNT], 'alias': ['huf_main', 'eur_main']}, dtype=str)


def make_cards() -> pd.DataFrame:
    return pd.DataFrame({'card_ref': [HUF_CARD_REF], 'alias': ['huf_card']}, dtype=str)


def write_export(folder: Path, rows: list[dict[str, str]], account: str = HUF_ACCOUNT,
                 start: str = '2026-09-01', end: str = '2026-09-30', sep: str = ';', quote: bool = False) -> Path:
    """Write rows as a George-style export: UTF-16 with BOM, Hungarian header, every column."""
    def fmt(value: str) -> str:
        return f'"{value}"' if quote else value

    header = sep.join(fmt(col) for col in ENGLISH_TO_HUNGARIAN.values())
    lines = [header] + [sep.join(fmt(row[col]) for col in ENGLISH_TO_HUNGARIAN) for row in rows]

    path = folder / f'{account}_{start}_{end}.csv'
    path.write_text('\n'.join(lines) + '\n', encoding='utf-16')
    return path
