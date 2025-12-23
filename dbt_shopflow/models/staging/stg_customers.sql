with raw as (
    select * from {{ source('rds', 'customers') }}
),
ranked as (
    select *,
    row_number() over (partition by customer_id order by customer_id) as rn
    from raw
)

select
    cast(customer_id as text) as customer_id,
    lower(trim(email)) as email,
    first_name,
    last_name,
    city,
    country,
    signup_date as registration_date,
    customer_segment,
    total_orders,
    total_spent
from ranked
where rn = 1

