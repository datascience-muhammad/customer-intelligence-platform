#!/usr/bin/env python3
"""Export curated dbt models from Postgres to Parquet and upload to S3.

Behavior:
- Reads curated model names from `dbt_shopflow/models/curated/` directory.
- Queries each model from the target schema (from env `DBT_SCHEMA` or `dbt_shopflow/profiles.yml`).
- Writes each model to an in-memory Parquet and uploads to S3 under
  `s3://{S3_BUCKET}/curated/{model}/extract_date=YYYY-MM-DD/{model}_{ts}.parquet`.

Uses the project's `.env` (searched upward) for DB and AWS credentials.
"""
import os
import io
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone
import boto3
import pandas as pd
import psycopg2
import yaml
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_env():
    p = Path(__file__).resolve()
    for i in range(1, 6):
        env_path = p.parents[i] / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f'Loaded environment from {env_path}')
            return
    logger.info('.env not found; using environment variables')


def _strip_quotes(v):
    if v is None:
        return v
    v = str(v).strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    return v


def connect_pg():
    # Connection fallback order: POSTGRES_* -> DBT_POSTGRES_* -> RDS_* -> localhost:5433 airflow/airflow
    host = _strip_quotes(os.environ.get('POSTGRES_HOST')) or _strip_quotes(os.environ.get('DBT_POSTGRES_HOST')) or _strip_quotes(os.environ.get('RDS_HOST')) or 'localhost'
    port = int(_strip_quotes(os.environ.get('POSTGRES_PORT') or os.environ.get('DBT_POSTGRES_PORT') or os.environ.get('RDS_PORT') or '5433'))
    dbname = _strip_quotes(os.environ.get('POSTGRES_DB') or os.environ.get('DBT_POSTGRES_DBNAME') or os.environ.get('RDS_DB') or 'airflow')
    user = _strip_quotes(os.environ.get('POSTGRES_USER') or os.environ.get('DBT_POSTGRES_USER') or os.environ.get('RDS_USER') or 'airflow')
    password = _strip_quotes(os.environ.get('POSTGRES_PASSWORD') or os.environ.get('DBT_POSTGRES_PASSWORD') or os.environ.get('RDS_PASSWORD') or 'airflow')

    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
    )
    conn.autocommit = True
    return conn


def get_target_schema():
    # Prefer explicit env var
    s = os.environ.get('DBT_SCHEMA') or os.environ.get('DBT_TARGET_SCHEMA')
    if s:
        return _strip_quotes(s)
    # Fall back to reading dbt profiles.yml
    p = Path(__file__).resolve().parents[2] / 'dbt_shopflow' / 'profiles.yml'
    if p.exists():
        try:
            with open(p, 'r', encoding='utf-8') as fh:
                cfg = yaml.safe_load(fh)
                # try to find first profile -> outputs -> dev -> schema
                for profile in cfg.values():
                    outputs = profile.get('outputs') or {}
                    for out in outputs.values():
                        schema = out.get('schema')
                        if schema:
                            return _strip_quotes(schema)
        except Exception:
            logger.exception('Error reading dbt profiles.yml')
    logger.warning('Target schema not found; defaulting to "public"')
    return 'public'


def s3_session_from_env():
    # prefer explicit creds in env/.env
    aws_access_key_id = _strip_quotes(os.environ.get('AWS_ACCESS_KEY_ID'))
    aws_secret_access_key = _strip_quotes(os.environ.get('AWS_SECRET_ACCESS_KEY'))
    aws_session_token = _strip_quotes(os.environ.get('AWS_SESSION_TOKEN'))

    if aws_access_key_id and aws_secret_access_key:
        logger.info('Using AWS credentials from environment/.env for S3 session')
        return boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
        )
    logger.info('Using default boto3 session (environment or instance profile)')
    return boto3.Session()


def list_curated_model_names():
    base = Path(__file__).resolve().parents[2] / 'dbt_shopflow' / 'models' / 'curated'
    if not base.exists():
        logger.error('Curated models directory not found: %s', base)
        return []
    names = [p.stem for p in base.glob('*.sql')]
    logger.info('Found curated models: %s', names)
    return names


def export_and_upload(model_names, schema, s3_bucket, s3_prefix='curated/'):
    conn = connect_pg()
    sess = s3_session_from_env()
    s3 = sess.client('s3')

    date_str = datetime.now(timezone.utc).date().isoformat()
    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')

    # Prepare local output base: data_engineering/local_output/curated
    local_base = Path(__file__).resolve().parents[2] / 'local_output' / 'curated'
    local_base.mkdir(parents=True, exist_ok=True)

    for m in model_names:
        q = f'SELECT * FROM "{schema}"."{m}"'
        logger.info('Querying table: %s', q)
        try:
            df = pd.read_sql_query(q, conn)
        except Exception as e:
            logger.exception('Failed to query model %s: %s', m, e)
            continue

        if df.empty:
            logger.warning('Model %s returned no rows; skipping upload', m)
            continue

        # Write local Parquet copy
        local_dir = local_base / m / f'extract_date={date_str}'
        local_dir.mkdir(parents=True, exist_ok=True)
        local_path = local_dir / f'{m}_{ts}.parquet'
        try:
            df.to_parquet(local_path, index=False)
            logger.info('Wrote local Parquet: %s (rows=%d)', local_path, len(df))
        except Exception:
            logger.exception('Failed writing local Parquet for %s', m)

        # Upload to S3
        buf = io.BytesIO()
        df.to_parquet(buf, index=False)
        buf.seek(0)
        key = f"{s3_prefix}{m}/extract_date={date_str}/{m}_{ts}.parquet"
        logger.info('Uploading %d bytes to s3://%s/%s', buf.getbuffer().nbytes, s3_bucket, key)
        try:
            s3.put_object(Bucket=s3_bucket, Key=key, Body=buf.getvalue())
            # confirm
            s3.head_object(Bucket=s3_bucket, Key=key)
            logger.info('Upload confirmed for s3://%s/%s', s3_bucket, key)
        except Exception:
            logger.exception('Upload failed for %s', key)


def main():
    load_env()
    skip_upload = (os.environ.get('SKIP_S3_UPLOAD') or '').strip() == '1'
    s3_bucket = os.environ.get('S3_BUCKET')

    if not s3_bucket and not skip_upload:
        logger.error('S3_BUCKET not set and SKIP_S3_UPLOAD!=1; refusing to upload')
        sys.exit(1)

    model_names = list_curated_model_names()
    if not model_names:
        logger.error('No curated models found; aborting')
        sys.exit(1)

    schema = get_target_schema()
    logger.info('Using target schema: %s', schema)

    if skip_upload:
        logger.info('SKIP_S3_UPLOAD=1: Will write local Parquet only, skipping S3 upload')
        # call export with a dummy bucket and prefix; upload code will still run but we can short-circuit by overriding client
        # Better: copy function with upload gated, but we reuse and rely on a no-op client
        # Instead, call a modified path which writes local only
        conn = connect_pg()
        date_str = datetime.now(timezone.utc).date().isoformat()
        ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        local_base = Path(__file__).resolve().parents[2] / 'data_engineering' / 'local_output' / 'curated'
        local_base.mkdir(parents=True, exist_ok=True)
        for m in model_names:
            q = f'SELECT * FROM "{schema}"."{m}"'
            logger.info('Querying table: %s', q)
            try:
                df = pd.read_sql_query(q, conn)
            except Exception as e:
                logger.exception('Failed to query model %s: %s', m, e)
                continue
            if df.empty:
                logger.warning('Model %s returned no rows; skipping local write', m)
                continue
            local_dir = local_base / m / f'extract_date={date_str}'
            local_dir.mkdir(parents=True, exist_ok=True)
            local_path = local_dir / f'{m}_{ts}.parquet'
            try:
                df.to_parquet(local_path, index=False)
                logger.info('Wrote local Parquet: %s (rows=%d)', local_path, len(df))
            except Exception:
                logger.exception('Failed writing local Parquet for %s', m)
        return

    export_and_upload(model_names, schema, s3_bucket)


if __name__ == '__main__':
    main()

