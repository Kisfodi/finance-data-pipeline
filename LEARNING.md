# Learning log

One section per roadmap step, newest at the bottom, written in my own words.
Same privacy rule as the rest of the repo: no real amounts, partners, row counts, account or card numbers.

<!-- Template:
## Step N: <title> (YYYY-MM-DD)
**Built:**
**Learned:**
**Would do differently:**
-->

## Step 1: dbt staging (2026-11-15)
**Built:**
- Configured the dbt project, including profiles, sources and staging models
- Defined staging models from several sources using its config file and CTEs
- Defined data tests to ensure bad data is caught before converting to marts
- Defined data contracts to ensure data integrity and consistency
- Added data types to staging models
- Refined what copies of duplicates should be kept by prioritizing monthly iterations over yearly iterations

**Learned:**
- Setup
  - Setting up dbt using DuckDB in my project
  - Configuring my dbt project using YML files (including profiles.yml, and project.yml)
- Sources
  - Defining a singular staging model using multiple sources (e.g. parquet files) in dbt?
  - Configuring the sources using YML files
- Staging
  - Using CTEs to make the intermediate staging models more readable, accessible, thus easier to maintain and debug
  - Naming conventions for sources and staging models
- Types
  - Learned about the importance of specifying data types in dbt models to ensure data integrity and performance.
  - Discovered that using the correct data types can help prevent data type mismatches and improve query performance.
- Deduplication
  - Using different approaches to deduplicate data in dbt models
  - Found out that negative indices can also be used with DuckDB (not sure about other SQL flavors)
- Tooling
  - Using different dbt command to check data contracts, intermediate staging models, and final models
**Would do differently:**
- In the ongoing year, extraction of the monthly data at the start of the next month
- When the year ends
  - Extraction of the yearly data at the start of the next year
  - Archive monthly data as historical monthly data will not be different from some parts of the yearly data (12 monthly tables $\rightarrow$ 1 yearly table)
- Using different approaches to ensure data contracts, not only specific to DuckDB