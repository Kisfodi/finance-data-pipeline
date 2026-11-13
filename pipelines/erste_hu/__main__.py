import argparse

from pipelines.common.cli import expand_globs
from pipelines.erste_hu.pipeline import run

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('files', nargs='+', help='raw CSV exports')
    parser.add_argument('--accounts', required=True, help='accounts.csv (account_number, alias)')
    parser.add_argument('--cards', required=True, help='cards.csv (card_ref, alias)')
    parser.add_argument('--out', default='data/clean/erste_hu', help='output folder for Parquet files')

    args = parser.parse_args()

    run(expand_globs(args.files), args.accounts, args.cards, args.out)


if __name__ == '__main__':
    main()