# Architecture

## Overview

End-to-end streaming analytics platform for a multi-city restaurant chain. Data flows from Azure Event Hubs through three medallion layers (Bronze → Silver → Gold) to an AI/BI Dashboard, all managed as Declarative Automation Bundles.

## Pipeline Flow

```
Azure Event Hubs (evh-ns-dbxprojectrc, topics: orders / reviews)
        |
        v (Kafka / SASL_SSL, connection string in secret scope)
[pipeline_ingestion_eventhub]  serverless SDP, continuous
  src/ingestion/eventhub.py
  → 01_bronze.orders (Streaming Table)
        |
        v
[pipeline_tranfm_silver]  serverless SDP, continuous
  src/silver/fact_orders.py
  src/silver/fact_order_items.py
  src/silver/fact_reviews.sql  ← uses ai_query() for sentiment + issue extraction
  → 02_silver.fact_orders, fact_order_items, fact_reviews (Streaming Tables)

  [pipelline_ingestion_silver]  managed ingestion (Lakeflow Connect)
  → 02_silver.dim_customers, dim_restaurant
        |
        v
[pipeline_trnsfm_gold]  serverless SDP, triggered
  src/gold/d_sales_summary.py
  src/gold/d_customers_360.py
  src/gold/d_restaurant_reviews.py
  → 03_gold.d_sales_summary, d_customer_360, d_restaurant_reviews (Materialized Views)
        |
        v
[Restaurant Analytics Dashboard]
  Page 1: Chain Performance (revenue, orders, AOV, peak hours, food categories)
  Page 2: Review Insights (sentiment, issue breakdown, recent feed)
```

## Orchestration

`wf_daily_master_job` sequences the three pipelines (ingestion → silver → gold). All tasks use ALL_SUCCESS dependency, max_concurrent_runs=1, with queue enabled.

## AI/ML

`fact_reviews.sql` calls `ai_query('databricks-gpt-oss-20b', ...)` per review row to extract structured sentiment and four issue flags (delivery, food quality, pricing, portion size) plus per-issue reason text.

## Security

Event Hub connection string is stored in Databricks Secret Scope `restaurant-analytics`, key `eh-connection-string`. Referenced in pipeline config as `{{secrets/restaurant-analytics/eh-connection-string}}`. Never committed to Git.
