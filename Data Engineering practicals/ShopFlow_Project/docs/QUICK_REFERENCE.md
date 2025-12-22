# DBT + Docker Airflow - Quick Reference Card

## 🚀 Quick Start Commands

### Start Services
```bash
cd "c:\Users\David Ibanga\Data Engineering practicals\ShopFlow_Project"
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

### View Logs
```bash
docker-compose logs -f airflow
```

---

## 🔗 Access Points

| Service | URL | Username | Password |
|---------|-----|----------|----------|
| **Airflow UI** | http://localhost:8081 | admin | admin |
| **PostgreSQL** | localhost:5433 | airflow | airflow |

---

## 📦 Local Output (Extraction)

- Default path: data_extraction/local_output/raw
- Override root: set `LOCAL_OUTPUT_ROOT` in `.env`
- Local-only mode: set `SKIP_S3_UPLOAD=1` to skip S3

Example: run a single-table RDS extract (customers) and write locally
```powershell
docker-compose exec \
  -e SKIP_S3_UPLOAD=1 \
  -e RDS_TABLES=customers \
  airflow \
  python /opt/airflow/project/data_extraction/extraction/data_extraction/extract_rds_to_s3.py

# Verify on host (PowerShell)
Get-ChildItem .\data_extraction\local_output\raw -Recurse | Select-Object FullName,Length | Format-Table -AutoSize
```

---

## 📊 dbt Commands (with Docker)

### Debug Connection
```bash
docker-compose exec \
  -e DBT_POSTGRES_HOST=postgres \
  -e DBT_POSTGRES_PORT=5432 \
  -e DBT_POSTGRES_USER=airflow \
  -e DBT_POSTGRES_PASSWORD=airflow \
  -e DBT_POSTGRES_DBNAME=airflow \
  -e DBT_POSTGRES_SCHEMA=raw \
  airflow \
  dbt debug --project-dir /opt/airflow/project/dbt_shopflow
```

### Run Models
```bash
docker-compose exec \
  -e DBT_POSTGRES_HOST=postgres \
  -e DBT_POSTGRES_PORT=5432 \
  -e DBT_POSTGRES_USER=airflow \
  -e DBT_POSTGRES_PASSWORD=airflow \
  -e DBT_POSTGRES_DBNAME=airflow \
  -e DBT_POSTGRES_SCHEMA=raw \
  airflow \
  dbt run --project-dir /opt/airflow/project/dbt_shopflow
```

### Run Tests
```bash
docker-compose exec \
  -e DBT_POSTGRES_HOST=postgres \
  -e DBT_POSTGRES_PORT=5432 \
  -e DBT_POSTGRES_USER=airflow \
  -e DBT_POSTGRES_PASSWORD=airflow \
  -e DBT_POSTGRES_DBNAME=airflow \
  -e DBT_POSTGRES_SCHEMA=raw \
  airflow \
  dbt test --project-dir /opt/airflow/project/dbt_shopflow
```

### Generate Docs
```bash
docker-compose exec \
  -e DBT_POSTGRES_HOST=postgres \
  -e DBT_POSTGRES_PORT=5432 \
  -e DBT_POSTGRES_USER=airflow \
  -e DBT_POSTGRES_PASSWORD=airflow \
  -e DBT_POSTGRES_DBNAME=airflow \
  -e DBT_POSTGRES_SCHEMA=raw \
  airflow \
  dbt docs generate --project-dir /opt/airflow/project/dbt_shopflow
```

---

## 📁 dbt Models

### Staging Views (raw_staging schema)
- `stg_customers` - Cleaned customer data
- `stg_orders` - Cleaned order data  
- `stg_products` - Cleaned product data
- `stg_events` - Cleaned event data
- `stg_inventory` - Cleaned inventory data
- `stg_support_tickets` - Cleaned support tickets

### Curated Tables (raw_curated schema)
- [Pending models to be configured]

---

## 🐳 Docker Commands

### Check Status
```bash
docker-compose ps
```

### Restart Services
```bash
docker-compose restart
```

### Remove Everything (WARNING: Deletes data)
```bash
docker-compose down -v
```

### Execute Command in Container
```bash
docker-compose exec airflow [command]
```

### Copy Files To/From Container
```bash
# To container
docker cp file.txt shopflow_project-airflow-1:/tmp/

# From container
docker cp shopflow_project-airflow-1:/tmp/file.txt ./
```

---

## 📝 Database Commands

### Connect to PostgreSQL
```bash
psql -h localhost -p 5433 -U airflow -d airflow
```

### List All Schemas
```sql
\dn
```

### List Tables in raw Schema
```sql
SELECT table_name FROM information_schema.tables WHERE table_schema='raw';
```

### View Data
```sql
SELECT * FROM raw.customers LIMIT 10;
SELECT * FROM raw_staging.stg_customers LIMIT 10;
```

---

## ✅ Verification Checklist

- [ ] `docker-compose ps` shows 3 containers running
- [ ] Can access http://localhost:8081 (Airflow UI)
- [ ] Can connect to postgres on port 5433
- [ ] `dbt debug` shows [OK connection ok]
- [ ] `dbt run` completes without errors
- [ ] `dbt test` passes all tests
- [ ] `dbt docs generate` creates documentation

---

## 🔧 Environment Variables

### Container Environment
```
AIRFLOW_HOME=/opt/airflow
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__CORE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres:5432/airflow
DBT_POSTGRES_HOST=postgres
DBT_POSTGRES_PORT=5432
DBT_POSTGRES_USER=airflow
DBT_POSTGRES_PASSWORD=airflow
DBT_POSTGRES_DBNAME=airflow
DBT_POSTGRES_SCHEMA=raw
```

### In .env File
```
AIRFLOW__CORE__FERNET_KEY=[your-key]
ENABLE_DBT=1
SKIP_S3_UPLOAD=1
```

---

## 📚 Documentation Files

- **[DBT_DOCKER_AIRFLOW_GUIDE.md](./DBT_DOCKER_AIRFLOW_GUIDE.md)** - Full setup guide
- **[DBT_TEST_REPORT.md](./DBT_TEST_REPORT.md)** - Detailed test results
- **[README.md](./README.md)** - Project overview
- **[README_AIRFLOW_DOCKER.md](./README_AIRFLOW_DOCKER.md)** - Airflow details

---

## 🆘 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Can't access Airflow UI | Check: `docker-compose ps` and `docker-compose logs airflow` |
| dbt connection fails | Verify: `psql -h localhost -p 5433 -U airflow -d airflow` |
| Models not found | Create raw schema tables or run extraction pipeline |
| Permission denied errors | Check database user permissions |
| Out of memory | Reduce dbt threads: modify `profiles.yml` |

---

## 📞 Common Tasks

### Trigger Airflow DAG
1. Go to http://localhost:8081
2. Find "shopflow_etl_rds" DAG
3. Click the play button
4. Wait for completion

### View dbt Documentation
1. Run: `dbt docs generate`
2. Docs created at: `/opt/airflow/project/dbt_shopflow/target/index.html`
3. Copy to host: `docker cp shopflow_project-airflow-1:/opt/airflow/project/dbt_shopflow/target ./dbt_docs`

### Enable dbt in DAG
```bash
# In Airflow UI:
# Admin > Variables > Create
# Key: ENABLE_DBT
# Value: 1

# Or via CLI:
docker-compose exec airflow airflow variables set ENABLE_DBT 1
```

---

## 🎯 Project Status

| Component | Status |
|-----------|--------|
| Docker Setup | ✓ Ready |
| Airflow | ✓ Running |
| PostgreSQL | ✓ Running |
| dbt | ✓ Installed & Connected |
| Models | ✓ Defined |
| Tests | ✓ Ready |
| DAG | ✓ Configured |

---

**Last Updated**: December 22, 2025
**Ready For**: Testing, Development, Production Deployment

For detailed information, see [DBT_DOCKER_AIRFLOW_GUIDE.md](./DBT_DOCKER_AIRFLOW_GUIDE.md)
