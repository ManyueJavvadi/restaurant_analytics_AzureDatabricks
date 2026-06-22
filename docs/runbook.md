# Runbook

Operational guide for deploying, running, and troubleshooting the Restaurant Analytics bundle.

---

## 1. Prerequisites

* Databricks CLI installed and authenticated (`databricks auth login` or `.databrickscfg` configured)
* Access to the `ws_dbxprojectrc` Unity Catalog catalog
* Git installed locally (or use the workspace terminal)
* GitHub repo access: `https://github.com/ManyueJavvadi/restaurant_analytics_AzureDatabricks.git`

---

## 2. First-Time Secret Setup

The Event Hub connection string must be stored in a Databricks Secret Scope before deploying. **Never commit it to Git.**

```bash
# Create the secret scope (one-time)
databricks secrets create-scope restaurant-analytics

# Store the Event Hub connection string
databricks secrets put-secret restaurant-analytics eh-connection-string
# Paste the full connection string when prompted:
# Endpoint=sb://evh-ns-dbxprojectrc.servicebus.windows.net/;SharedAccessKeyName=...;SharedAccessKey=...
```

Verify:
```bash
databricks secrets list-secrets restaurant-analytics
```

---

## 3. Deploy

### Validate the bundle
```bash
cd /Workspace/Users/manyueinfo@gmail.com/restaurant-analytics
databricks bundle validate
```

### Deploy to dev
```bash
databricks bundle deploy -t dev
```

### Deploy to prod
```bash
databricks bundle deploy -t prod --var="warehouse_id=<your-sql-warehouse-id>"
```

To find your SQL Warehouse ID: go to SQL Warehouses in the workspace UI → click your warehouse → Connection Details → the ID is the hex string in the Server hostname (e.g. `aef6789abc123456`).

---

## 4. Run the Master Job

```bash
# Trigger one run of the full pipeline sequence (dev)
databricks bundle run -t dev daily_master_job

# Check run status
databricks jobs list-runs --job-name wf_daily_master_job
```

---

## 5. Exporting the Dashboard Artifact

The `.lvdash.json` file in `dashboards/` must be manually exported from the workspace UI after first deployment (it cannot be auto-exported via CLI from this page):

1. Open the Databricks workspace UI
2. Navigate to the **Restaurant Analytics Dashboard**
3. Click the **three-dot menu (⋯)** at the top right of the dashboard
4. Select **Download dashboard definition**
5. Save the downloaded file as:
   `restaurant-analytics/dashboards/restaurant_analytics_dashboard.lvdash.json`
6. Commit and push the file to Git

---

## 6. Monitoring & Troubleshooting

### Check pipeline status
In the workspace UI: **Jobs & Pipelines** → filter by Pipelines → click the pipeline name to see event logs and last run status.

Or via CLI:
```bash
databricks pipelines get --pipeline-id <pipeline-id>
```

### Silver pipeline fails (fact_reviews)
The `fact_reviews.sql` transformation calls `ai_query('databricks-gpt-oss-20b', ...)` for every incoming review. If this pipeline fails or slows significantly:
* Check the pipeline event log for `ai_query` errors
* Verify the model endpoint `databricks-gpt-oss-20b` is available (Foundation Model API status page)
* Check for token rate-limit errors — reduce batch size or add retry logic if needed
* Validate that `01_bronze.reviews` is receiving data (check ingestion pipeline)

### Event Hub ingestion stops
If `pipeline_ingestion_eventhub` stops producing data:
* Confirm the secret `restaurant-analytics/eh-connection-string` is still valid (keys rotate)
* Re-run `databricks secrets put-secret restaurant-analytics eh-connection-string` with the updated key
* Restart the pipeline: Jobs & Pipelines → pipeline_ingestion_eventhub → Start
* Check the Event Hub namespace in Azure Portal for quota/throttling events

### Gold pipeline produces stale data
* The gold pipeline (`pipeline_trnsfm_gold`) is triggered (not continuous) — it runs when the master job calls it
* If the dashboard shows stale numbers, check that `wf_daily_master_job` completed successfully
* Manually trigger a gold refresh: `databricks bundle run -t dev daily_master_job`

---

## 7. Push to GitHub

Run these commands from the workspace terminal or locally after cloning:

```bash
cd /Workspace/Users/manyueinfo@gmail.com/restaurant-analytics

git init
git remote add origin https://github.com/ManyueJavvadi/restaurant_analytics_AzureDatabricks.git
git add -A
git commit -m "Initial restaurant analytics bundle scaffold"
git push -u origin main
```

> If the branch is `master` instead of `main`:
> ```bash
> git push -u origin master
> ```

> If the remote already has commits (non-empty repo), pull first:
> ```bash
> git pull origin main --allow-unrelated-histories
> git push -u origin main
> ```
