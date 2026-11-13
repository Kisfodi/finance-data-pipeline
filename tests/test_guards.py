import pandas as pd
import pytest

from pipelines.common.guards import assert_no_card_numbers, luhn_ok
from tests.factories import TEST_PAN


def frame(values: list[str], col: str = 'info', dtype: str = 'str') -> pd.DataFrame:
    return pd.DataFrame({col: pd.Series(values, dtype=dtype)})


@pytest.mark.parametrize('number, expected', [
    (TEST_PAN, True),
    ('4111111111111112', False),
    ('79927398713', True),   # textbook Luhn example
])
def test_luhn(number, expected):
    assert luhn_ok(number) is expected


@pytest.mark.parametrize('dtype', ['str', 'object', 'string[pyarrow]'])
def test_card_number_in_text_raises(dtype):
    with pytest.raises(ValueError, match=r"possible full card number in column\(s\) \['info'\]"):
        assert_no_card_numbers(frame([f'paid with {TEST_PAN} today'], dtype=dtype), 'fake.csv')


def test_message_names_column_but_not_number():
    with pytest.raises(ValueError) as exc:
        assert_no_card_numbers(frame([TEST_PAN]), 'fake.csv')
    assert TEST_PAN not in str(exc.value)


def test_only_offending_columns_are_named():
    df = pd.DataFrame({'clean': ['nothing here'], 'dirty': [TEST_PAN]}, dtype=str)
    with pytest.raises(ValueError, match=r"\['dirty'\]"):
        assert_no_card_numbers(df, 'fake.csv')


def test_skipped_column_is_not_checked():
    df = pd.DataFrame({'tid': [TEST_PAN], 'info': ['ok']}, dtype=str)
    assert_no_card_numbers(df, 'fake.csv', skip_columns=('tid',))


def test_skip_does_not_hide_other_columns():
    df = pd.DataFrame({'tid': ['x'], 'info': [TEST_PAN]}, dtype=str)
    with pytest.raises(ValueError):
        assert_no_card_numbers(df, 'fake.csv', skip_columns=('tid',))


@pytest.mark.parametrize('value', [
    '4111111111111112',             # 16 digits, fails Luhn
    '123456xxxxxx7890',             # bank-masked token
    '411111111111',                 # 12 digits, too short
    '14111111111111111',            # starts with 1
    '4111111111111111111111',       # longer than 19 digits
    '',
])
def test_values_that_are_not_card_numbers_pass(value):
    assert_no_card_numbers(frame([value]), 'fake.csv')
