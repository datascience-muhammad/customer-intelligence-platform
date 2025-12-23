-- dim_products: product dimension
with products as (
    select * from {{ ref('stg_products') }}
)

select
    product_id,
    product_name,
    category,
    brand,
    price,
    cost,
    margin_pct,
    stock_status
from products
