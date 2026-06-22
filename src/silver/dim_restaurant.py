# dim_restaurant — Managed Ingestion (Lakeflow Connect)
#
# This table is NOT authored as pipeline Python/SQL code.
# It is managed by the 'pipelline_ingestion_silver' managed ingestion pipeline
# (pipeline ID: 508b0758-c087-4e83-ac85-1ea552f169a8) which syncs data
# from an external source directly into ws_dbxprojectrc.02_silver.dim_restaurant.
#
# Schema (02_silver.dim_restaurant):
#   restaurant_id  STRING
#   name           STRING
#   city           STRING
#   (additional columns as configured in managed ingestion)
#
# To manage or reconfigure this pipeline, navigate to:
# Jobs & Pipelines > pipelline_ingestion_silver in the Databricks workspace UI.
#
# If you migrate to a code-driven approach, implement the ingestion logic here
# using Auto Loader or COPY INTO from the source system.
