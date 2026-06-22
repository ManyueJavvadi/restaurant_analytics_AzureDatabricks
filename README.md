# Restaurant Analytics — Azure Databricks

End-to-end real-time analytics platform for a multi-city restaurant chain, built on **Azure Event Hubs**, **Azure SQL Database**, **Lakeflow Spark Declarative Pipelines**, **Lakeflow Connect**, **Unity Catalog**, and **AI/BI Dashboards** — packaged as a **Declarative Automation Bundle (DAB)** for repeatable, environment-aware deployments.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      DATA INGESTION                                              │
│                                                                                                  │
│   streaming.orders ──► Azure Event Hubs ──► Spark Declarative Pipeline ──► 01_bronze.orders     │
│                                                                                                  │
│   ┌─────────────────┐                                                                            │
│   │  Azure SQL DB   │  customers, restaurants, menu_items, historical_orders, reviews            │
│   └────────┬────────┘                                                                            │
│            │                                                                                     │
│            ▼  Lakeflow Connect (Managed Ingestion — zero code)                                  │
│            ├──► 01_bronze.historical_orders  (one-time load)                                    │
│            ├──► 01_bronze.reviews                                                               │
│            ├──► 02_silver.dim_customers                                                         │
│            ├──► 02_silver.dim_restaurants                                                       │
│            └──► 02_silver.dim_menu_items                                                        │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

┌───────────────────┐   ┌──────────────────────────────────────┐   ┌──────────────────────────────┐
│      BRONZE        │   │               SILVER                  │   │             GOLD             │
│   01_bronze        │   │            02_silver                  │   │           03_gold            │
│                    │   │                                       │   │                              │
│  orders ──────────────► fact_orders                           │   │                              │
│                    │   │  fact_order_items                ─────────► d_sales_summary             │
│  historical_orders─────► (merged via silver pipeline)         │   │                              │
│                    │   │                                       │   │  d_customer_360 ────────────► Dashboard
│  reviews ─────────────► fact_reviews                          │   │                              │
│                    │   │  (AI: sentiment + issue flags)   ─────────► d_restaurant_reviews ──────► Mosaic AI
│                    │   │                                       │   │                              │
│                    │   │  dim_customers  ◄── Lakeflow Connect  │   │                              │
│                    │   │  dim_restaurants ◄── Lakeflow Connect │   │                              │
│                    │   │  dim_menu_items  ◄── Lakeflow Connect │   │                              │
└───────────────────┘   └──────────────────────────────────────┘   └──────────────────────────────┘

                    ┌─────────────────────────────────────────────┐
                    │              Unity Catalog                   │
                    │   Spark Declarative Pipelines | Databricks SQL│
                    └─────────────────────────────────────────────┘
```

---

## Two Data Sources — Why Both?

| Source | Type | What it carries | How it lands |
|---|---|---|---|
| **Azure Event Hubs** | Real-time stream | Live orders being placed right now | Spark Declarative Pipeline (Kafka/SASL_SSL) |
| **Azure SQL Database** | Relational batch | Master data — customers, restaurants, menus, historical orders, reviews | Lakeflow Connect (managed ingestion, no code) |

The combination lets you answer questions like: *"Which loyalty-tier customers ordered most this week, what did they order, and how did they rate the experience?"* — by joining live streaming data with SQL-sourced dimension tables in real time.

---

## Pipelines

| Pipeline | Type | Source → Target | Mode |
|---|---|---|---|
| `pipeline_ingestion_eventhub` | Spark Declarative | Event Hubs → `01_bronze.orders` | Serverless, continuous |
| `pipelline_ingestion_silver` | Lakeflow Connect (managed) | Azure SQL DB → silver dim tables | Scheduled sync |
| `pipeline_tranfm_silver` | Spark Declarative | `01_bronze` → `02_silver` (facts) | Serverless, continuous |
| `pipeline_trnsfm_gold` | Spark Declarative | `02_silver` → `03_gold` | Serverless, triggered |

Orchestrated by **`wf_daily_master_job`**: ingestion → silver → gold, in sequence, ALL_SUCCESS dependency.

---

## Tables

### Bronze — `ws_dbxprojectrc.01_bronze`
| Table | Source | Description |
|---|---|---|
| `orders` | Event Hubs (streaming) | Live order events, raw JSON parsed |
| `historical_orders` | Azure SQL via Lakeflow Connect | One-time load of past orders |
| `reviews` | Azure SQL via Lakeflow Connect | Customer review text |

### Silver — `ws_dbxprojectrc.02_silver`
| Table | Type | Description |
|---|---|---|
| `fact_orders` | Streaming Table | Validated orders with time dimensions |
| `fact_order_items` | Streaming Table | Exploded line items (one row per item) |
| `fact_reviews` | Streaming Table | Reviews enriched with AI sentiment + issue flags |
| `dim_customers` | Managed Ingestion | Customer master data from SQL |
| `dim_restaurants` | Managed Ingestion | Restaurant master data from SQL |
| `dim_menu_items` | Managed Ingestion | Menu catalogue from SQL |

### Gold — `ws_dbxprojectrc.03_gold`
| Table | Type | Description |
|---|---|---|
| `d_sales_summary` | Materialized View | Daily revenue aggregates (~£1.9M total, 10,666 orders) |
| `d_customer_360` | Materialized View | Customer lifetime value, loyalty tier, favourite items |
| `d_restaurant_reviews` | Materialized View | Per-restaurant ratings and sentiment stats |

---

## AI / ML

`fact_reviews.sql` calls `ai_query('databricks-gpt-oss-20b', ...)` on every incoming review to extract:
- **Sentiment**: positive / neutral / negative
- **Issue flags**: delivery, food quality, pricing, portion size (`true`/`false`)
- **Issue reasons**: natural language explanation per flag

Results feed directly into the **Review Insights** dashboard page and `d_restaurant_reviews` gold table.

---

## Dashboard

Two pages, built on Databricks AI/BI:

**Page 1 — Chain Performance**
Revenue totals, order counts, AOV, daily sales trend, revenue by order type (dine-in / takeaway / delivery), order volume by day of week, peak hour heatmap, best-selling items, revenue by food category.

**Page 2 — Review Insights**
Review count, avg rating, sentiment breakdown (positive / neutral / negative), issue categorisation (AI-driven), ratings distribution, review volume over time, recent review feed.

---

## Project Structure

```
restaurant-analytics/
├── databricks.yml                        # Bundle root — dev + prod targets
├── .gitignore
├── README.md
├── resources/
│   ├── pipelines/
│   │   ├── ingestion_eventhub.yml        # Bronze ingestion pipeline config
│   │   ├── silver_transform.yml          # Silver transformation pipeline config
│   │   └── gold_transform.yml            # Gold aggregation pipeline config
│   ├── jobs/
│   │   └── daily_master_job.yml          # Master orchestration job
│   └── dashboards/
│       └── restaurant_analytics_dashboard.yml
├── src/
│   ├── ingestion/
│   │   └── eventhub.py                   # Event Hub → bronze streaming
│   ├── silver/
│   │   ├── fact_orders.py                # Order fact table + data quality
│   │   ├── fact_order_items.py           # Exploded line items
│   │   ├── fact_reviews.sql              # AI-enriched review analysis
│   │   ├── dim_customers.py              # Stub — managed ingestion (see file)
│   │   └── dim_restaurant.py             # Stub — managed ingestion (see file)
│   └── gold/
│       ├── d_sales_summary.py            # Daily revenue aggregates
│       ├── d_customers_360.py            # Customer 360 view
│       └── d_restaurant_reviews.py       # Per-restaurant review stats
├── dashboards/
│   └── restaurant_analytics_dashboard.lvdash.json
├── conf/
│   ├── dev/variables.yml                 # Dev environment variables
│   └── prod/variables.yml                # Prod environment variables
├── docs/
│   ├── architecture.md
│   ├── data_model.md
│   └── runbook.md
└── tests/unit/
```

---

## Quick Start

### 1. Secret Setup (one-time)
```bash
databricks secrets create-scope restaurant-analytics
databricks secrets put-secret restaurant-analytics eh-connection-string
# Paste full Event Hub connection string when prompted
```

### 2. Deploy
```bash
databricks bundle validate
databricks bundle deploy -t dev
```

```bash
# Production
databricks bundle deploy -t prod --var="warehouse_id=<your-warehouse-id>"
```

### 3. Run the Master Job
```bash
databricks bundle run -t dev daily_master_job
```

---

## Environment Variables

Before deploying, fill in `conf/dev/variables.yml` and `conf/prod/variables.yml`:

| Variable | Description | Where to find it |
|---|---|---|
| `warehouse_id` | SQL Warehouse ID for the dashboard | SQL Warehouses → your warehouse → Connection Details |
| `catalog_name` | Unity Catalog name | Default: `ws_dbxprojectrc` |
| `notification_email` | Job failure alerts | Your email |

---

## Security

The Event Hub connection string is **never committed to Git**. It lives in a Databricks Secret Scope:

| Scope | Key |
|---|---|
| `restaurant-analytics` | `eh-connection-string` |

Referenced in pipeline config as `{{secrets/restaurant-analytics/eh-connection-string}}`.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Streaming ingest | Azure Event Hubs + Kafka protocol |
| Batch / dimension ingest | Azure SQL Database + Lakeflow Connect |
| Pipeline engine | Lakeflow Spark Declarative Pipelines (serverless) |
| Storage & governance | Unity Catalog (Delta Lake) |
| AI enrichment | Databricks `ai_query()` — `databricks-gpt-oss-20b` |
| Orchestration | Lakeflow Jobs |
| Visualisation | Databricks AI/BI Dashboards |
| Deployment | Declarative Automation Bundles (DAB) |
| Cloud | Microsoft Azure |
