# ShopFlow Data Extraction

Simple and straightforward data extraction scripts for the ShopFlow Customer Intelligence Platform.

## 📦 Local Output Location

- Default path (host): `data_extraction/local_output`
- Within containers: `/opt/airflow/project/data_extraction/local_output`
- Override root with env var: `LOCAL_OUTPUT_ROOT`
- Local-only testing: set `SKIP_S3_UPLOAD=1` to skip S3 uploads

Example (write only `customers` locally via Docker):

```powershell
docker-compose exec \
    -e SKIP_S3_UPLOAD=1 \
    -e RDS_TABLES=customers \
    airflow \
    python /opt/airflow/project/data_extraction/extraction/data_extraction/extract_rds_to_s3.py

# Verify on host
Get-ChildItem .\data_extraction\local_output\raw -Recurse | Select-Object FullName,Length | Format-Table -AutoSize
```

Note: Older runs may have created `data_extraction/extraction/data_extraction/local_output`. The extractors no longer write there. You can safely delete that duplicate folder after verifying files in the top-level path.

## 📁 Project Structure

```
data_engineering/extraction/
├── extract_rds_to_s3.py          # Extract from PostgreSQL RDS
├── extract_api_to_s3.py          # Extract from Support Tickets API
├── requirements.txt              # Python dependencies
└── logs/                        # Extraction logs
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
Consolidated, testable extractors and helpers for the ShopFlow Customer Intelligence Platform.

This folder contains the canonical extraction scripts and supporting utilities used to pull raw data from
the RDS PostgreSQL instance and the Support Tickets API, convert to Parquet, and upload (or write locally)
for downstream processing with dbt.

### 2. Configure Connection
├── data_extraction/
│   ├── _common.py               # Shared helpers (S3, parquet, .env loader, DQ)
│   ├── data_quality.py          # Advanced local DQ checks (optional)
│   ├── extract_rds_to_s3.py     # RDS extractor (uses `_common`)
│   ├── extract_api_to_s3.py     # API extractor (uses `_common`)
│   ├── local_output/            # Local fallback outputs written during dry-runs
│   └── tests/                   # Smoke-tests + harness
├── requirements.txt             # Python dependencies
└── logs/                        # Extraction logs
# AWS Configuration
Create or update the `.env` file at the repository root with your credentials. The project provides an
idempotent loader (`_common.load_env_once()`) that will preserve existing environment variables and
avoid re-loading the file repeatedly.

Example `.env` keys used by the extractors:
S3_BUCKET="shopflow-intel-dev"
SHOPFLOW_API_URL="https://api.sabisave.info"
SHOPFLOW_API_KEY="shopflow-training-key"
SHOPFLOW_API_ENDPOINT="/tickets"
RDS_PORT=5432
Running locally (dry-run, writes local Parquet and skips S3 uploads):

```powershell
python run_extract_dry_with_env.py
```

Notes:
- `run_extract_dry_with_env.py` loads `.env` (idempotently), sets `SKIP_S3_UPLOAD=1` by default, and runs
    the API extractor followed by the RDS extractor. This is the recommended way to test extraction locally.
- To run full uploads to S3, ensure AWS credentials are available and run the extractor modules directly or
    run a production runner that sets `SKIP_S3_UPLOAD=0`.
API_ENDPOINT="/tickets"
- ✅ `support_tickets` → ~50,000 records (paginated)
### 3. Run Extractions
By default extractors write local fallback copies to `data_engineering/extraction/data_extraction/local_output/`
and upload to S3 when `SKIP_S3_UPLOAD` is not set. S3 layout (when uploaded) follows this convention:
**Extract from RDS PostgreSQL:**
└── raw/
        ├── {table}/extract_date=YYYY-MM-DD/{table}_{ts}.parquet
        └── support_tickets/extract_date=YYYY-MM-DD/support_tickets_{ts}.parquet
```
What it does:
- Loads config via the centralized `.env` loader
- Connects to RDS PostgreSQL and reads configured tables
- Converts results to Parquet (in-memory) and writes local copies + optional S3 upload

Key features:
- Uses `data_extraction/_common.py` for Parquet conversion, local write, and S3 handling
- Honors `SKIP_S3_UPLOAD` for safe local testing
- Calls `run_dq_if_enabled()` when `RUN_DQ=1`
- ✅ `products` → 5,000 records
What it does:
- Loads config via centralized loader
- Fetches tickets from the Support Tickets API using a paginated, retrying HTTP session
- Converts to Parquet and writes local copies + optional S3 upload

Key features:
- Automatic pagination (page size capped at API max)
- Safe dry-run via `SKIP_S3_UPLOAD`
- Resilient HTTP session with retries
## 📦 Output Location
Update the `.env` file at project root with your credentials. The new idempotent loader
(`_common.load_env_once()`) is used by the canonical runner and individual extractors.
All data is uploaded to S3 in Parquet format with date partitions:
| `SHOPFLOW_API_URL` | API base URL | `https://api.sabisave.info` |
| `SHOPFLOW_API_KEY` | API key | `shopflow-training-key` |
```
After extraction completes:
1. Verify local Parquet files under `data_engineering/extraction/data_extraction/local_output/` (dry-run) or
     verify objects in S3 when `SKIP_S3_UPLOAD` is disabled.
2. Run dbt transformations in `dbt_shopflow/` to build staging and curated layers.
3. Optionally enable `RUN_DQ=1` to run local data quality checks after extraction.
    ├── products/extract_date=2024-12-07/products.parquet
There are utilities to export dbt staging/curated outputs to S3/parquet if needed:
**Script:** `data_engineering/extraction/export_staging_to_s3.py`
**What it does:**
        - Connects to the project's Postgres using `.env` credentials
        - Discovers tables/views in schema `analytics_staging` where names start with `stg_`
        - Exports each non-empty model to `s3://{S3_BUCKET}/staging/{model}/extract_date=YYYY-MM-DD/{model}_{ts}.parquet`

### `extract_rds_to_s3.py`
**What it does:**
1. Loads config from `.env` file
2. Connects to RDS PostgreSQL
5. Uploads to S3 raw layer with date partition

**Key features:**
- Configuration validation
- Error handling per table
### `extract_api_to_s3.py`
**What it does:**
1. Loads config from `.env` file
2. Fetches tickets from API with pagination (1000 per page)
3. Handles retries and rate limiting
4. Converts to Parquet format
5. Uploads to S3 raw layer

**Key features:**
- Automatic pagination
- Rate limit protection (0.5s delay)
- Configuration validation
- Logging for debugging
- 130 lines of code

## 🔐 Environment Variables

Update the `.env` file at project root with your credentials.

| Variable | Description | Example |
|----------|-------------|---------|
| `RDS_HOST` | RDS endpoint | `ecommerce-db.xxxxx.rds.amazonaws.com` |
| `RDS_PORT` | RDS port | `5432` |
| `RDS_DB` | Database name | `postgres` |
| `RDS_USER` | Database user | `ecommerce_user` |
| `RDS_PASSWORD` | Database password | `YourPassword123` |
| `RDS_TABLES` | Tables to extract | `customers,orders,products,events,inventory` |
| `S3_BUCKET` | S3 bucket name | `shopflow-intel-dev` |
| `AWS_REGION` | AWS region | `us-east-1` |
| `API_BASE_URL` | API base URL | `https://api.sabisave.info` |
| `API_KEY` | API key | `shopflow-training-key` |

## 🔐 AWS Credentials

Ensure AWS credentials are configured:

```bash
# Option 1: Environment variables
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"

# Option 2: AWS CLI profile
aws configure
```

## 📝 Example Output

```
============================================================
Starting RDS to S3 Extraction Process
============================================================
2024-12-07 10:00:01 - INFO - Configuration validated successfully
2024-12-07 10:00:01 - INFO - Connecting to RDS PostgreSQL...
2024-12-07 10:00:02 - INFO - Connected successfully!
2024-12-07 10:00:02 - INFO - Extracting table: customers
2024-12-07 10:00:05 - INFO - Extracted 100000 rows from customers
2024-12-07 10:00:08 - INFO - Uploading customers to s3://shopflow-intel-dev/raw/customers/...
2024-12-07 10:00:10 - INFO - Upload complete for customers
2024-12-07 10:00:10 - INFO - ✓ Successfully processed customers
...
============================================================
✓ Extraction process completed!
============================================================
```

## 🎯 Next Steps

After extraction completes:
1. ✅ Verify data in S3 bucket
2. → Proceed to **dbt transformations** (Team B)
3. → Build staging and curated layers

## 🐛 Troubleshooting

**RDS Connection Error:**
```
Check RDS endpoint and credentials in .env
Verify RDS security group allows your IP
```

**API Error 401:**
```
Verify API key is correct in .env
Check API endpoint URL
```

**S3 Upload Error:**
```
Check AWS credentials are configured
Verify S3 bucket exists and permissions are correct
```

**Missing environment variables:**
```
Ensure all required variables are in .env file
Check for typos in variable names
```

## 👥 Team

**Data Engineering Team A - Extraction**
- Owner: Responsible for raw data layer
- Handoff: To Team B after completion
- Success Criteria: All tables extracted to S3 by Dec 4

## 🗄️ Staging Export Script

We've added a helper to export dbt staging models to the S3 staging layer as Parquet files.

- **Script:** `data_engineering/extraction/export_staging_to_s3.py`
- **What it does:**
    - Connects to the project's Postgres using `.env` credentials
    - Discovers tables/views in schema `analytics_staging` where names start with `stg_`
    - Exports each non-empty model to `s3://{S3_BUCKET}/staging/{model}/extract_date=YYYY-MM-DD/{model}_{ts}.parquet`

Usage:
```powershell
python data_engineering\extraction\export_staging_to_s3.py
```

Notes:
- The script reads `S3_BUCKET`, RDS connection vars, and AWS creds from `.env` or the environment.
- Large tables are loaded into memory; if memory is a concern, consider exporting by chunk or using a streaming approach.

Example S3 path created by the script:
```
s3://shopflow-intel-dev/staging/stg_support_tickets/extract_date=2025-12-09/stg_support_tickets_20251209T102020Z.parquet
```

Notes:
- This script queries the `analytics_staging` schema (overridable with `DBT_SCHEMA` env var).
- It discovers staging models by scanning `dbt_shopflow/models/staging/stg_*.sql`.
- If you prefer different S3 layout (e.g., drop the `stg_` prefix in folder names), let me know and I can adjust.
