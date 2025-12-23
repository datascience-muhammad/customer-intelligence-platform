-- fact_orders: transactional fact table
-- Add order_date_id FK to dim_dates
with orders as (
    select * from {{ ref('stg_orders') }}
),
dates as (
    select * from {{ ref('dim_dates') }}
)

select
    o.order_id,
    o.customer_id,
    o.product_id,
    o.order_date::date as order_date,
    d.date_id as order_date_id,
    o.order_amount,
    o.quantity,
    o.discount_amount,
    o.payment_method
from orders o
left join dates d on o.order_date::date = d.date
