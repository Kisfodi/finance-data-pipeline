from pathlib import Path

import pytest

from pipelines.erste_hu.extract import detect_separator, extract, is_card_statement, parse_filename
from tests.factories import HUF_ACCOUNT, TEST_PAN, card_row, make_row, write_export


# --- file names ---

def test_parse_filename():
    assert parse_filename(Path(f'{HUF_ACCOUNT}_2026-09-01_2026-09-30.csv')) == (HUF_ACCOUNT, '2026-09-01', '2026-09-30')


def test_parse_filename_accepts_upper_case_extension():
    assert parse_filename(Path(f'{HUF_ACCOUNT}_2026-09-01_2026-09-30.CSV'))[0] == HUF_ACCOUNT


@pytest.mark.parametrize('name, message', [
    (f'{HUF_ACCOUNT}_2026-09-01_2026-09-30.xlsx', 'Not a CSV'),
    (f'{HUF_ACCOUNT}_2026-09-01_2026-09-30_1.csv', 'Unexpected name format'),
    (f'{HUF_ACCOUNT}_2026-09-01.csv', 'Unexpected name format'),
    (f'{HUF_ACCOUNT}_2026-09-30_2026-09-01.csv', 'Start date is after end date'),
    (f'{HUF_ACCOUNT}_2026-09-01_2026-09-31.csv', None),   # 31 September does not exist (message from datetime)
    # fromisoformat alone would accept these compact forms (Python 3.11+)
    (f'{HUF_ACCOUNT}_20260901_20260930.csv', 'Dates must be YYYY-MM-DD'),
    (f'{HUF_ACCOUNT}_2026-09-01_20260930.csv', 'Dates must be YYYY-MM-DD'),
    (f'{HUF_ACCOUNT}_2026-W36-1_2026-09-30.csv', 'Dates must be YYYY-MM-DD'),   # ISO week date
    (f'{HUF_ACCOUNT}_2026-9-1_2026-09-30.csv', 'Dates must be YYYY-MM-DD'),
])
def test_parse_filename_rejects_bad_names(name, message):
    with pytest.raises(ValueError, match=message):
        parse_filename(Path(name))


@pytest.mark.parametrize('name, expected', [
    ('123456______7890_2026-09-01_2026-09-30.csv', True),
    (f'{HUF_ACCOUNT}_2026-09-01_2026-09-30.csv', False),
])
def test_is_card_statement(name, expected):
    assert is_card_statement(Path(name)) is expected


# --- separators and reading ---

@pytest.mark.parametrize('sep, quote', [(';', False), (',', True), ('\t', False), (';', True)])
def test_detect_separator(tmp_path, sep, quote):
    path = write_export(tmp_path, [make_row()], sep=sep, quote=quote)
    assert detect_separator(path) == sep


def test_detect_separator_rejects_unknown_header(tmp_path):
    path = tmp_path / f'{HUF_ACCOUNT}_2026-09-01_2026-09-30.csv'
    path.write_text('a;b;c\n1;2;3\n', encoding='utf-16')

    with pytest.raises(ValueError, match='Unexpected separator format'):
        detect_separator(path)


def test_extract_reads_everything_as_strings(tmp_path):
    # Quoted comma-separated export with a decimal comma inside a quoted value
    rows = [make_row(amount='-0,50', currency='EUR'), make_row(amount='0012')]
    raw = extract(write_export(tmp_path, rows, sep=',', quote=True))

    assert raw.account_number == HUF_ACCOUNT
    assert (raw.start, raw.end) == ('2026-09-01', '2026-09-30')
    assert raw.df['Összeg'].tolist() == ['-0,50', '0012']   # no numeric coercion, leading zeros kept
    assert raw.df['Partner IBAN száma'].tolist() == ['', '']  # empty stays empty string, not NaN


def test_extract_header_has_no_bom(tmp_path):
    raw = extract(write_export(tmp_path, [make_row()]))
    assert not any(col.startswith('﻿') for col in raw.df.columns)


def test_extract_stops_on_full_card_number(tmp_path):
    path = write_export(tmp_path, [card_row(info=f'card {TEST_PAN} vásár.')])

    with pytest.raises(ValueError, match='possible full card number') as exc:
        extract(path)
    assert TEST_PAN not in str(exc.value)  # the message must never contain the number


def test_extract_allows_long_number_in_transaction_id(tmp_path):
    # Long transaction ids can pass Luhn by chance, so that column is skipped
    raw = extract(write_export(tmp_path, [make_row(transaction_id=TEST_PAN)]))
    assert len(raw.df) == 1
