-- fact_events: customer behavioral events
select
    event_id,
    customer_id,
    session_id,
    event_type,
    event_timestamp,
    product_id,
    device_type,
    browser
from {{ ref('stg_events') }}
