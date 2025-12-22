-- staging model for events
-- Cleaning applied:
-- 1. Deduplicate on event_id (keep latest by event_timestamp)
-- 2. Cast timestamps and normalize text fields

with raw as (
    select * from {{ source('rds', 'events') }}
),
ranked as (
    select *,
    row_number() over (partition by event_id order by cast(event_timestamp as timestamp) desc nulls last) as rn
    from raw
)

select
    cast(event_id as text) as event_id,
    cast(customer_id as text) as customer_id,
    -- expose a standard column name used downstream
    cast(event_timestamp as timestamp) as event_timestamp,
    lower(trim(event_type)) as event_type,
    null::text as session_id,
    null::text as device_type,
    null::text as browser,
    -- product_id not present in raw.events; keep null
    null::text as product_id
from ranked
where rn = 1

