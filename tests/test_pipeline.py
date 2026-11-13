from pathlib import Path

import pandas as pd
import pytest

from pipelines.common.schema import OUTPUT_COLS
from pipelines.erste_hu.pipeline import run
from tests.factories import EUR_ACCOUNT, HUF_ACCOUNT, HUF_CARD_REF, card_row, make_row, write_export


@pytest.fixture
def project(tmp_path: Path) -> dict[str, Path]:
    raw = tmp_path / 'raw'
    raw.mkdir()
    accounts = tmp_path / 'accounts.csv'
    accounts.write_text(f'account_number,alias\n{HUF_ACCOUNT},huf_main\n{EUR_ACCOUNT},eur_main\n', encoding='utf-8')
    cards = tmp_path / 'cards.csv'
    cards.write_text(f'card_ref,alias\n{HUF_CARD_REF},huf_card\n', encoding='utf-8')
    return {'raw': raw, 'accounts': accounts, 'cards': cards, 'out': tmp_path / 'clean'}


def run_project(p: dict[str, Path], files: list[Path]) -> None:
    run([str(f) for f in files], str(p['accounts']), str(p['cards']), str(p['out']))


def test_end_to_end_writes_one_parquet_per_export(project, capsys):
    huf = write_export(project['raw'], [card_row(amount='-189', info='SHOP vásár. 0.50 EUR 378.57'),
                                        make_row(partner_name='Landlord')])
    eur = write_export(project['raw'], [make_row(account_number=EUR_ACCOUNT, amount='-0,50', currency='EUR')],
                       account=EUR_ACCOUNT, sep=',', quote=True)
    run_project(project, [huf, eur])

    written = sorted(p.name for p in project['out'].glob('*.parquet'))
    assert written == ['eur_main_2026-09-01_2026-09-30.parquet', 'huf_main_2026-09-01_2026-09-30.parquet']

    huf_out = pd.read_parquet(project['out'] / 'huf_main_2026-09-01_2026-09-30.parquet')
    assert list(huf_out.columns) == OUTPUT_COLS
    assert len(huf_out) == 2
    assert int(huf_out['is_fx_payment'].sum()) == 1

    printed = capsys.readouterr().out
    assert HUF_ACCOUNT not in printed and EUR_ACCOUNT not in printed


def test_rerun_is_idempotent(project):
    huf = write_export(project['raw'], [card_row(), card_row(), make_row(partner_name='Landlord')])
    out_file = project['out'] / 'huf_main_2026-09-01_2026-09-30.parquet'

    run_project(project, [huf])
    first = pd.read_parquet(out_file)
    run_project(project, [huf])

    assert len(list(project['out'].glob('*.parquet'))) == 1
    pd.testing.assert_frame_equal(first, pd.read_parquet(out_file))


def test_card_statement_is_skipped(project, capsys):
    card_statement = project['raw'] / '123456______7890_2026-09-01_2026-09-30.csv'
    card_statement.write_text('not read\n', encoding='utf-16')
    run_project(project, [card_statement])

    assert not project['out'].exists() or not any(project['out'].glob('*.parquet'))
    assert 'skipped (card statement' in capsys.readouterr().out


def test_coverage_gap_is_printed_as_warning(project, capsys):
    aug = write_export(project['raw'], [make_row(booking_date='2026.08.10')], start='2026-08-01', end='2026-08-31')
    oct_ = write_export(project['raw'], [make_row(booking_date='2026.10.10')], start='2026-10-01', end='2026-10-31')
    run_project(project, [aug, oct_])

    assert 'WARNING coverage: huf_main: gap from 2026-09-01 to 2026-09-30' in capsys.readouterr().out


def test_failed_file_writes_nothing(project):
    bad = write_export(project['raw'], [make_row(amount='12a')])
    with pytest.raises(ValueError):
        run_project(project, [bad])
    assert not project['out'].exists() or not any(project['out'].glob('*.parquet'))
