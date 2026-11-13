

import re
from datetime import date, timedelta
from pathlib import Path

STEM_RE = re.compile(r'^(?P<alias>.+)_(?P<start>\d{4}-\d{2}-\d{2})_(?P<end>\d{4}-\d{2}-\d{2})')

def find_coverage_issues(clean_dir: str | Path) -> list[str]:

    spans_by_alias: dict[str, list[tuple[date, date]]] = {}

    for path in sorted(Path(clean_dir).glob('*.parquet')):
        m = STEM_RE.match(path.stem)

        if m:
            spans_by_alias.setdefault(m['alias'], []).append(
                (date.fromisoformat(m['start']), date.fromisoformat(m['end']))
            )

    issues = []

    for alias, spans in spans_by_alias.items():
        covered_until = None

        for start, end in spans:
            if covered_until is not None:
                if start <= covered_until:
                    issues.append(f'{alias}: overlap, a file starting {start} begins before {covered_until} (data covered twice; deduplicate on txn_key)')

                elif start > covered_until + timedelta(days=1):
                    issues.append(f'{alias}: gap from {covered_until + timedelta(days=1)} to {start + timedelta(days=-1)} (no export for these days)')

            covered_until = end if covered_until is None else max(covered_until, end)

    return issues