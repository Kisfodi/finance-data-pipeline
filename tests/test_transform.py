import pandas as pd
import pytest

from pipelines.common.schema import OUTPUT_COLS
from pipelines.erste_hu.transform import transform
from tests.factories import (
    EUR_ACCOUNT, HUF_ACCOUNT, NARROW_NBSP, NBSP, UNLISTED_CARD_TOKEN,
    card_row, make_accounts, make_cards, make_raw, make_row,
)


def run(rows, **raw_kwargs) -> pd.DataFrame:
    return transform(make_raw(rows, **raw_kwargs), make_accounts(), make_cards())


# --- output contract and privacy ---

def test_output_has_exactly_the_contract_columns():
    out = run([make_row()])
    assert list(out.columns) == OUTPUT_COLS


def test_output_has_no_pii_or_account_numbers():
    out = run([card_row(user_name='Test User', partner_account='11111111-22222222-33333333',
                        partner_bank_code='117')])
    text = out.astype(str).to_string()

    assert 'Test User' not in text
    assert HUF_ACCOUNT not in text
    assert HUF_ACCOUNT.replace('-', '') not in text
    assert '11111111-22222222-33333333' not in text
    assert 'xxxxxx' not in text  # masked card token comes out only as an alias


def test_alias_and_source_file_use_alias_not_account_number():
    out = run([make_row()])
    assert out.loc[0, 'account_alias'] == 'huf_main'
    assert out.loc[0, 'source_file'] == 'huf_main_2026-09-01_2026-09-30'


# --- amounts ---

@pytest.mark.parametrize('text, expected', [
    (f'-12{NBSP}345', -12345.0),          # HUF thousands separator: no-break space
    (f'-1{NARROW_NBSP}234{NARROW_NBSP}567', -1234567.0),
    ('-12 345', -12345.0),                # normal space
    ('1500', 1500.0),
    ('-0,50', -0.5),                      # EUR decimal comma
    (f'1{NBSP}234,56', 1234.56),
])
def test_amount_parsing(text, expected):
    out = run([make_row(amount=text)])
    assert out.loc[0, 'amount'] == expected


@pytest.mark.parametrize('text', ['12a', '', '1.234,56', '--5', '1,2,3'])
def test_unexpected_amount_format_raises(text):
    with pytest.raises(ValueError, match='Unexpected amount format'):
        run([make_row(amount=text)])


# --- dates ---

def test_booking_date_outside_file_name_range_raises():
    with pytest.raises(ValueError, match='outside the date range'):
        run([make_row(booking_date='2026.10.01')])


def test_spend_date_uses_transaction_date_and_falls_back_to_booking_date():
    # Card purchase on 31 Aug, booked 1 Sep: belongs to the September file but is August spending
    card = card_row(booking_date='2026.09.01', transaction_ts='2026.08.31 23:10:00')
    transfer = make_row(booking_date='2026.09.02', partner_name='Landlord')
    out = run([card, transfer]).set_index('partner_name')

    assert out.loc['Test Shop', 'spend_date'] == pd.Timestamp('2026-08-31')
    assert out.loc['Test Shop', 'transaction_ts'] == pd.Timestamp('2026-08-31 23:10:00')
    assert out.loc['Landlord', 'spend_date'] == pd.Timestamp('2026-09-02')
    assert pd.isna(out.loc['Landlord', 'transaction_ts'])


# --- FX ---

def test_fx_payment_is_parsed():
    # 0.50 EUR at 378.57 HUF/EUR = 189.285 HUF; the bank books -189
    out = run([card_row(amount='-189', info='TEST SHOP WIEN vásár. 0.50 EUR 378.57')])
    row = out.loc[0]

    assert row['is_fx_payment']
    assert row['fx_orig_amount'] == 0.5
    assert row['fx_orig_currency'] == 'EUR'
    assert row['fx_rate'] == 378.57
    assert row['fx_amount_ok']


def test_non_fx_rows_have_real_missing_values_not_empty_strings():
    out = run([card_row()])
    row = out.loc[0]

    assert not row['is_fx_payment']
    assert pd.isna(row['fx_orig_amount'])
    assert pd.isna(row['fx_orig_currency'])
    assert pd.isna(row['fx_rate'])
    assert pd.isna(row['fx_amount_ok'])


def test_fx_amount_that_does_not_match_raises():
    with pytest.raises(ValueError, match='FX parsing check failed'):
        run([card_row(amount='-500', info='TEST SHOP WIEN vásár. 0.50 EUR 378.57')])


def test_fx_tail_in_the_account_currency_raises():
    with pytest.raises(ValueError, match='FX parsing check failed'):
        run([card_row(amount='-189', info='TEST SHOP vásár. 0.50 HUF 378.57')])


# --- cards ---

def test_card_alias_known_unknown_and_none():
    rows = [
        card_row(partner_name='Known Card Shop'),
        card_row(token=UNLISTED_CARD_TOKEN, partner_name='Unlisted Card Shop'),
        make_row(partner_name='No Card'),
    ]
    with pytest.warns(UserWarning, match='999999-0000'):
        out = run(rows).set_index('partner_name')

    assert out.loc['Known Card Shop', 'card_alias'] == 'huf_card'
    assert out.loc['Unlisted Card Shop', 'card_alias'] == 'unknown_card'
    assert pd.isna(out.loc['No Card', 'card_alias'])


# --- internal transfers ---

def test_internal_transfer_flag():
    own_iban = 'HU42' + EUR_ACCOUNT.replace('-', '')
    rows = [
        make_row(partner_name='Own EUR Account', partner_iban=own_iban),
        make_row(partner_name='Someone Else', partner_iban='HU42' + '9' * 24),
        make_row(partner_name='No IBAN'),
    ]
    out = run(rows).set_index('partner_name')

    assert out.loc['Own EUR Account', 'is_internal_transfer']
    assert not out.loc['Someone Else', 'is_internal_transfer']
    assert not out.loc['No IBAN', 'is_internal_transfer']


# --- keys ---

def test_identical_purchases_are_kept_with_different_keys():
    out = run([card_row(), card_row()])
    assert len(out) == 2
    assert out['txn_key'].is_unique


def test_keys_are_stable_across_reruns():
    rows = [card_row(), card_row(), make_row(partner_name='Landlord')]
    assert run(rows)['txn_key'].tolist() == run(rows)['txn_key'].tolist()


def test_overlapping_exports_give_the_same_keys():
    # The same September rows inside a monthly and a yearly export must match, so dbt can de-duplicate
    rows = [card_row(), card_row(), make_row(partner_name='Landlord')]
    monthly = run(rows)
    yearly = run(rows, start='2026-01-01', end='2026-12-31')

    assert set(monthly['txn_key']) == set(yearly['txn_key'])


def test_key_does_not_depend_on_row_order_of_different_transactions():
    a = card_row(partner_name='Shop A')
    b = make_row(partner_name='Shop B')
    keys_ab = run([a, b]).set_index('partner_name')['txn_key']
    keys_ba = run([b, a]).set_index('partner_name')['txn_key']

    pd.testing.assert_series_equal(keys_ab.sort_index(), keys_ba.sort_index())


# --- accounts ---

def test_account_number_inside_file_must_match_file_name():
    with pytest.raises(ValueError, match='differs from the file name'):
        run([make_row(account_number=EUR_ACCOUNT)])


def test_unknown_account_raises():
    unknown = '12345678-00000009-00000000'
    with pytest.raises(KeyError, match='not listed in accounts.csv'):
        run([make_row(account_number=unknown)], account=unknown)
