-- staging model for orders
-- Cleaning applied:
-- 1. Deduplicate on order_id (keep latest by order_date)
-- 2. Cast types and coalesce numeric fields to sensible defaults
-- 3. Normalize categorical fields

with raw as (
    select * from {{ source('rds', 'orders') }}
),
ranked as (
    -- Keep latest by order_date
    select *,
    row_number() over (partition by order_id order by cast(order_date as timestamp) desc nulls last) as rn
    from raw
)

select
    cast(order_id as text) as order_id,
    cast(customer_id as text) as customer_id,
    -- product_id not available in raw.orders; set null
    null::int as product_id,
    cast(order_date as timestamp) as order_date,
    -- use order_amount from raw.orders (already renamed during extraction)
    coalesce(order_amount, 0.0)::numeric as order_amount,
    -- quantity not available; default to 1
    1::int as quantity,
    -- discount_amount not available; default to 0
    0.0::numeric as discount_amount,
    -- payment_method not available; keep null
    null::text as payment_method
from ranked
where rn = 1

