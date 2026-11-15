SELECT txn_key, card_alias
FROM {{ ref('stg_erste_hu__transactions') }}
WHERE card_alias = 'unknown_card'