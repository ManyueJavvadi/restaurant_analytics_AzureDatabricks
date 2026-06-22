# Data Model

All tables live in Unity Catalog `ws_dbxprojectrc`.

---

## Bronze — `01_bronze`

### `orders` (Streaming Table)

Raw order events from Azure Event Hub, parsed from Kafka JSON.

| Column | Type | Notes |
|---|---|---|
| order_id | STRING | Unique order identifier |
| order_timestamp | STRING | Raw ISO timestamp from event |
| restaurant_id | STRING | |
| customer_id | STRING | |
| order_type | STRING | dine_in / takeaway / delivery |
| items | STRING | JSON array of line items |
| total_amount | DOUBLE | |
| payment_method | STRING | cash / card / wallet |
| order_status | STRING | completed / pending / ready / delivered / preparing / confirmed |

---

## Silver — `02_silver`

### `fact_orders` (Streaming Table)

Validated, enriched order facts with time dimensions. Source: `01_bronze.orders`.

| Column | Type | Notes |
|---|---|---|
| order_id | STRING | PK |
| order_timestamp | TIMESTAMP | Parsed from raw string |
| order_date | DATE | |
| order_hour | INT | 0–23 |
| day_of_week | STRING | Monday – Sunday |
| is_weekend | BOOLEAN | True for Sat/Sun |
| restaurant_id | STRING | FK → dim_restaurant |
| customer_id | STRING | FK → dim_customers |
| order_type | STRING | dine_in / takeaway / delivery |
| item_count | INT | Size of items array |
| total_amount | DECIMAL(10,2) | |
| payment_method | STRING | cash / card / wallet |
| order_status | STRING | |

Data quality expectations (drop row on violation):
* `order_id`, `order_timestamp`, `customer_id`, `restaurant_id` NOT NULL
* `item_count > 0`, `total_amount > 0`
* `order_status IN ('completed','pending','ready','delivered','preparing','confirmed')`
* `payment_method IN ('cash','card','wallet')`

### `fact_order_items` (Streaming Table)

Exploded line items — one row per item per order. Source: `01_bronze.orders`.

| Column | Type | Notes |
|---|---|---|
| order_id | STRING | FK → fact_orders |
| item_id | STRING | Menu item identifier |
| restaurant_id | STRING | FK → dim_restaurant |
| order_timestamp | TIMESTAMP | |
| order_date | DATE | |
| item_name | STRING | |
| category | STRING | Food category |
| quantity | INT | |
| unit_price | DECIMAL(10,2) | |
| subtotal | DECIMAL(10,2) | quantity × unit_price |

Data quality: all IDs NOT NULL, quantity/unit_price/subtotal > 0.

### `fact_reviews` (Streaming Table)

AI-enriched customer reviews. Source: `01_bronze.reviews` via `ai_query()`.

| Column | Type | Notes |
|---|---|---|
| review_id | STRING | PK |
| order_id | STRING | FK → fact_orders |
| customer_id | STRING | FK → dim_customers |
| restaurant_id | STRING | FK → dim_restaurant |
| rating | INT | 1–5 |
| review_text | STRING | Raw review text |
| analysis_json | STRING | Full raw AI output JSON |
| sentiment | STRING | positive / neutral / negative |
| issue_delivery | STRING | **'true' or 'false'** (see note) |
| issue_delivery_reason | STRING | |
| issue_food_quality | STRING | **'true' or 'false'** |
| issue_food_quality_reason | STRING | |
| issue_pricing | STRING | **'true' or 'false'** |
| issue_pricing_reason | STRING | |
| issue_portion_size | STRING | **'true' or 'false'** |
| issue_portion_size_reason | STRING | |
| review_timestamp | TIMESTAMP | |

> **Important:** Issue flag columns are STRING type containing literal `'true'` or `'false'` values extracted via `get_json_object` from the AI-generated JSON. Metric view queries must use `LOWER(CAST(flag AS STRING)) = 'true'` — not `= 'yes'` or `= 1`.

Data quality constraints: `sentiment IN ('positive','neutral','negative')`, `rating >= 0`.

### `dim_customers` (Managed Ingestion)

Populated by `pipelline_ingestion_silver` (pipeline ID: `508b0758-c087-4e83-ac85-1ea552f169a8`), a Lakeflow Connect managed ingestion pipeline. **Not authored as SDP source code.**

| Column | Type |
|---|---|
| customer_id | STRING |
| name | STRING |
| email | STRING |
| city | STRING |
| join_date | DATE |

### `dim_restaurant` (Managed Ingestion)

Also populated by `pipelline_ingestion_silver`. **Not authored as SDP source code.**

| Column | Type |
|---|---|
| restaurant_id | STRING |
| name | STRING |
| city | STRING |

---

## Gold — `03_gold`

### `d_sales_summary` (Materialized View)

Daily revenue aggregates. Partitioned by `order_date`. Source: `02_silver.fact_orders`.

| Column | Type | Notes |
|---|---|---|
| order_date | DATE | Partition key |
| total_orders | BIGINT | COUNT DISTINCT order_id |
| total_revenue | DECIMAL(10,2) | SUM total_amount |
| avg_order_value | DECIMAL(10,2) | AVG total_amount |
| unique_customers | BIGINT | |
| unique_restaurants | BIGINT | |
| dine_in_orders | BIGINT | |
| takeaway_orders | BIGINT | |
| delivery_orders | BIGINT | |

### `d_customer_360` (Materialized View)

Customer lifetime value and behaviour profile. Sources: all silver tables.

| Column | Type | Notes |
|---|---|---|
| customer_id | STRING | |
| customer_name | STRING | |
| email | STRING | |
| city | STRING | |
| join_date | DATE | |
| total_orders | BIGINT | |
| lifetime_spend | DECIMAL(10,2) | |
| avg_order_value | DECIMAL(10,2) | |
| last_order_date | DATE | |
| loyalty_tier | STRING | Platinum ≥5000 / Gold ≥2000 / Silver ≥500 / Bronze |
| favorite_restaurant | STRING | Most-visited restaurant name |
| favorite_item | STRING | Most-ordered item name |
| avg_rating_given | DECIMAL(10,2) | |
| total_reviews | BIGINT | |
| is_vip | BOOLEAN | lifetime_spend ≥ 5000 |

### `d_restaurant_reviews` (Materialized View)

Per-restaurant review statistics. Sources: `dim_restaurant` + `fact_reviews`.

| Column | Type |
|---|---|
| restaurant_id | STRING |
| restaurant_name | STRING |
| city | STRING |
| total_reviews | BIGINT |
| avg_rating | DECIMAL(10,2) |
| rating_5_count – rating_1_count | BIGINT each |
| sentiment_positive_count | BIGINT |
| sentiment_neutral_count | BIGINT |
| sentiment_negative_count | BIGINT |
