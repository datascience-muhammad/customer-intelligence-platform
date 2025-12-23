"""Airflow DAG: RDS -> S3 extraction, ingest, and dbt run

This DAG extracts data from RDS (Postgres) to S3 (Parquet), ingests the
Parquet files into Postgres (upsert), and runs dbt transformations in a
containerized dbt image.
"""

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.models import Variable
from datetime import datetime, timedelta
import os

default_args = {
    'owner': 'shopflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='shopflow_etl_rds',
    default_args=default_args,
    schedule_interval=None,
    start_date=datetime(2025,1,1),
    catchup=False,
) as dag:

    # Extract data from RDS (Postgres) and write parquet files (local only, skip S3)
    extract_rds = BashOperator(
        task_id='extract_rds_to_s3',
        bash_command=(
            'export PYTHONPATH=/opt/airflow/project:$PYTHONPATH; '
            'python /opt/airflow/project/data_extraction/extraction/data_extraction/extract_rds_to_s3.py'
        ),
    )

    # Extract data from API and write parquet files to local_output + S3
    extract_api = BashOperator(
        task_id='extract_api_to_s3',
        bash_command=(
            'export PYTHONPATH=/opt/airflow/project:$PYTHONPATH; '
            'python /opt/airflow/project/data_extraction/extraction/data_extraction/extract_api_to_s3.py'
        ),
    )

    # Ingest all Parquet files into Postgres (idempotent upsert, RDS + API)
    ingest = BashOperator(
        task_id='ingest_parquet_to_postgres',
        bash_command=(
            'export PYTHONPATH=/opt/airflow/project:$PYTHONPATH; '
            'export DBT_POSTGRES_HOST=postgres; '
            'export DBT_POSTGRES_PORT=5432; '
            'export DBT_POSTGRES_USER=airflow; '
            'export DBT_POSTGRES_PASSWORD=airflow; '
            'export DBT_POSTGRES_DBNAME=airflow; '
            'python /opt/airflow/project/data_extraction/extraction/ingest_api_parquet_to_postgres.py'
        ),
        env={
            'PGHOST': 'postgres',
            'PGPORT': '5432',
            'PGUSER': 'airflow',
            'PGPASSWORD': 'airflow',
            'PGDATABASE': 'airflow',
        },
    )

    # Run dbt using the dbt CLI installed in this image (avoids Docker socket).
    run_dbt = BashOperator(
        task_id='dbt_run',
        bash_command=(
            'export PYTHONPATH=/home/airflow/.local/lib/python3.11/site-packages:/opt/airflow/project:$PYTHONPATH; '
            'export PGHOST=postgres; '
            'export PGPORT=5432; '
            'export PGUSER=postgres; '
            'export PGPASSWORD=postgres; '
            'export PGDATABASE=shopflow; '
            '/home/airflow/.local/bin/dbt run --project-dir /opt/airflow/project/dbt_shopflow --profiles-dir /opt/airflow/project/dbt_shopflow && '
            '/home/airflow/.local/bin/dbt test --project-dir /opt/airflow/project/dbt_shopflow --profiles-dir /opt/airflow/project/dbt_shopflow'
        ),
        env={
            # dbt Postgres connection parameters (match docker-compose postgres service)
            'DBT_POSTGRES_HOST': 'postgres',
            'DBT_POSTGRES_PORT': '5432',
            'DBT_POSTGRES_USER': 'airflow',
            'DBT_POSTGRES_PASSWORD': 'airflow',
            'DBT_POSTGRES_DBNAME': 'airflow',
            'DBT_POSTGRES_SCHEMA': 'raw',
        },
    )

    # Export all schemas (raw, staging, curated) to local Parquet files
    export_local = BashOperator(
        task_id='export_local',
        bash_command=(
            'export PYTHONPATH=/opt/airflow/project:$PYTHONPATH; '
            'python /opt/airflow/project/data_extraction/transform/export_all_to_local.py'
        ),
        env={
            'POSTGRES_HOST': 'postgres',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'airflow',
            'POSTGRES_USER': 'airflow',
            'POSTGRES_PASSWORD': 'airflow',
        },
    )

    # Optionally export curated models to S3
    export_s3 = BashOperator(
        task_id='export_s3_curated',
        bash_command=(
            'export PYTHONPATH=/opt/airflow/project:$PYTHONPATH; '
            'python /opt/airflow/project/data_extraction/transform/export_curated_to_s3.py'
        ),
        env={
            'SKIP_S3_UPLOAD': '{{ var.value.get("SKIP_S3_UPLOAD", "1") }}',
            'S3_BUCKET': '{{ var.value.get("S3_BUCKET", "") }}',
            'POSTGRES_HOST': 'postgres',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'airflow',
            'POSTGRES_USER': 'airflow',
            'POSTGRES_PASSWORD': 'airflow',
            'DBT_POSTGRES_SCHEMA': 'raw',
        },
    )

    # Decide whether to include dbt step using Airflow Variable (overrides env var)
    enable_dbt = Variable.get('ENABLE_DBT', default_var=os.environ.get('ENABLE_DBT', '0'))
    if str(enable_dbt) == '1':
        [extract_rds, extract_api] >> ingest >> run_dbt >> export_local >> export_s3
    else:
        [extract_rds, extract_api] >> ingest

