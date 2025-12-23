from __future__ import annotations

import os
import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

# Make sure Airflow can import the project module path if necessary
import sys
# Ensure the project's `project` folder is on Python path inside the Airflow container.
# In the container the repo is mounted at `/opt/airflow/project`.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'project'))
container_project_path = '/opt/airflow/project'
if os.path.isdir(project_root) and project_root not in sys.path:
    sys.path.insert(0, project_root)
elif os.path.isdir(container_project_path) and container_project_path not in sys.path:
    sys.path.insert(0, container_project_path)

from airflow.providers.amazon.aws.hooks.s3 import S3Hook

LOG = logging.getLogger(__name__)

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


def _list_and_log(**context):
    bucket = os.environ.get('S3_BUCKET')
    if not bucket:
        raise ValueError('S3_BUCKET not set in environment for DAG')
    hook = S3Hook(aws_conn_id='aws_default')
    try:
        keys = hook.list_keys(bucket_name=bucket, prefix='staging/') or []
        LOG.info('Airflow DAG listed %d objects in bucket=%s', len(keys), bucket)
        return {'count': len(keys)}
    except Exception:
        LOG.exception('Error listing objects with S3Hook')
        raise
with DAG(
    dag_id='list_s3_staging',
    default_args=default_args,
    start_date=datetime(2025, 1, 1),
    schedule_interval='@daily',
    catchup=False,
    max_active_runs=1,
) as dag:

    list_task = PythonOperator(
        task_id='list_staging_objects',
        python_callable=_list_and_log,
        provide_context=True,
    )

    list_task
