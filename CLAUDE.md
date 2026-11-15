# Finance Data Pipeline

Personal data-engineering project: turn my own Erste Bank Hungary (George) CSV exports into clean, typed data, then analyse it. I am a data science / ML student and use this to practice a realistic pipeline end to end. The data is real personal financial data, so privacy is a hard constraint, not a nice-to-have.

## Goals

- Build an end-to-end pipeline on my own data: raw George CSV -> cleaned Parquet -> DuckDB + dbt -> marts -> dashboard.
- Questions to answer: monthly spend by category and currency; income vs spending (internal transfers excluded); recurring payments; whether paying foreign purchases from the HUF account instead of the EUR account was worse (FX markup against a reference rate).
- Practice good habits: strict extract/transform/load separation, one package per source, a fixed output schema, fail-loud validation, idempotent re-runs, tests.
- Hard rule: no real account numbers, card numbers, transactions or names in Git, logs, tests, examples or anything shared. Use made-up values such as `12345678-00000000-12345678` and `123456-7890`.

## Current status

Done (manually verified on September 2026 exports of one HUF and one EUR account):

- `pipelines/erste_hu`: extract, transform, load for George exports, run as a module.
- Cleaning: UTF-16 decoding, per-file delimiter detection, Hungarian -> English columns, amount/date parsing, PII columns dropped, FX details parsed, card alias, internal-transfer flag, stable `txn_key`.
- Checks: schema drift, account number in file vs file name, booking dates inside the file-name range, FX amount consistency, full-card-number guard, duplicate config rows, coverage gaps/overlaps (warning).
- Regression baseline for September 2026: HUF file 44 rows (10 FX payments), EUR file 9 rows (no FX). Re-run after changes and compare with `pd.testing.assert_frame_equal`.
- Since then also run on 9 real exports (yearly 2024-2026 plus monthly September and October 2026, both accounts, two cards) with strict mode and no warnings; outputs identical to `data/clean` on pandas 3.1.1.

Also done:
- Git repository with `.gitignore` (no remote yet; I commit by hand).
- Dependencies declared in `pyproject.toml` with dependency groups.
- Automated tests: pytest suite in `tests/`, fabricated data only, covering transform, extract, guards, coverage, config loaders and an end-to-end pipeline run.
- DuckDB + dbt (roadmap step 1): source `erste_hu.transactions` over all cleaned Parquet files, staging model `stg_erste_hu__transactions` (de-duplicated on `txn_key`, keeping the copy from the shortest export; `amount` and `fx_orig_amount` as `DECIMAL(18,2)`, `booking_date` and `spend_date` as `DATE`), materialized as a table in `data/warehouse/finance.duckdb`, with an enforced contract on all 18 columns. dbt tests: `txn_key` unique and not null, `account_alias` not null, currency in (EUR, HUF), singular test for `unknown_card` (warn). `dbt build` passes; row count after de-duplication equals the number of distinct `txn_key`s in the source; stored column types match the contract.

In progress: finishing roadmap step 1 (see open step 1: warn check and learning note).

Not done yet: categories, marts, FX-markup analysis, dashboard, orchestration, CI.

Not exercised on real data yet: `is_internal_transfer` (no own-account transfers in the exports so far; covered only by tests).

## File structure

```
finance_pipeline/
  CLAUDE.md
  LEARNING.md                   # my learning log, one section per roadmap step (written by me)
  .gitignore                    # data/, real config CSVs, any *.csv / *.parquet / *.duckdb / *.ipynb, .env, .venv/, caches, .idea/
  pyproject.toml                # dependencies, dependency groups, pytest settings
  uv.lock                       # exact tested versions
  dbt_project.yml               # dbt project: profile name, test-paths, staging materialized as table
  profiles.yml                  # dbt connection: DuckDB file path only, no secrets (committed)
  models/
    staging/erste_hu/
      _erste_hu__sources.yml    # source erste_hu.transactions -> external_location data/clean/erste_hu/*.parquet
      stg_erste_hu__transactions.sql   # CTEs: source -> with_file_span -> deduplicated -> typed
      stg_erste_hu__transactions.yml   # enforced contract (all columns with data_type) and column tests
  dbt_tests/                    # dbt singular tests (not tests/, which is pytest)
    assert_card_alias_not_unknown.sql
    schema.yml                  # severity: warn for the singular test
  target/, logs/                # dbt output, gitignored
  config/
    accounts.example.csv        # account_number (8-8-8 with hyphens), alias   -> real file: accounts.csv (gitignored)
    cards.example.csv           # card_ref (first6-last4), alias               -> real file: cards.csv (gitignored)
  data/                         # gitignored entirely
    raw/erste_hu/               # exports exactly as George produced them, never edited
    clean/erste_hu/             # <alias>_<start>_<end>.parquet, one per raw file
    warehouse/finance.duckdb    # dbt output; rebuildable from clean/, no backup needed
  pipelines/
    common/                     # source-independent pieces
      accounts.py               # load_accounts, lookup_alias
      cards.py                  # load_cards, UNKNOWN_CARD_ALIAS
      cli.py                    # expand_globs
      coverage.py               # find_coverage_issues (gaps/overlaps from file names)
      guards.py                 # assert_no_card_numbers (Luhn check)
      keys.py                   # add_txn_key
      load.py                   # load_parquet
      schema.py                 # OUTPUT_COLS, the output contract
    erste_hu/                   # everything specific to George
      settings.py               # COLUMN_MAP, DROP_COLUMNS, KEY_COLS, regexes
      extract.py                # RawExport, parse_filename, detect_separator, extract, is_card_statement
      transform.py              # pure transform and its helpers
      pipeline.py               # run(): extract -> transform -> load, then coverage warnings
      __main__.py               # command line
  tests/                        # pytest, fabricated data only
    factories.py                # fake rows, accounts, cards; write_export() writes a UTF-16 George-style file
    test_transform.py           # amounts, dates, FX, cards, internal transfers, keys, privacy of the output
    test_extract.py             # file names, separators, reading as strings, card guard inside extract
    test_guards.py              # assert_no_card_numbers, luhn_ok
    test_coverage.py            # find_coverage_issues
    test_config.py              # load_accounts, load_cards, expand_globs
    test_pipeline.py            # end to end in a temporary folder
```

Dependency rule: sources import from `common`; `common` never imports from a source.

## Commands

Run from the project root (running from another folder gives `ModuleNotFoundError`):

```
uv run python -m pipelines.erste_hu "data/raw/erste_hu/*.csv" --accounts config/accounts.csv --cards config/cards.csv --out data/clean/erste_hu
```

- Strict mode (warnings become errors, useful for CI): add `-W error::UserWarning` after `python`.
- Tests: `uv run pytest` (settings in `pyproject.toml`: tests in `tests/`, project root on the import path, any unexpected warning fails a test).
- dbt, also from the project root (relative paths in `profiles.yml` and the source location resolve from where dbt runs):
  - `uv run dbt debug`: check profile and connection.
  - `uv run dbt build`: build models and run dbt tests.
  - `uv run dbt show --select <model>` or `--inline "<sql with {{ ref(...) }}>"`; add `--output json` for untruncated values. Prefer aggregates when sharing output.
- Dependencies live in `pyproject.toml` as minimum versions; `uv.lock` holds the exact tested versions (Python 3.14.7, pandas 3.1.1, pyarrow 26.0.1, duckdb 2.0.0, dbt-core 1.12.7, dbt-duckdb 1.11.1). Upgrade on purpose with `uv lock --upgrade-package <name>`, then re-check the regression baseline.
  - Main: `pandas`, `pyarrow` (pipeline), `duckdb`, `dbt-duckdb` (warehouse). dbt-core 2.0 exists only as a release candidate; stay on 1.x until 2.0 and a matching `dbt-duckdb` are stable.
  - Group `dev` (installed by default): `pytest`.
  - Group `analysis` (notebooks and plots, not used by the pipeline): `numpy`, `matplotlib`, `seaborn`, `ipykernel`. Install with `uv sync --group analysis`; a plain `uv sync` removes them again.
- The environment is Windows with uv and PyCharm.

## Decisions and why

Source and raw data
- Manual George CSV exports for now. There is no official personal API, and scraping would mean handing my login to third-party code. Later option: PSD2 aggregator (Enable Banking), whose consent expires periodically, so it must fail loudly.
- Raw files are never edited or pre-converted (no find/replace of delimiters). Export all columns and drop what is not needed in code: the George column picker cannot be automated. Back up `data/raw/` because old periods may not be re-exportable.
- Filenames are strict: `<account>_<start>_<end>.csv`, dates exactly `YYYY-MM-DD` and valid, start <= end. The format is checked with `FILE_DATE_RE` before `date.fromisoformat`, because since Python 3.11 `fromisoformat` also accepts compact forms like `20260901`, which would give an output name the coverage check cannot read. Suffixes like `_1` or `_e7a763` only appeared in the chat's upload area and are not real.

Parsing
- Read with `encoding='utf-16'` (not `utf-16-le`, which leaves a BOM in the first header). The `\x00` characters seen earlier were just UTF-16 read as the wrong encoding.
- Read everything as strings (`dtype=str, keep_default_na=False`) and parse afterwards, so nothing is silently coerced.
- The delimiter is detected per file by splitting the header into exactly the expected column names (comma, semicolon or tab). Exports differ: quoted or not, comma or semicolon. Quoting is left to pandas. Unquoted text containing the delimiter fails loudly with a ParserError, and a shifted column would fail the account-number check.
- Amounts: strip every space type (normal, nbsp ` `, narrow nbsp ` `), decimal comma -> dot, validate with a regex, then `to_numeric`. HUF uses nbsp thousands separators and no decimals; EUR uses a decimal comma. Never sum HUF and EUR: keep the currency column.
- Regex rule for pandas `.str` methods: the whitespace pattern must be a non-raw string `'[\\s  ]'`. With pyarrow installed, pandas 3 uses Arrow strings (RE2): no `\u` escapes, `\s` is ASCII-only, no lookarounds. A raw `r'[\s ...]'` crashes there. A raw `\\s` also never matches spaces.
- Columns are renamed with a name-keyed dict, not by position, so reordering is harmless; any missing or extra column raises.

Columns, privacy, output
- Dropped: user name (PII), partner bank code (always empty), partner account (same account as the IBAN, in domestic format), booking info (card digits) after FX and card alias are parsed out of it.
- Output has aliases only (`config/accounts.csv`, `config/cards.csv`), never account or card numbers. `source_file` is the output stem, which has no account number either.
- Parquet output: keeps types, DuckDB reads it directly. Amount stays float64; cast to `DECIMAL(18,2)` and dates to `date` in the dbt staging model.
- `OUTPUT_COLS` in `common/schema.py` is a contract with the dbt models. Every bank source must return exactly these columns.
- `partner_iban` is third-party personal data; decide before sharing any output.

FX
- FX tail of booking info on foreign card payments: `... vásár. 0.50 EUR 378.57` = original amount, original currency, rate (HUF per 1 unit). Parsed into `fx_orig_amount`, `fx_orig_currency`, `fx_rate`, plus `is_fx_payment`; real NaN on other rows, not empty strings.
- The parse is checked: `|amount|` must equal original amount x rate within `1 + 0.5% of original`. A format change makes the run fail instead of producing wrong numbers.

Keys and dates
- `txn_key` = sha256 of account number, booking date, amount, currency, partner, transaction time + an occurrence counter, first 16 hex characters. The bank gives no unique id for card payments, and identical purchases on one day are legitimate, so no blind de-duplication. Built from the real account number so it survives alias renames.
- Overlapping exports (for example yearly + quarterly) give identical keys, so de-duplicate on `txn_key` downstream in dbt (done in staging; see the dbt section).
- Dates: `booking_date`, `transaction_ts` (Europe/Budapest local, naive, empty for non-card rows), `spend_date` = transaction date, falling back to booking date. Exports are cut by booking date, so a purchase can fall before the range start. Month totals by `spend_date` are final only after the next month's file is loaded: incremental models must reprocess the previous month.
- Internal transfers: `is_internal_transfer` is true when the partner IBAN minus its first 4 characters equals one of my own account numbers (hyphens removed). Own-account transfers must not count as spending.

Cards
- Card statement exports repeat card payments already in the account export (verified: all 39 rows matched on time, amount, booking date and partner; the same card pays from both accounts). Loading them would double-count, so files named like `123456______7890_<start>_<end>.csv` (`*` became `_`) are skipped with a message.
- Card info comes from the bank-masked token at the start of booking info (`123456xxxxxx7890`) -> `card_ref` `first6-last4` -> `card_alias` via `config/cards.csv`.
- Card missing from `cards.csv` -> label `unknown_card` plus a `UserWarning`, not an error: only a label is missing, and adding the card and re-running fixes it. No card involved stays NA, so the two cases remain distinguishable.
- `assert_no_card_numbers` in extract stops the run on any text column holding a 13-19 digit number starting with 2-6 that passes Luhn (transaction id column skipped, because long ids pass Luhn by chance). The message names columns, never the number.
- If card statements are ever needed as a source: parse the name with `ref, start, end = stem.rsplit('_', 2)`, skip the account-number check, build `txn_key` from the file's account or card reference, add a `source_kind` column and keep card rows out of spend totals.

Structure and checks
- ETL separation: `extract` is the only reader, `transform` is a pure function (DataFrame in, DataFrame out; no files, no printing), `load_parquet` is the only writer. This makes transform testable in memory and lets another source (an API) replace only extract.
- Python does only what must happen before SQL can use the data (decode, rename, parse, remove PII, parse FX). Business rules such as categories belong in dbt. `is_internal_transfer` and `spend_date` currently live in Python; moving them is an open judgment call.
- One package per source under `pipelines/`; shared code in `pipelines/common`. Split by stage inside a source; do not split further.
- Errors for anything that makes the data wrong (schema drift, account mismatch, bad amount, FX mismatch, booking dates outside the file-name range, possible card number, unknown account). Warnings for missing labels and coverage. An unknown account stays an error because the alias names the output file.
- Coverage check works from the cleaned file names (`<alias>_<start>_<end>.parquet`), not from rows, so an empty month (a file with zero rows) counts as covered. Gap: start > previous end + 1 day. Overlap: start <= previous end (uses the running maximum end, so nested ranges give no false gaps). Warnings only; the whole output folder is checked each run.
- Wildcards are expanded in Python (`expand_globs`) because cmd.exe and PowerShell pass `*.csv` through unexpanded.
- Re-running overwrites the same output file names, so every step is idempotent.

dbt and DuckDB
- One DuckDB database for everything (`data/warehouse/finance.duckdb`), not one per provider: marts need all accounts and providers together, and a dbt target points at one database. Provider folders exist only in `data/raw/` and `data/clean/`.
- Source design: one dbt source per provider, one logical table backed by a wildcard over all its Parquet files. Date-range files are storage, not structure: no per-file or per-account sources. Account and currency are columns. Filter periods by `spend_date` / `booking_date` in models, never by picking files.
- Naming: `stg_<source>__<entity>`; the provider stays in the model name even inside a provider folder, because model names must be unique and `ref()` and database objects show no folder. Sources in `_<source>__sources.yml`, separate from model YAML.
- Staging is materialized as a table, not a view: a view stores the relative Parquet path and fails when queried from any other folder (PyCharm viewer, notebooks, a dashboard or Docker). The table makes the database self-contained; it is current only after `dbt build`.
- De-duplication: the most specific export is the authoritative copy. `with_file_span` adds `file_span_days` = end date minus start date, read from the last two `_`-separated parts of `source_file` (`SPLIT_PART` with negative indexes, so aliases may contain any number of underscores; a bad name gives `''` and the `DATE` cast fails loudly). `deduplicated` keeps `QUALIFY ROW_NUMBER() OVER (PARTITION BY txn_key ORDER BY file_span_days, source_file) = 1`: shortest span first, `source_file` as the unique tie-breaker so the result is deterministic. `typed` drops the helper with `* EXCLUDE (file_span_days)`. Only `source_file` differs between copies, so totals are unaffected; compared with the first version (file-name order), only the January duplicates changed (now monthly instead of yearly). Date format of file names is owned by Python (`parse_filename`), so SQL does not re-validate it.
- Types are converted in dbt only (one owner), in the `typed` CTE: `amount` and `fx_orig_amount` float -> `DECIMAL(18,2)` (money: exact cents for sums and reconciliation; all current values have at most 2 decimals, a 3-decimal currency would need `(18,3)`), `booking_date` / `spend_date` from midnight timestamps to `DATE` (clean grouping and date joins, for example FX reference rates). `fx_rate` stays `DOUBLE`: a ratio that is multiplied and compared, never summed, so float precision is more than enough. `transaction_ts` stays a timestamp without time zone (Budapest local). Non-FX rows hold real `NULL`s (not `NaN`), which cast cleanly.
- Enforced model contract on `stg_erste_hu__transactions`: every output column listed with `data_type`, in `OUTPUT_COLS` order. It is the dbt-side check of the Python -> dbt contract: an extra or missing column, or a wrong type (for example a forgotten cast, or a helper column left in the final `select`), stops the build. Write precision and scale (`decimal(18,2)`): plain `numeric` / `decimal` means `DECIMAL(18,3)` in DuckDB, and with a contract the stored table takes the contract's type. With the contract in place, `SELECT * REPLACE / EXCLUDE` is kept: the SQL stays short and the YAML holds the explicit, checked column list. Changing `OUTPUT_COLS` means updating this contract.
- A failed `dbt build` leaves the previous table in place, so `describe` / queries on `ref()` can show stale results. Check that the last build succeeded; `dbt show --select <model>` runs the current SQL without building.
- dbt tests live in `dbt_tests/` (`test-paths`), so they do not mix with pytest in `tests/`. A singular test's severity is set in a top-level `data_tests:` YAML entry (or `config()` in its SQL), never under a model column, which takes only generic tests.
- `profiles.yml` holds only the DuckDB file path, so it is committed. A future cloud target (for example Databricks) must read credentials with `env_var()`, never commit them.

## Conventions

- Python 3.14+ syntax with type hints on function signatures (`str | Path`, `list[str]`). Single quotes. snake_case. Small functions.
- Imports are absolute (`from pipelines.common.load import load_parquet`).
- I/O only in `extract.py`, `load.py`, `pipeline.py`, `__main__.py` and `cli.py`. Everything in `transform.py` stays pure.
- Fail loudly on anything that makes data wrong; never hide a problem with a fallback value. Missing reference labels are the one case that warns.
- Keep pandas `.str` regexes compatible with both the Python and Arrow engines (see the regex rule above). Compare outputs before and after a change with `pd.testing.assert_frame_equal`.
- Tests and examples use only fabricated data. Build test data with `tests/factories.py` (`make_row`, `card_row`, `make_raw`, `write_export`) instead of writing DataFrames by hand; `make_raw` gives the in-memory Hungarian-column DataFrame that `transform` takes. Every bug fix gets a test that would have caught it.
- Never print or log full account numbers or card numbers. Masked card references may appear in warnings, because I need them to fill `cards.csv`.
- Changing `OUTPUT_COLS` means updating the dbt models too; say so in the change summary.
- After every change, tell me which files changed and what changed in each, and say what was tested and what was not. I often apply changes to my own copy file by file.
- Keep explanations short and direct; say when something was verified versus assumed.

## How I work with Claude (learning first)

This project is how I learn data engineering. Working code I cannot explain is a failure, not a shortcut. Default to helping me think, not doing the work for me.

Modes. I may name one; if I do not, use the default for the roadmap step (table below).
- **Review** (default for anything I write): point out bugs, edge cases, privacy risks and weak spots, ranked by importance, with line references. Say *what* is wrong and *why*; do not rewrite my code. Show a fix only when I ask, and then the smallest one.
- **Hint**: when I am stuck, give the smallest useful nudge first (the concept, the docs page, the question to ask myself). Give a bigger hint only if I ask again. Never jump straight to the solution.
- **Explain**: teach the concept with a tiny example that is not my project's code, then let me apply it.
- **Quiz**: after a step, ask me 3-5 short questions about why it works (for example: why de-duplicate on `txn_key` in dbt and not in Python?). Correct my answers honestly.
- **Build**: you write the code. Only for steps marked delegate, or when I explicitly say "build it". Afterwards, tell me the 2-3 things in it most worth understanding.

Defaults per roadmap step:

| Step | Default mode | Why |
|---|---|---|
| dbt staging model, dbt tests | Hint + Review | core data-engineering skill: SQL, typing, de-duplication |
| Category seed and rules | Review | my own business logic |
| Marts, incremental models | Hint + Review | data modeling and windowing are the main learning goal |
| FX-markup analysis | Explain + Review | my actual data-science question; I do the analysis |
| DuckDB setup, dashboard | Review | some new tools, less core |
| Dockerfile, docker compose | Hint + Review | job-relevant; I write it, you check privacy (`.dockerignore`) |
| CI workflow, backup script, `.gitignore`, renames, boilerplate | Build | little learning value |
| Tests | I write the test cases first (what correct means); code can be either | deciding behaviour is the hard part |

Rules for every mode:
- Before helping with something I am stuck on, ask what I tried and what I expected, unless I already said.
- If I ask for code in a learning step, check once ("this is a Hint step: want a hint or the full code?"), then respect my answer.
- Point out when I seem to accept something without understanding it, and suggest a quiz or an explain-back.
- When you review, also say what is good, so I know what to keep doing.
- The privacy rules and conventions above apply in every mode.

After each roadmap step I write a few lines in my own words in `LEARNING.md` (one section per step: built, learned, would do differently). Before moving to the next step, check that the step's section is filled in, and ask me if it is not. These notes are mine; do not write them for me. They follow the same privacy rule: no real amounts, partners, row counts, account or card numbers.

## Open next steps

In rough order:

1. Finish roadmap step 1 (staging model done: span-based de-duplication and enforced contract):
   - Check that the `unknown_card` test really warns (temporarily point it at an existing alias; expect `WARN` and a successful build).
   - Optional: one-line `description`s for the less obvious columns (`txn_key`, `spend_date`, `fx_amount_ok`, `source_file`) for `dbt docs`.
   - Learning note for the step in `LEARNING.md`.
   - Considered and not chosen for de-duplication: drop `source_file` and use `distinct` (disagreeing copies would fail `unique` loudly, but traceability is lost).
2. Category seed (merchant rule -> category) joined in dbt; unmatched merchants fall into "uncategorized" for occasional review. A seed CSV is caught by the `*.csv` rule in `.gitignore`: add an exception only after deciding merchant names are fine to share. The `unknown_card` check and an "uncategorized" check have the same shape: a good point to turn the singular test into a custom generic test.
3. Marts: monthly spend by category and currency (by `spend_date`), income vs spending without internal transfers, recurring payments. Incremental, reprocessing the previous month. Model as a star schema: transactions as the fact table; dimensions only where an entity has its own attributes (accounts: currency, provider, type; cards; categories; calendar). An account dimension needs an alias-keyed seed without account numbers, never `config/accounts.csv`. Consider separate schemas for staging and marts (`+schema`; mind the default prefix from `generate_schema_name`).
4. FX analysis: add daily ECB or MNB reference rates as a second small source, compute the markup on foreign card payments, compare with the rate from my own HUF -> EUR top-ups (needs real internal transfers in the data; this also exercises `is_internal_transfer`).
5. Dashboard (Streamlit or Metabase) on the DuckDB marts.
6. One command that runs clean, `dbt build` and the coverage check; later an orchestrator (Dagster) for scheduling or a trigger on new files.
7. GitHub remote, then CI (GitHub Actions running `uv run pytest`), a backup routine for `data/raw/`, and a decision on `partner_iban` in anything shared.

Optional:
- Enable Banking API as a second adapter returning the same schema (consent expires, so fail loudly).
- `valid_from` / `valid_to` columns in `cards.csv`, with a warning for payments outside a card's validity window.
- Move card-alias mapping into `common` as a column-wise helper once a second source needs it.
- Move `is_internal_transfer` and `spend_date` logic into dbt.
- Replay transactions through Kafka or Spark purely as a learning exercise; the data volume does not need either.
