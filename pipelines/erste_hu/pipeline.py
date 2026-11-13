from pathlib import Path

from pipelines.common.accounts import load_accounts, lookup_alias
from pipelines.common.cards import load_cards
from pipelines.common.coverage import find_coverage_issues
from pipelines.common.load import load_parquet
from pipelines.erste_hu.extract import extract, is_card_statement
from pipelines.erste_hu.transform import file_stem, transform

def run(files: list[str], accounts_path: str, cards_path: str, out_dir: str) -> None:
    accounts = load_accounts(accounts_path)
    cards = load_cards(cards_path)

    for f in files:

        if is_card_statement(Path(f)):
            print(f'{Path(f).name}: skipped (card statement; its payments are already in the account export)')
            continue

        raw = extract(f)
        stem = file_stem(lookup_alias(raw.account_number, accounts, raw.file_name), raw)
        cleaned = transform(raw, accounts, cards)
        out_file = load_parquet(cleaned, out_dir, stem)

        print(f'{out_file} ({len(cleaned)} rows, {int(cleaned["is_fx_payment"].sum())} FX)')

    for issue in find_coverage_issues(out_dir):
        print(f'WARNING coverage: {issue}')