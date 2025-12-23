# Run Airflow + dbt locally (Docker)

This project includes a Docker + docker-compose scaffold to run Airflow (LocalExecutor) with `dbt-postgres` installed in the Airflow image. The container mounts your repository so DAGs can call the extractor and dbt runner directly.

Quick start (PowerShell):

```powershell
# Build the image and start services
docker compose build
docker compose up -d

# View logs for the airflow service
docker compose logs -f airflow

# Open Airflow UI at http://localhost:8080 (admin/admin)
```

Notes:
- The compose file mounts the repository under `/opt/airflow/project`. DAG `shopflow_etl_api_dbt` runs the extraction script and then `dbt_runner.py`.
- Ensure your `.env` contains DB, S3, and AWS credentials and is present at the repository root. The compose file uses `env_file: .env` so sensitive values remain out of source control.
- If you prefer Astronomer/Astro-managed images, replace the `FROM` line in `docker/Dockerfile` with the Astronomer base image and adjust tags accordingly.

