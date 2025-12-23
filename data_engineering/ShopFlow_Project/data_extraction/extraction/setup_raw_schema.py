#!/usr/bin/env python3
"""
Initialize Postgres raw schema with idempotent table creation.
Sets up primary keys and unique constraints to support upsert logic.

Usage:
    python setup_raw_schema.py

Environment variables:
    PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE
"""

import os
import logging
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_engine_from_env() -> str:
    """Build a Postgres SQLAlchemy URL from env vars."""
    host = os.environ.get('PGHOST', 'postgres')
    port = int(os.environ.get('PGPORT', '5432'))
    user = os.environ.get('PGUSER', 'airflow')
    password = os.environ.get('PGPASSWORD', 'airflow')
    dbname = os.environ.get('PGDATABASE', 'airflow')
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    return url


def setup_schema():
    """Create raw schema with tables and constraints for idempotent upsert."""
    url = get_engine_from_env()
    logger.info("Connecting to Postgres for schema setup")
    engine = create_engine(url, future=True)
    
    # SQL statements to set up schema and tables with primary keys
    setup_statements = [
        "CREATE SCHEMA IF NOT EXISTS raw",
        """CREATE TABLE IF NOT EXISTS raw.customers (
            customer_id BIGINT PRIMARY KEY,
            name VARCHAR(255),
            email VARCHAR(255),
            created_at TIMESTAMP,
            city VARCHAR(100),
            country VARCHAR(100)
        )""",
        """CREATE TABLE IF NOT EXISTS raw.orders (
            order_id BIGINT PRIMARY KEY,
            customer_id BIGINT,
            order_date DATE,
            order_amount NUMERIC,
            status VARCHAR(50)
        )""",
        """CREATE TABLE IF NOT EXISTS raw.products (
            product_id BIGINT PRIMARY KEY,
            name VARCHAR(255),
            category VARCHAR(100),
            price NUMERIC
        )""",
        """CREATE TABLE IF NOT EXISTS raw.events (
            event_id BIGINT PRIMARY KEY,
            customer_id BIGINT,
            event_type VARCHAR(50),
            event_time TIMESTAMP,
            product_id BIGINT
        )""",
        """CREATE TABLE IF NOT EXISTS raw.inventory (
            product_id BIGINT PRIMARY KEY,
            quantity BIGINT,
            warehouse VARCHAR(100),
            last_updated TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS raw.support_tickets (
            ticket_id BIGINT PRIMARY KEY,
            customer_id BIGINT,
            subject VARCHAR(255),
            created_at TIMESTAMP,
            priority VARCHAR(50),
            status VARCHAR(50)
        )""",
    ]
    
    try:
        with engine.begin() as conn:
            for statement in setup_statements:
                logger.info("Executing: %s...", statement[:80])
                conn.execute(text(statement))
        logger.info("✓ Raw schema setup completed successfully")
        return True
    except Exception as e:
        logger.error("✗ Schema setup failed: %s", e)
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    setup_schema()

