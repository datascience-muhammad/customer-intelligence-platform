-- staging model for inventory
-- Cleaning applied:
-- 1. Deduplicate on product_id (keep a single record per product)
-- 2. Coalesce stock quantities and compute stock_status

with raw as (
    select * from {{ source('rds', 'inventory') }}
),
ranked as (
    -- use last_updated to pick the latest record
    select *, row_number() over (partition by product_id order by last_updated desc nulls last) as rn
    from raw
)

select
    cast(product_id as text) as product_id,
    -- use warehouse_id from raw table (keep as text)
    cast(warehouse_id as text) as warehouse_id,
    coalesce(cast(stock_level as int), 0) as stock_level,
    cast(reorder_level as int) as reorder_level,
    cast(last_updated as timestamp) as last_updated,
    case when coalesce(stock_level,0) > 0 then 'in_stock' else 'out_of_stock' end as stock_status
from ranked
where rn = 1

