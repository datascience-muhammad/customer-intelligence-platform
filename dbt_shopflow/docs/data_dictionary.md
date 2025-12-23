# ShopFlow Data Dictionary

Scope: curated and staging dbt models in `dbt_shopflow/models`.

## Tables

### dim_customers
- customer_id: string — PK
- email: string
- name: string
- city: string
- country: string
- signup_date: date
- customer_segment: string
- total_orders: integer
- total_spent: numeric
- tenure_days: integer
- total_support_tickets: integer
- avg_satisfaction_score: numeric(3,2)
- avg_resolution_hours: integer
- open_tickets_count: integer
- last_ticket_date: timestamp

Source: `stg_customers` (see models/staging/stg_customers.sql)

### dim_products
- product_id: string — PK
- product_name: string
- category: string
- brand: string
- price: numeric
- cost: numeric
- margin_pct: numeric
- stock_status: string

Source: `stg_products` (models/staging/stg_products.sql)

### dim_dates
- date_id: integer — surrogate PK
- date: date
- year, quarter, month, week, day: integer
- day_of_week: integer
- is_weekend: boolean

Derived from: `stg_orders`, `stg_events`, `stg_support_tickets` (models/curated/dim_dates.sql)

### fact_orders
- order_id: string — PK
- customer_id: string (FK -> dim_customers)
- product_id: string (FK -> dim_products)
- order_date: date
- order_date_id: integer (FK -> dim_dates.date_id)
- order_amount: numeric
- quantity: integer
- discount_amount: numeric
- payment_method: string

Source: `stg_orders` (models/staging/stg_orders.sql)

### fact_events
- event_id: string — PK
- customer_id: string
- session_id: string
- event_type: string
- event_timestamp: timestamp
- product_id: string
- device_type: string
- browser: string

Source: `stg_events` (models/staging/stg_events.sql)

### support_tickets (curated)
- ticket_id: string
- customer_id: string
- created_date: timestamp
- resolved_date: timestamp
- issue_type: string
- issue_category: string
- status: string (normalized values)
- is_resolved: boolean
- resolution_hours: double
- hours_open: double
- satisfaction_score: integer
- agent_id: string

Source: `stg_support_tickets` (models/staging/stg_support_tickets.sql)

### ml_features
- customer_id: string
- recency_days: integer
- frequency_orders: integer
- monetary_total: numeric
- avg_order_value: numeric
- days_since_signup: integer
- churn_risk_score: numeric
- total_support_tickets: integer
- avg_satisfaction_score: numeric
- avg_resolution_hours: integer
- open_tickets_count: integer
- last_ticket_date: timestamp

Source: computed from `stg_orders`, `stg_customers`, `stg_support_tickets` (models/curated/ml_features.sql)

## Notes & Recommendations
- Types are inferred from casts in SQL; run `DESCRIBE`/`\d` on your target DB to capture exact types after materialization.
- Add `schema.yml` descriptions in `dbt_shopflow/models` to enable `dbt docs generate` and produce an authoritative docs site.
- Sensitive fields (email, customer_id) should be classified and access-controlled.

---
Generated from DBT model SQL in this repository. For updates, re-run this generation or keep `schema.yml` in sync.
