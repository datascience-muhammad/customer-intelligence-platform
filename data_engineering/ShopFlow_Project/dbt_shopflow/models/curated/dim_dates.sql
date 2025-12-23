-- dim_dates: simple date dimension derived from available dates
with dates as (
    select order_date::date as d from {{ ref('stg_orders') }}
    union
    select event_timestamp::date from {{ ref('stg_events') }}
    union
    select created_date::date from {{ ref('stg_support_tickets') }}
), distinct_dates as (
    select distinct d as date
    from dates
)

select
    row_number() over (order by date) as date_id,
    date as date,
    extract(year from date) as year,
    extract(quarter from date) as quarter,
    extract(month from date) as month,
    extract(week from date) as week,
    extract(day from date) as day,
    extract(dow from date) as day_of_week,
    case when extract(dow from date) in (0,6) then true else false end as is_weekend
from distinct_dates
