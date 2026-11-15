WITH
    source AS (
        SELECT *
        FROM {{ source('erste_hu', 'transactions') }}
    ),

    deduplicated AS (
        SELECT *
        FROM source
        QUALIFY
            ROW_NUMBER() OVER (PARTITION BY txn_key ORDER BY source_file DESC) = 1
    ),

    typed AS (
        SELECT * REPLACE (
            CAST(amount AS DECIMAL(18, 2)) AS amount,
            CAST(booking_date AS DATE) AS booking_date,
            CAST(spend_date AS DATE) AS spend_date
        ) FROM deduplicated
    )

SELECT *
FROM typed