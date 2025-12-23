#!/usr/bin/env python3
"""Export raw, staging, and curated relations from Postgres to local Parquet.

Output layout:
- data_extraction/local_output/raw/<table>/extract_date=YYYY-MM-DD/<table>_<ts>.parquet
- data_extraction/local_output/staging/<view>/extract_date=YYYY-MM-DD/<view>_<ts>.parquet
- data_extraction/local_output/curated/<table>/extract_date=YYYY-MM-DD/<table>_<ts>.parquet

Connection resolution order:
1) Explicit POSTGRES_* env (POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD)
2) DBT_POSTGRES_* env
3) RDS_* env
4) Fallback host=localhost, port=5433, db=airflow, user=airflow, password=airflow

This script is safe to run repeatedly; it appends timestamped files per run.
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
import logging

import pandas as pd
import psycopg2
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_env():
    # search up to 5 parent dirs for a .env
    p = Path(__file__).resolve()
    for i in range(1, 6):
        env_path = p.parents[i] / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            logger.info('Loaded environment from %s', env_path)
            return
    logger.info('.env not found; using environment variables')


def _get(env, default=None):
    v = os.environ.get(env)
    return v if v is not None else default


def connect_pg():
    # Priority: POSTGRES_* -> DBT_POSTGRES_* -> RDS_* -> fallback
    host = _get('POSTGRES_HOST') or _get('DBT_POSTGRES_HOST') or _get('RDS_HOST') or 'localhost'
    port = int(_get('POSTGRES_PORT') or _get('DBT_POSTGRES_PORT') or _get('RDS_PORT') or '5433')
    db = _get('POSTGRES_DB') or _get('DBT_POSTGRES_DBNAME') or _get('RDS_DB') or 'airflow'
    user = _get('POSTGRES_USER') or _get('DBT_POSTGRES_USER') or _get('RDS_USER') or 'airflow'
    pwd = _get('POSTGRES_PASSWORD') or _get('DBT_POSTGRES_PASSWORD') or _get('RDS_PASSWORD') or 'airflow'
    logger.info('Connecting to Postgres %s:%s db=%s user=%s', host, port, db, user)
    conn = psycopg2.connect(host=host, port=port, dbname=db, user=user, password=pwd)
    conn.autocommit = True
    return conn


def list_relations(conn, schema, include_views=True, include_tables=True):
    rels = []
    if include_tables:
        with conn.cursor() as cur:
            cur.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname=%s ORDER BY 1", (schema,))
            rels += [r[0] for r in cur.fetchall()]
    if include_views:
        with conn.cursor() as cur:
            cur.execute("SELECT viewname FROM pg_catalog.pg_views WHERE schemaname=%s ORDER BY 1", (schema,))
            rels += [r[0] for r in cur.fetchall()]
    return rels


def write_parquet(df, base_dir: Path, relation: str, date_str: str, ts: str):
    out_dir = base_dir / relation / f'extract_date={date_str}'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'{relation}_{ts}.parquet'
    df.to_parquet(out_path, index=False)
    logger.info('Wrote %s (rows=%d)', out_path, len(df))


def export_schema(conn, schema: str, folder_name: str):
    base = Path(__file__).resolve().parents[2] / 'data_extraction' / 'local_output' / folder_name
    base.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).date().isoformat()
    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')

    # include views and tables for all schemas
    rels = list_relations(conn, schema, include_views=True, include_tables=True)
    if not rels:
        logger.warning('No relations found in schema=%s', schema)
        return
    logger.info('Exporting %d relations from schema=%s', len(rels), schema)
    for r in rels:
        q = f'SELECT * FROM "{schema}"."{r}"'
        try:
            df = pd.read_sql_query(q, conn)
        except Exception as e:
            logger.exception('Query failed for %s.%s: %s', schema, r, e)
            continue
        # write parquet
        try:
            write_parquet(df, base, r, date_str, ts)
        except Exception as e:
            logger.exception('Failed to write parquet for %s.%s: %s', schema, r, e)


def main():
    load_env()
    conn = connect_pg()
    # raw, staging, curated schemas used by dbt_project.yml
    raw_schema = _get('DBT_POSTGRES_SCHEMA', 'raw')
    staging_schema = 'raw_staging'
    curated_schema = 'raw_curated'

    export_schema(conn, raw_schema, 'raw')
    export_schema(conn, staging_schema, 'staging')
    export_schema(conn, curated_schema, 'curated')


if __name__ == '__main__':
    main()

