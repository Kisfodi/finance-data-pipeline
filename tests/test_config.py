from pathlib import Path

import pytest

from pipelines.common.accounts import load_accounts, lookup_alias
from pipelines.common.cards import load_cards
from pipelines.common.cli import expand_globs
from tests.factories import EUR_ACCOUNT, HUF_ACCOUNT


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding='utf-8')
    return path


# --- accounts ---

def test_load_accounts_strips_spaces(tmp_path):
    path = write(tmp_path / 'accounts.csv',
                 f'account_number , alias\n {HUF_ACCOUNT},huf_main \n{EUR_ACCOUNT} , eur_main\n')
    acc = load_accounts(path)

    assert list(acc.columns) == ['account_number', 'alias']
    assert lookup_alias(HUF_ACCOUNT, acc) == 'huf_main'
    assert lookup_alias(EUR_ACCOUNT, acc) == 'eur_main'


def test_load_accounts_rejects_duplicates_that_differ_only_by_spaces(tmp_path):
    path = write(tmp_path / 'accounts.csv', f'account_number,alias\n{HUF_ACCOUNT},main\n{EUR_ACCOUNT}, main\n')
    with pytest.raises(ValueError, match='duplicate'):
        load_accounts(path)


def test_load_accounts_requires_columns(tmp_path):
    path = write(tmp_path / 'accounts.csv', f'number,alias\n{HUF_ACCOUNT},huf_main\n')
    with pytest.raises(ValueError, match='needs the columns'):
        load_accounts(path)


def test_lookup_alias_unknown_account_names_context_not_number(tmp_path):
    acc = load_accounts(write(tmp_path / 'accounts.csv', f'account_number,alias\n{HUF_ACCOUNT},huf_main\n'))
    with pytest.raises(KeyError, match='export.csv') as exc:
        lookup_alias(EUR_ACCOUNT, acc, context='export.csv')
    assert EUR_ACCOUNT not in str(exc.value)


# --- cards ---

def test_load_cards_strips_spaces(tmp_path):
    cards = load_cards(write(tmp_path / 'cards.csv', 'card_ref, alias\n123456-7890 , huf_card\n'))
    assert cards.to_dict('records') == [{'card_ref': '123456-7890', 'alias': 'huf_card'}]


def test_load_cards_rejects_duplicate_alias(tmp_path):
    path = write(tmp_path / 'cards.csv', 'card_ref,alias\n123456-7890,card\n123456-1111, card\n')
    with pytest.raises(ValueError, match='unique'):
        load_cards(path)


def test_load_cards_requires_columns(tmp_path):
    with pytest.raises(ValueError, match='needs columns'):
        load_cards(write(tmp_path / 'cards.csv', 'card,alias\n123456-7890,huf_card\n'))


# --- command line globs ---

def test_expand_globs_sorts_and_removes_duplicates(tmp_path):
    for name in ('b.csv', 'a.csv'):
        (tmp_path / name).touch()
    pattern = str(tmp_path / '*.csv')

    assert [Path(f).name for f in expand_globs([pattern, pattern])] == ['a.csv', 'b.csv']


def test_expand_globs_fails_when_nothing_matches(tmp_path):
    with pytest.raises(SystemExit, match='No files match'):
        expand_globs([str(tmp_path / '*.csv')])
