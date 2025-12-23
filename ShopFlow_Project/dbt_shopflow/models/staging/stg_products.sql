-- staging model for products
-- Cleaning applied:
-- 1. Deduplicate on product_id (keep one record; if no timestamp available it will keep an arbitrary row)
-- 2. Trim and coalesce numeric fields
-- 3. Compute margin_pct

with raw as (
    select * from {{ source('rds', 'products') }}
),
ranked as (
    -- If there is an update timestamp field, replace the ORDER BY below with that field.
    select *,
      row_number() over (partition by product_id order by product_id) as rn
    from raw
)

select
    cast(product_id as text) as product_id,
    trim(product_name) as product_name,
    trim(category) as category,
    -- fields not present in raw.products
    null::text as brand,
    coalesce(price, 0.0)::numeric as price,
    null::numeric as cost,
    null::numeric as margin_pct,
    null::text as stock_status
from ranked
where rn = 1

