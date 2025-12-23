import os
import logging
from pathlib import Path
from typing import Optional, List

import pandas as pd
from sqlalchemy import create_engine, text


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


SCRIPT_ROOT = Path(__file__).resolve().parent
LOCAL_OUTPUT_ROOT = SCRIPT_ROOT / 'data_extraction' / 'local_output' / 'raw'


def find_latest_parquet(glob_patterns: List[str]) -> Optional[Path]:
    candidates = []
    for pattern in glob_patterns:
        for f in LOCAL_OUTPUT_ROOT.glob(pattern):
            try:
                mtime = f.stat().st_mtime
            except Exception:
                continue
            candidates.append((mtime, f))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def read_table_parquet(table: str) -> Optional[pd.DataFrame]:
    # Build table-specific search patterns relative to LOCAL_OUTPUT_ROOT
    patterns_map = {
        'customers': [
            'customers.parquet',
            'customers/*.parquet',
        ],
        'orders': [
            'orders.parquet',
            'orders/*.parquet',
        ],
        'products': [
            'products.parquet',
            'products/*.parquet',
        ],
        'events': [
            'events.parquet',
            'events/*.parquet',
        ],
        'inventory': [
            'inventory.parquet',
            'inventory/*.parquet',
        ],
        'support_tickets': [
            'support_tickets*.parquet',
            'support_tickets/*.parquet',
            'support_tickets/extract_date=*/support_tickets_*.parquet',
        ],
    }

    patterns = patterns_map.get(table, [f'{table}.parquet', f'{table}/*.parquet'])
    latest = find_latest_parquet(patterns)
    if not latest:
        logger.warning("No parquet files found for table %s under %s (patterns=%s)", table, LOCAL_OUTPUT_ROOT, patterns)
        return None
    logger.info("Reading parquet for %s: %s", table, latest)
    try:
        df = pd.read_parquet(latest)
        # normalize column names to lowercase
        df.columns = [str(c).lower() for c in df.columns]
        return df
    except Exception as e:
        logger.error("Failed to read parquet for %s: %s", table, e)
        return None


def get_engine_from_env() -> str:
    """Build a Postgres SQLAlchemy URL from env vars with sane defaults.

    Defaults align with docker-compose services: airflow/airflow@postgres:5432/airflow
    """
    host = os.environ.get('PGHOST', 'postgres')
    port = int(os.environ.get('PGPORT', '5432'))
    user = os.environ.get('PGUSER', 'airflow')
    password = os.environ.get('PGPASSWORD', 'airflow')
    dbname = os.environ.get('PGDATABASE', 'airflow')
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    return url


def load_to_postgres(table: str, df: pd.DataFrame, schema: str = 'raw') -> bool:
    """Load data idempotently using UPSERT (ON CONFLICT DO UPDATE).
    
    This ensures duplicate primary keys are updated rather than causing errors.
    """
    url = get_engine_from_env()
    logger.info("Connecting to Postgres with URL: %s", url.replace(os.environ.get('DBT_POSTGRES_PASSWORD','airflow'), '***'))
    engine = create_engine(url, future=True)
    
    # Define primary keys for each table
    primary_keys_map = {
        'customers': ['customer_id'],
        'orders': ['order_id'],
        'products': ['product_id'],
        'events': ['event_id'],
        'inventory': ['product_id'],
        'support_tickets': ['ticket_id'],
    }
    
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql(f"CREATE SCHEMA IF NOT EXISTS {schema}")
            
            # Get primary key(s) for this table
            pk_cols = primary_keys_map.get(table, [])
            
            if not pk_cols:
                logger.warning("No primary key defined for %s; using replace strategy", table)
                df.to_sql(table, con=conn, schema=schema, if_exists='append', index=False)
            else:
                # Check if table exists
                result = conn.execute(
                    text(f"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema='{schema}' AND table_name='{table}')")
                )
                table_exists = result.scalar()
                
                if not table_exists:
                    logger.info("Table %s.%s does not exist, creating it", schema, table)
                    df.to_sql(table, con=conn, schema=schema, if_exists='replace', index=False)
                else:
                    # Upsert: insert or update on conflict
                    logger.info("Upserting %d rows into %s.%s with primary key(s): %s", 
                                len(df), schema, table, pk_cols)
                    
                    # Build temp table name
                    temp_table = f"{table}_temp"
                    
                    # Create temp table with staging data
                    df.to_sql(temp_table, con=conn, schema=schema, if_exists='replace', index=False)
                    
                    # Get actual column list from temp table to ensure correct order
                    columns_list = ', '.join(df.columns)
                    
                    # Build conflict clause
                    conflict_cols = ', '.join(pk_cols)
                    set_clause = ', '.join([f"{col}=EXCLUDED.{col}" for col in df.columns if col not in pk_cols])
                    
                    if set_clause:
                        upsert_sql = f"""
                            INSERT INTO {schema}.{table} ({columns_list})
                            SELECT {columns_list} FROM {schema}.{temp_table}
                            ON CONFLICT ({conflict_cols})
                            DO UPDATE SET {set_clause}
                        """
                    else:
                        upsert_sql = f"""
                            INSERT INTO {schema}.{table} ({columns_list})
                            SELECT {columns_list} FROM {schema}.{temp_table}
                            ON CONFLICT ({conflict_cols})
                            DO NOTHING
                        """
                    
                    conn.execute(text(upsert_sql))
                    conn.execute(text(f"DROP TABLE IF EXISTS {schema}.{temp_table}"))
                    
        logger.info("Successfully upserted %d rows into %s.%s", len(df), schema, table)
        return True
    except Exception as e:
        logger.error("Failed loading %s into Postgres: %s", table, e)
        import traceback
        traceback.print_exc()
        return False


def main():
    tables = [
        'customers',
        'orders',
        'products',
        'events',
        'inventory',
        'support_tickets',
    ]
    any_loaded = False
    for t in tables:
        df = read_table_parquet(t)
        if df is None:
            continue
        ok = load_to_postgres(t, df, schema='raw')
        any_loaded = any_loaded or ok

    if not any_loaded:
        logger.warning("No tables were loaded — ensure local_output/raw has parquet files")


if __name__ == '__main__':
    main()

