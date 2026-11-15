WITH
    source AS (
        SELECT *
        FROM {{ source('erste_hu', 'transactions') }}
    ),

    with_file_span AS (
        SELECT *,
        CAST(SPLIT_PART(source_file, '_', -1) AS DATE)
            - CAST(SPLIT_PART(source_file, '_', -2) AS DATE) AS file_span_days
        FROM source
    ),

    deduplicated AS (
        SELECT *
        FROM with_file_span
        QUALIFY
            ROW_NUMBER() OVER (PARTITION BY txn_key ORDER BY file_span_days, source_file) = 1
    ),

    typed AS (
        SELECT *
        EXCLUDE (file_span_days)
        REPLACE (
            CAST(booking_date AS DATE) AS booking_date,
            CAST(spend_date AS DATE) AS spend_date,
            CAST(amount AS DECIMAL(18, 2)) AS amount,
            CAST(fx_orig_amount AS DECIMAL(18, 2)) AS fx_orig_amount
        )
        FROM deduplicated
    )

SELECT *
FROM typed