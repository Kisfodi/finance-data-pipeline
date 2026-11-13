
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from pipelines.common.guards import assert_no_card_numbers
from pipelines.erste_hu.settings import CARD_STATEMENT_NAME_RE, COLUMN_MAP, FILE_DATE_RE, PAN_SKIP_COLUMNS

@dataclass(frozen=True)
class RawExport:
    df: pd.DataFrame
    account_number: str
    start: str
    end: str
    file_name: str

def is_card_statement(path: Path) -> bool:
    return bool(CARD_STATEMENT_NAME_RE.match(path.name))

def parse_filename(path: Path) -> tuple[str, str, str]:

    if path.suffix.lower() != '.csv':
        raise ValueError(f'Not a CSV file: {path.name}')

    path_parts = path.stem.split('_')

    if len(path_parts) != 3:
        raise ValueError(f'Unexpected name format: {path.name}')

    acct, start, end = path_parts

    if not (FILE_DATE_RE.fullmatch(start) and FILE_DATE_RE.fullmatch(end)):
        raise ValueError(f'Dates must be YYYY-MM-DD: {path.name}')

    if date.fromisoformat(start) > date.fromisoformat(end):
        raise ValueError(f'Start date is after end date: {path.name}')

    return acct, start, end

def detect_separator(path: Path) -> str:

    with open(path, encoding='utf-16') as fh:
        header = fh.readline().strip()

        for sep in (',', ';', '\t'):
            if {c.strip().strip('"') for c in header.split(sep)} == set(COLUMN_MAP):
                return sep

        raise ValueError(f'Unexpected separator format: {path.name}')

def extract(path: str | Path) -> RawExport:

    path = Path(path)
    acct, start, end = parse_filename(path)

    df = pd.read_csv(path, sep=detect_separator(path), encoding='utf-16', dtype=str, keep_default_na=False)

    missing, extra = set(COLUMN_MAP) - set(df.columns), set(df.columns) - set(COLUMN_MAP)
    if missing or extra:
        raise ValueError(f'Schema changed. missing={missing}, extra={extra}')

    assert_no_card_numbers(df, path.name, PAN_SKIP_COLUMNS)

    return RawExport(df=df, account_number=acct, start=start, end=end, file_name=path.name)