-- ML features table: basic RFM + ticket-based features
-- ml_features: precomputed features per customer
with orders as (
    select customer_id,
           count(*) as frequency_orders,
           sum(order_amount) as monetary_total,
           avg(order_amount) as avg_order_value,
           max(order_date) as last_order_date,
           min(order_date) as first_order_date
    from {{ ref('stg_orders') }}
    group by customer_id
),
customers as (
    select * from {{ ref('stg_customers') }}
),
    tickets as (
    select customer_id,
            count(ticket_id)::int as total_support_tickets,
            avg(satisfaction_score) as avg_satisfaction_score,
            -- round avg resolution hours to integer to match dim_customers
            round(avg(resolution_hours))::int as avg_resolution_hours,
            -- use case-insensitive, trimmed status check to match dim_customers behavior
            sum(case when lower(trim(status)) not in ('resolved','closed') then 1 else 0 end)::int as open_tickets_count,
            -- cast to timestamp for consistent dtype
            cast(max(created_date) as timestamp) as last_ticket_date
    from {{ ref('stg_support_tickets') }}
    group by customer_id
)

select
    c.customer_id,
    (now()::date - coalesce(o.last_order_date::date, c.registration_date::date)) as recency_days,
    coalesce(o.frequency_orders,0) as frequency_orders,
    coalesce(o.monetary_total,0.0) as monetary_total,
    round(coalesce(o.avg_order_value,0.0)::numeric,2) as avg_order_value,
    (now()::date - c.registration_date::date) as days_since_signup,
    -- churn_risk_score: simple heuristic combining recency and support tickets
    (case
        when (now()::date - coalesce(o.last_order_date::date, c.registration_date::date)) > 90 then 0.7
        when coalesce(t.open_tickets_count,0) > 3 then 0.6
        else 0.1
     end) as churn_risk_score,
    coalesce(t.total_support_tickets,0) as total_support_tickets,
    round(coalesce(t.avg_satisfaction_score,0)::numeric,2) as avg_satisfaction_score,
    coalesce(t.avg_resolution_hours,0) as avg_resolution_hours,
    coalesce(t.open_tickets_count,0) as open_tickets_count,
    cast(t.last_ticket_date as timestamp) as last_ticket_date
from customers c
left join orders o on o.customer_id = c.customer_id
left join tickets t on t.customer_id = c.customer_id
