-- Curated Customer Dimension
with customers as (
  select * from {{ ref('stg_customers') }}
),

orders_agg as (
  select
    customer_id,
    count(*)::int as total_orders,
    sum(order_amount)::numeric as total_spent
  from {{ ref('stg_orders') }}
  group by customer_id
),

tickets_agg as (
  select
    customer_id,
    count(*)::int as total_support_tickets,
    round(avg(satisfaction_score)::numeric, 2)::numeric(3,2) as avg_satisfaction_score,
    round(avg(resolution_hours))::int as avg_resolution_hours,
    sum(case when lower(trim(status)) not in ('resolved','closed') then 1 else 0 end)::int as open_tickets_count,
    cast(max(created_date) as timestamp) as last_ticket_date
  from {{ ref('stg_support_tickets') }}
  where customer_id is not null
  group by customer_id
)

select
  c.customer_id,
  c.email,
  -- use first_name and last_name from staging
  trim(coalesce(c.first_name || ' ' || c.last_name, c.first_name, c.last_name)) as name,
  c.city,
  c.country,
  c.registration_date as signup_date,
  c.customer_segment,
  coalesce(o.total_orders, 0) as total_orders,
  coalesce(o.total_spent, 0.0)::numeric as total_spent,

  -- tenure days
  case 
    when c.registration_date is not null then (current_date - c.registration_date::date)
    else null
  end as tenure_days,

  coalesce(t.total_support_tickets, 0) as total_support_tickets,
  coalesce(t.avg_satisfaction_score, 0.00)::numeric(3,2) as avg_satisfaction_score,
  coalesce(t.avg_resolution_hours, 0) as avg_resolution_hours,
  coalesce(t.open_tickets_count, 0) as open_tickets_count,
  cast(t.last_ticket_date as timestamp) as last_ticket_date

from customers c
left join orders_agg o on c.customer_id = o.customer_id
left join tickets_agg t on c.customer_id = t.customer_id
