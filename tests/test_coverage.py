from pathlib import Path

from pipelines.common.coverage import find_coverage_issues


def touch(folder: Path, *stems: str) -> Path:
    # The check reads only file names, so empty files are enough
    for stem in stems:
        (folder / f'{stem}.parquet').touch()
    return folder


def test_consecutive_months_have_no_issues(tmp_path):
    touch(tmp_path, 'huf_main_2026-08-01_2026-08-31', 'huf_main_2026-09-01_2026-09-30')
    assert find_coverage_issues(tmp_path) == []


def test_gap_is_reported_with_its_dates(tmp_path):
    touch(tmp_path, 'huf_main_2026-08-01_2026-08-31', 'huf_main_2026-10-01_2026-10-31')
    assert find_coverage_issues(tmp_path) == ['huf_main: gap from 2026-09-01 to 2026-09-30 (no export for these days)']


def test_overlap_is_reported(tmp_path):
    touch(tmp_path, 'huf_main_2026-01-01_2026-12-31', 'huf_main_2026-09-01_2026-09-30')
    issues = find_coverage_issues(tmp_path)
    assert len(issues) == 1
    assert 'overlap' in issues[0]


def test_nested_ranges_do_not_create_false_gaps(tmp_path):
    # Year file plus months inside it, then the next year: overlaps only, no gap after September
    touch(tmp_path,
          'huf_main_2025-01-01_2025-12-31',
          'huf_main_2025-03-01_2025-03-31',
          'huf_main_2025-09-01_2025-09-30',
          'huf_main_2026-01-01_2026-12-31')
    issues = find_coverage_issues(tmp_path)
    assert len(issues) == 2
    assert all('overlap' in issue for issue in issues)


def test_accounts_are_checked_separately(tmp_path):
    touch(tmp_path, 'huf_main_2026-08-01_2026-08-31', 'eur_main_2026-09-01_2026-09-30')
    assert find_coverage_issues(tmp_path) == []


def test_other_files_are_ignored(tmp_path):
    touch(tmp_path, 'huf_main_2026-08-01_2026-08-31', 'notes')
    (tmp_path / 'huf_main_2026-10-01_2026-10-31.csv').touch()
    assert find_coverage_issues(tmp_path) == []


def test_empty_folder(tmp_path):
    assert find_coverage_issues(tmp_path) == []
