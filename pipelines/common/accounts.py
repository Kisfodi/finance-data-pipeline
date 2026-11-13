from pathlib import Path

import pandas as pd

def load_accounts(path: str | Path) -> pd.DataFrame:
    # Strip spaces around names and values, so a stray space cannot break the account lookup
    acc = pd.read_csv(path, dtype=str).rename(columns=str.strip)
    acc = acc.apply(lambda col: col.str.strip())

    if not {'account_number', 'alias'} <= set(acc.columns):
        raise ValueError('accounts.csv needs the columns account_number and alias')

    if acc['account_number'].duplicated().any() or acc['alias'].duplicated().any():
        raise ValueError('accounts.csv contains duplicate rows for columns account_number and alias')

    return acc

def lookup_alias(account_number: str, accounts: pd.DataFrame, context: str='') -> str:
    alias_by_number = dict(zip(accounts['account_number'], accounts['alias']))

    if account_number not in alias_by_number:
        prefix = f'{context}: ' if context else ''
        raise KeyError(f'{prefix}account is not listed in accounts.csv')

    return alias_by_number[account_number]