# ShopFlow Data Dictionary

This document describes the data model used in the **Customer Intelligence Platform** for:

1. **Relational layer (PostgreSQL on AWS RDS)** – core e‑commerce entities.
2. **Support tickets layer (MongoDB Atlas)** – customer support interactions exposed via the ShopFlow Support API.

Use this as reference when building DE / DS pipelines, joins, and training exercises.

---

## 1. Relational Layer – AWS RDS (PostgreSQL)

### 1.1 `customers` table

One row per **customer**.

| Column             | Type            | Nullable | Description                                                      | Notes / Examples                                                         |
| ------------------ | --------------- | -------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------ |
| `customer_id`      | `VARCHAR(20)`   | No       | Synthetic unique identifier for each customer.                   | Primary key. Format: `CUST000001`, `CUST123456`.                         |
| `email`            | `VARCHAR(255)`  | No       | Customer email address.                                          | Unique. Fake addresses generated via Faker.                              |
| `first_name`       | `VARCHAR(100)`  | Yes      | Customer first name.                                             | e.g. `"John"`.                                                           |
| `last_name`        | `VARCHAR(100)`  | Yes      | Customer last name.                                              | e.g. `"Doe"`.                                                            |
| `city`             | `VARCHAR(100)`  | Yes      | City where the customer is located.                              | e.g. `"Toronto"`, `"London"`.                                            |
| `country`          | `VARCHAR(50)`   | Yes      | Country for the customer.                                        | One of `USA`, `Canada`, `UK`, `Germany`, `France`, `Australia`.          |
| `signup_date`      | `DATE`          | Yes      | Date the customer signed up to the platform.                     | Uniformly distributed between `2022-01-01` and `2024-11-30`.             |
| `customer_segment` | `VARCHAR(50)`   | Yes      | Behavioural segment used for churn / value analysis.             | One of: `High Value`, `Medium Value`, `Low Value`, `At Risk`, `Churned`. |
| `total_orders`     | `INT`           | Yes      | Total historical number of orders for this customer (synthetic). | Generated based on `customer_segment` (e.g. higher for `High Value`).    |
| `total_spent`      | `DECIMAL(10,2)` | Yes      | Approximate total revenue from this customer in currency units.  | Synthetic, consistent with `total_orders` and segment.                   |

**Business notes**

- `customer_segment` is **assigned first** and drives the distribution of `total_orders` and `total_spent`.
- Churn logic in the dataset uses **order recency** (see `orders` section) in combination with this segment.

---

### 1.2 `products` table

One row per **product** in the catalog.

| Column         | Type            | Nullable | Description                                   | Notes / Examples                                                                         |
| -------------- | --------------- | -------- | --------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `product_id`   | `VARCHAR(20)`   | No       | Synthetic unique identifier for each product. | Primary key. Format: `PROD00001`, `PROD01234`.                                           |
| `product_name` | `VARCHAR(255)`  | Yes      | Human‑readable product name.                  | e.g. `"Nova Electronics"`, `"Aurora Clothing"`.                                          |
| `category`     | `VARCHAR(50)`   | Yes      | High‑level product category.                  | One of: `Electronics`, `Clothing`, `Home & Garden`, `Sports`, `Books`, `Beauty`, `Toys`. |
| `brand`        | `VARCHAR(50)`   | Yes      | Product brand.                                | One of: `BrandA`, `BrandB`, `BrandC`, `BrandD`, `BrandE`, `Generic`.                     |
| `price`        | `DECIMAL(10,2)` | Yes      | Retail price of the product.                  | Range roughly `10.00`–`500.00`.                                                          |
| `cost`         | `DECIMAL(10,2)` | Yes      | Internal unit cost of the product.            | Typically 40–70% of `price`.                                                             |
| `margin_pct`   | `DECIMAL(5,2)`  | Yes      | Gross margin percentage on the product.       | Computed as `((price - cost) / price) * 100`.                                            |
| `stock_status` | `VARCHAR(20)`   | Yes      | Current stock status label.                   | One of: `In Stock`, `Low Stock`, `Out of Stock`.                                         |

**Business notes**

- Use `price`, `cost`, and `margin_pct` for profitability analysis.
- `category` and `brand` are useful for segmentation and product‑mix analysis.

---

### 1.3 `orders` table

One row per **order line item** (order–product pair).

| Column            | Type            | Nullable | Description                                              | Notes / Examples                                            |
| ----------------- | --------------- | -------- | -------------------------------------------------------- | ----------------------------------------------------------- |
| `order_id`        | `VARCHAR(20)`   | No       | Synthetic order identifier.                              | Primary key. Format: `ORD0000001`, `ORD0123456`.            |
| `customer_id`     | `VARCHAR(20)`   | Yes      | Customer who placed the order.                           | Foreign key → `customers.customer_id`.                      |
| `product_id`      | `VARCHAR(20)`   | Yes      | Product purchased in this order line.                    | Foreign key → `products.product_id`.                        |
| `order_date`      | `DATE`          | Yes      | Date the order was placed.                               | `2022-01-01` to `2024-11-29`.                               |
| `order_amount`    | `DECIMAL(10,2)` | Yes      | Gross value of this order line (before discount).        | `price * quantity`.                                         |
| `quantity`        | `INT`           | Yes      | Number of units purchased for this product in the order. | Range `1`–`5`.                                              |
| `discount_amount` | `DECIMAL(10,2)` | Yes      | Discount applied on this order line.                     | 0%, 5%, 10%, or 15% of `order_amount`.                      |
| `payment_method`  | `VARCHAR(50)`   | Yes      | Payment method used.                                     | One of: `Credit Card`, `PayPal`, `Debit Card`, `Apple Pay`. |

**Business / churn logic notes**

- **Churned customers** (`customers.customer_segment = 'Churned'`): their `order_date` values are mostly in **early part of the timeline** (2022–mid 2023).
- **Active customers**: orders spread across full date range (2022–2024).
- A key derived metric used in validation:

  - `days_since_last_order` = `END_DATE` − `max(order_date)` per `customer_id`.
  - Customers with `days_since_last_order > 90` are treated as **churned** in the data quality checks.

---

### 1.4 `events` table

One row per **user event** (page view, cart event, checkout, etc.). Used for behaviour and funnel analysis.

| Column            | Type          | Nullable | Description                                        | Notes / Examples                                                                |
| ----------------- | ------------- | -------- | -------------------------------------------------- | ------------------------------------------------------------------------------- |
| `event_id`        | `VARCHAR(20)` | No       | Synthetic event identifier.                        | Primary key. Format: `EVT00000001`.                                             |
| `customer_id`     | `VARCHAR(20)` | Yes      | Customer generating the event.                     | Foreign key → `customers.customer_id`.                                          |
| `session_id`      | `VARCHAR(50)` | Yes      | Synthetic session identifier.                      | Format: `SES1234567`.                                                           |
| `event_type`      | `VARCHAR(50)` | Yes      | Type of event.                                     | One of: `page_view`, `add_to_cart`, `remove_from_cart`, `checkout`, `purchase`. |
| `event_timestamp` | `TIMESTAMP`   | Yes      | Timestamp of the event (date + time).              | Random day/time between `2022-01-01` and `2024-11-30`.                          |
| `product_id`      | `VARCHAR(20)` | Yes      | Product associated with the event (if applicable). | Foreign key → `products.product_id`.                                            |
| `page_url`        | `TEXT`        | Yes      | Pseudo‑URL path representing the visited page.     | e.g. `/products/electronics/PROD00042`.                                         |
| `device_type`     | `VARCHAR(20)` | Yes      | Device type used.                                  | One of: `Desktop`, `Mobile`, `Tablet`.                                          |
| `browser`         | `VARCHAR(50)` | Yes      | Browser used.                                      | One of: `Chrome`, `Safari`, `Firefox`, `Edge`.                                  |

**Business notes**

- Can be used to compute **funnel metrics** (add‑to‑cart → checkout → purchase) by `customer_id`, `product_id`, or `session_id`.
- Can be joined to `orders` using a combination of `customer_id`, `product_id`, and time proximity, if needed for advanced analysis.

---

### 1.5 `inventory` table

One row per **product–warehouse–date** combination. Used for basic stock and replenishment analysis.

| Column          | Type          | Nullable | Description                                            | Notes / Examples                                                                         |
| --------------- | ------------- | -------- | ------------------------------------------------------ | ---------------------------------------------------------------------------------------- |
| `product_id`    | `VARCHAR(20)` | No       | Product tracked in inventory.                          | Foreign key → `products.product_id`. Part of primary key.                                |
| `warehouse_id`  | `VARCHAR(50)` | No       | Warehouse identifier.                                  | One of: `WH-US-EAST`, `WH-US-WEST`, `WH-EU-CENTRAL`, `WH-ASIA-PAC`. Part of primary key. |
| `date`          | `DATE`        | No       | Date for which the inventory snapshot applies.         | Within last 31 days of `END_DATE`. Part of primary key.                                  |
| `stock_level`   | `INT`         | Yes      | Units in stock on that date at that warehouse.         | 0–500.                                                                                   |
| `reorder_level` | `INT`         | Yes      | Threshold level at which replenishment should trigger. | 50–100.                                                                                  |
| `last_updated`  | `TIMESTAMP`   | Yes      | Timestamp when this row was last updated.              | `NOW()` at generation time.                                                              |

**Keys & indexes**

- Primary key: (`product_id`, `warehouse_id`, `date`).
- Use this table to create **days of cover**, **stockout**, and **reorder** exercises.

---

## 2. Support Tickets – MongoDB Atlas (`support_tickets` collection)

One document per **support ticket**. This lives in MongoDB Atlas (e.g. database `shopflow`, collection `support_tickets`) and is exposed via the **ShopFlow Support API**.

### 2.1 Document schema – `support_tickets`

Below is the logical schema used by the generator and the API.

| Field                | Type       | Nullable | Description                                               | Notes / Examples                                                                                  |
| -------------------- | ---------- | -------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `_id`                | `ObjectId` | No       | MongoDB internal unique ID for the document.              | Not exposed in the FastAPI Pydantic model, but present in Mongo.                                  |
| `ticket_id`          | `string`   | No       | Synthetic ticket identifier.                              | Format: `TKT0000001`, `TKT0001234`.                                                               |
| `customer_id`        | `string`   | No       | ID of the customer who opened the ticket.                 | Should match `customers.customer_id` in RDS (e.g. `CUST000456`).                                  |
| `customer_segment`   | `string`   | Yes      | Segment of the customer at the time of ticket generation. | Optional; typically one of `High Value`, `Medium Value`, `Low Value`, `At Risk`, `Churned`.       |
| `created_date`       | `datetime` | No       | When the ticket was created.                              | ISODate in Mongo; roughly aligned with the orders timeline.                                       |
| `resolved_date`      | `datetime` | Yes      | When the ticket was resolved/closed.                      | Null for `Open` / `In Progress` tickets.                                                          |
| `issue_type`         | `string`   | No       | High‑level type of issue reported.                        | One of: `Product Defect`, `Shipping Delay`, `Billing Issue`, `Account Issue`, `Product Question`. |
| `issue_category`     | `string`   | No       | Product category associated with the issue.               | Same category set as `products.category`: `Electronics`, `Clothing`, etc.                         |
| `priority`           | `string`   | No       | Priority assigned to the ticket.                          | One of: `Low`, `Medium`, `High`, `Critical`.                                                      |
| `status`             | `string`   | No       | Lifecycle status of the ticket.                           | One of: `Resolved`, `Closed`, `Open`, `In Progress`.                                              |
| `resolution_hours`   | `int`      | Yes      | Time taken to resolve the ticket in hours.                | Typically between 1 and 720 if status is `Resolved` / `Closed`; null otherwise.                   |
| `satisfaction_score` | `number`   | Yes      | Post‑resolution customer satisfaction rating (1–5).       | Often null for unresolved tickets; distribution skewed to 3–5.                                    |
| `agent_id`           | `string`   | No       | Synthetic support agent identifier.                       | Format: `AGT001`, `AGT050`.                                                                       |
| `description`        | `string`   | No       | Short textual description of the issue.                   | e.g. `"Billing Issue reported by customer"`.                                                      |
| `order_id`           | `string`   | Yes      | Related order ID, if applicable.                          | Matches RDS `orders.order_id` when present (e.g. `ORD0001234`).                                   |
| `product_id`         | `string`   | Yes      | Related product ID, if applicable.                        | Matches RDS `products.product_id` when present (e.g. `PROD00123`).                                |

**Relationships & usage**

- `customer_id` links **Mongo support tickets** to **RDS customers/orders**.
- Optional `order_id` and `product_id` fields allow joining tickets to specific e‑commerce transactions/products.
- `created_date`, `priority`, `status`, and `resolution_hours` support **SLA / operational analytics**.
- `satisfaction_score` enables **CSAT analysis** by segment, agent, or issue type.

---

## 3. Typical Join Patterns (Quick Reference)

- **Customers ↔ Orders**

  - Join key: `customers.customer_id = orders.customer_id`.
  - Use for CLV, churn, and RFM‑style features.

- **Orders ↔ Products**

  - Join key: `orders.product_id = products.product_id`.
  - Use for product performance and mix analysis.

- **Customers ↔ Events**

  - Join key: `events.customer_id = customers.customer_id`.
  - Use for behavioural funnels and pre‑churn activity patterns.

- **Customers ↔ Support Tickets (Mongo)**

  - Join key: `support_tickets.customer_id = customers.customer_id`.
  - Use for linking **support burden** and **churn / value**.

- **Orders ↔ Support Tickets (Mongo)**

  - Join key (when present): `support_tickets.order_id = orders.order_id`.
  - Use for order‑level issue analysis (e.g. defect vs delay vs billing).

This data dictionary is designed so DEs and DSs can easily understand the structure, build pipelines (RDS + Mongo/API), and create realistic analytics and modeling exercises on top of the synthetic ShopFlow platform.
