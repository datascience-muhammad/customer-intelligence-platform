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
    dag_id='shopflow_etl_api',
    default_args=default_args,
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
) as dag:

    # 1) Run extraction script (extract -> s3)
    extract = BashOperator(
        task_id='extract_api_to_s3',
        bash_command='export PYTHONPATH=/opt/airflow/project:$PYTHONPATH; python /opt/airflow/project/data_extraction/extraction/data_extraction/extract_api_to_s3.py '
    )

    # 2) Optionally run ingestion (if you want DB ingest)
    ingest = BashOperator(
        task_id='ingest_parquet_to_postgres',
        bash_command='export PYTHONPATH=/opt/airflow/project:$PYTHONPATH; python /opt/airflow/project/data_extraction/extraction/ingest_api_parquet_to_postgres.py || true'
    )

    # 3) Run dbt transformations using the dbt CLI installed in this image
    run_dbt = BashOperator(
        task_id='run_dbt',
        bash_command=(
            'export PYTHONPATH=/home/airflow/.local/lib/python3.11/site-packages:/opt/airflow/project:$PYTHONPATH; '
            '/home/airflow/.local/bin/dbt test --project-dir /opt/airflow/project/dbt_shopflow --profiles-dir /opt/airflow/project/dbt_shopflow && '
            '/home/airflow/.local/bin/dbt run --project-dir /opt/airflow/project/dbt_shopflow --profiles-dir /opt/airflow/project/dbt_shopflow && '
            'if [ "${SKIP_S3_UPLOAD:-1}" != "1" ]; then python /opt/airflow/project/data_extraction/transform/export_curated_to_s3.py; fi'
        ),
        env={
            'DBT_POSTGRES_HOST': 'postgres',
            'DBT_POSTGRES_PORT': '5432',
            'DBT_POSTGRES_USER': 'airflow',
            'DBT_POSTGRES_PASSWORD': 'airflow',
            'DBT_POSTGRES_DBNAME': 'airflow',
            'DBT_POSTGRES_SCHEMA': 'raw',
            'SKIP_S3_UPLOAD': '{{ var.value.get("SKIP_S3_UPLOAD", "1") }}',
            'S3_BUCKET': '{{ var.value.get("S3_BUCKET", "") }}',
        },
    )

# Decide whether to include dbt step using Airflow Variable (overrides env var)
enable_dbt = Variable.get('ENABLE_DBT', default_var=os.environ.get('ENABLE_DBT', '0'))
if str(enable_dbt) == '1':
    extract >> ingest >> run_dbt
else:
    extract >> ingest

