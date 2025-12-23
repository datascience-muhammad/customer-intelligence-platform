# ShopFlow ETL Data Pipeline

## Overview

ShopFlow is a production-ready end-to-end data engineering pipeline that extracts e-commerce data from multiple sources (PostgreSQL RDS and REST API), transforms it using dbt, and delivers analytics-ready datasets for business intelligence and machine learning.

## Project Structure

```
ShopFlow_Project/
├── airflow/
│   └── dags/              # Airflow DAG definitions
├── config/                # Configuration files (.env, settings)
├── data_engineering/
│   ├── extraction/        # Data extraction scripts
│   │   └── data_extraction/
│   ├── transform/         # Export and transformation utilities
│   └── local_output/      # Local data storage (raw/staging/curated)
├── dbt_shopflow/          # dbt project (models, tests, docs)
│   ├── models/
│   │   ├── staging/       # Staging views
│   │   └── curated/       # Analytics tables
│   ├── macros/
│   └── tests/
├── docker/                # Docker configuration
├── docs/                  # Documentation
├── logs/                  # Application logs
├── primecart-terraform/   # Infrastructure as Code
├── scripts/               # Utility scripts
└── docker-compose.yml     # Docker orchestration

## Pipeline Architecture

```
extract_rds ──┐
              ├──> ingest ──> dbt_transform ──> export_local ──> export_s3
extract_api ──┘                    │
                                   ├─> staging layer (6 views)
                                   └─> curated layer (7 tables)
```

### Pipeline Stages

1. **Extract (Parallel)**
   - `extract_rds_to_s3`: Extracts 5 tables from PostgreSQL RDS (customers, orders, products, events, inventory)
   - `extract_api_to_s3`: Pulls support tickets from REST API
   - Output: Parquet files in `local_output/raw/` + S3 (optional)

2. **Ingest**
   - `ingest_parquet_to_postgres`: Loads parquet files into Postgres `raw` schema
   - Uses idempotent upsert logic (INSERT ON CONFLICT DO UPDATE)
   - Handles 2.6M+ rows total

3. **Transform (dbt)**
   - **Staging Layer** (6 views in `raw_staging` schema)
     - `stg_customers`: Deduped customers with normalized email
     - `stg_orders`: Cleaned orders with status normalization
     - `stg_products`: Product catalog with category classification
     - `stg_events`: User behavior events (page views, clicks, purchases)
     - `stg_inventory`: Stock levels with warehouse mapping
     - `stg_support_tickets`: Customer support data with SLA tracking
   
   - **Curated Layer** (7 tables in `raw_curated` schema)
     - `dim_customers`: Customer dimension with RFM segmentation (100K rows)
     - `dim_products`: Product dimension with pricing/margin (5K rows)
     - `dim_dates`: Date dimension for time intelligence (1065 rows)
     - `fact_orders`: Order fact table with full transaction history (500K rows)
     - `fact_events`: Event fact table for behavioral analytics (2M rows)
     - `ml_features`: Customer features for churn prediction (100K rows)
     - `support_tickets`: Support ticket analytics with satisfaction scores (50K rows)

4. **Export**
   - `export_local`: Exports all schemas to local parquet files
   - `export_s3_curated`: Optionally uploads curated models to S3

## Data Volumes

| Schema | Tables | Total Rows | Disk Size |
|--------|--------|------------|-----------|
| raw | 6 | 2,665,926 | 351 MB |
| raw_staging | 6 views | - | - |
| raw_curated | 7 | 2,856,065 | 216 MB |

## Quick Start

### Prerequisites
- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- 8GB+ RAM recommended
- 2GB free disk space
- AWS credentials configured (for S3 access)

### 1. Environment Setup

```bash
# Copy the example environment file
cp config/.env-backup config/.env

# Edit config/.env and set your credentials:
# - AWS_ACCESS_KEY_ID
# - AWS_SECRET_ACCESS_KEY
# - RDS_HOST, RDS_USER, RDS_PASSWORD
# - API_KEY (if applicable)
```

### 2. Start the Pipeline

```bash
# Start all Docker services
docker-compose up -d

# Wait for Airflow to initialize (~2 minutes)
# Access Airflow UI: http://localhost:8081
# Username: admin / Password: admin
```

### 3. Trigger the DAG

```bash
# Trigger the complete ETL pipeline from Airflow UI or CLI
# Via UI: http://localhost:8081 -> Enable and trigger 'shopflow_etl_rds'
# Via CLI:
docker-compose exec airflow airflow dags trigger shopflow_etl_rds
```

### 4. Verify Results

```bash
# Check pipeline execution status in Airflow UI
# Data will be available in:
# - Local: data_engineering/local_output/curated/*.parquet
# - S3: s3://your-bucket/curated/
# - Postgres: raw, raw_staging, raw_curated schemas
``` 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname IN ('raw', 'raw_staging', 'raw_curated')
ORDER BY schemaname, tablename;
```

## Configuration

### Environment Variables

Set these in `docker-compose.yml` or `.env` file:

- **Postgres Connection**
  - `DBT_POSTGRES_HOST`: postgres (default)
  - `DBT_POSTGRES_PORT`: 5432
  - `DBT_POSTGRES_USER`: airflow
  - `DBT_POSTGRES_PASSWORD`: airflow
  - `DBT_POSTGRES_DBNAME`: airflow
  - `DBT_POSTGRES_SCHEMA`: raw

- **S3 Upload (Optional)**
  - `SKIP_S3_UPLOAD`: 1 (set to 0 to enable S3 uploads)
  - `S3_BUCKET`: your-bucket-name
  - `AWS_ACCESS_KEY_ID`: your-key
  - `AWS_SECRET_ACCESS_KEY`: your-secret

### Airflow Variables

Set these in Airflow UI → Admin → Variables:

- `ENABLE_DBT`: 1 (enables dbt transformation step)
- `SKIP_S3_UPLOAD`: 1 (disables S3 upload in export tasks)
- `S3_BUCKET`: target bucket for exports

## Project Structure

```
ShopFlow_Project/
├── airflow/
│   └── dags/
│       ├── etl_pipeline_rds.py       # Main DAG orchestration
│       └── etl_pipeline_api.py       # API extraction DAG
├── dbt_shopflow/
│   ├── models/
│   │   ├── staging/                   # 6 staging views
│   │   │   ├── stg_customers.sql
## Additional Documentation

- [Deployment Guide](docs/DEPLOYMENT.md) - Docker and Airflow setup
- [Quick Reference](docs/QUICK_REFERENCE.md) - Common commands and operations
- [dbt Documentation](dbt_shopflow/docs/data_dictionary.md) - Data models and schemas
- [API Documentation](data_engineering/extraction/README.md) - Extraction details

## Data Quality & Testing

The pipeline includes comprehensive data quality checks through dbt tests:

### dbt Tests
- **Not Null Tests**: Ensure critical fields are populated
- **Unique Tests**: Verify primary key uniqueness
- **Relationship Tests**: Validate foreign key integrity
- **Custom Tests**: Business logic validation

Run tests:
```bash
# Execute all dbt tests
docker-compose exec airflow bash -c "cd /opt/airflow/project/dbt_shopflow && dbt test"
```

## Monitoring & Logs

### Application Logs
- Airflow logs: `logs/airflow/`
- dbt logs: `dbt_shopflow/logs/`

### Monitoring
- Airflow UI: http://localhost:8081
- View DAG execution history, task logs, and metrics

## Troubleshooting

### Common Issues

1. **Docker containers not starting**
   ```bash
   # Check logs
   docker-compose logs scheduler
   docker-compose logs airflow
   
   # Restart services
   docker-compose restart
   ```

2. **DAG not appearing in UI**
   ```bash
   # Force DAG refresh
   docker-compose exec airflow airflow dags list
   ```

3. **Database connection errors**
   - Verify credentials in `config/.env`
   - Check network connectivity
   - Ensure RDS security groups allow access

## Contributing

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Technology Stack

- **Orchestration**: Apache Airflow 2.8+
- **Container Runtime**: Docker Compose
- **Database**: PostgreSQL 14
- **Transformation**: dbt 1.5+
- **Data Format**: Apache Parquet
- **Storage**: Local filesystem + AWS S3
- **Language**: Python 3.11+

## License

MIT License - See LICENSE file for details
