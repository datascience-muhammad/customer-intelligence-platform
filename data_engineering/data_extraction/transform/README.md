# ShopFlow Transform Utilities

This folder contains helper scripts used to export curated dbt outputs and publish dbt artifacts to S3.

Contents

- `export_curated_to_s3.py` — Export curated dbt models from Postgres to Parquet and upload to S3.
- `publish_dbt_docs_to_s3.py` — Publish dbt `target/` artifacts (docs, catalog, run_results) to S3.

Purpose

These scripts are convenience utilities for packaging dbt outputs and making them available to other teams or
for archival. They are not replacements for dbt itself — run dbt in `dbt_shopflow/` to build models and
generate `target/` artifacts first.

Quick Start

1. Ensure dbt models are built:

```powershell
# from repo root
cd dbt_shopflow
# run dbt locally (example)
dbt run --profiles-dir ..\profiles.yml
```

2. Populate environment variables in the repository `.env` (or system environment). The scripts try to load
   a `.env` found upward from their location.

Key environment variables

- `S3_BUCKET` — S3 bucket to upload to (required)
- AWS credentials — `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` (optional if using instance profiles)
- Postgres/RDS credentials for querying curated models when using `export_curated_to_s3.py`: `RDS_HOST`, `RDS_DB`, `RDS_USER`, `RDS_PASSWORD`, `RDS_PORT`
- `DBT_SCHEMA` (optional) — target schema where curated models live; otherwise the script attempts to read the schema from `dbt_shopflow/profiles.yml`.

Usage

Export curated models to S3:

```powershell
python data_engineering\transform\export_curated_to_s3.py
```

Publish dbt artifacts (target/) to S3:

```powershell
python data_engineering\transform\publish_dbt_docs_to_s3.py
```

Notes & Best Practices

- These scripts load `.env` by searching upward; for consistent behavior prefer the centralized loader in
  `data_engineering/extraction/data_extraction/_common.py` where possible (i.e., call `_common.load_env_once()` in
  custom runners).
- Large curated models may require significant memory; run these scripts on a machine with sufficient RAM or
  modify to stream/export in chunks.
- Uploaded S3 keys are timestamped under `curated/` or `dbt_docs/` with `extract_date=YYYY-MM-DD` prefixes.

Examples of S3 paths created

- Curated model:
  `s3://{S3_BUCKET}/curated/dim_customers/extract_date=2025-12-16/dim_customers_20251216T205205Z.parquet`
- dbt docs:
  `s3://{S3_BUCKET}/dbt_docs/extract_date=2025-12-16/index.html`

If you'd like, I can:
- Switch the transform scripts to use `_common.load_env_once()` to standardize loading, or
- Add a small runner `run_transform_with_env.py` similar to the extraction runner for idempotent env loading and dry-run behavior.
