#!/usr/bin/env python3
"""
Automated extraction and idempotent ingestion pipeline.

1. Extract RDS tables to Parquet (local only, skip S3)
2. Extract API data to Parquet (local only, skip S3)
3. Ingest all Parquet files into Postgres with upsert logic (idempotent)

Usage:
    python run_automated_extract_ingest.py

Environment variables:
    RDS_HOST, RDS_PORT, RDS_USER, RDS_PASSWORD, RDS_DATABASE
    API_BASE_URL, API_KEY (for API extraction)
    PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE (for ingestion)
    SKIP_RDS: set to 1 to skip RDS extraction
    SKIP_API: set to 1 to skip API extraction
    SKIP_INGEST: set to 1 to skip ingestion
"""

import os
import sys
import logging
import subprocess
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
EXTRACTION_DIR = SCRIPT_DIR / 'data_extraction'


def run_command(cmd_path: Path, description: str) -> bool:
    """Run a Python script and return success status."""
    logger.info("=" * 80)
    logger.info("Running: %s", description)
    logger.info("=" * 80)
    
    try:
        # Set SKIP_S3_UPLOAD to prevent S3 errors with invalid credentials
        env = os.environ.copy()
        env['SKIP_S3_UPLOAD'] = '1'
        env['PYTHONPATH'] = str(SCRIPT_DIR) + ':' + env.get('PYTHONPATH', '')
        
        result = subprocess.run(
            [sys.executable, str(cmd_path)],
            env=env,
            check=False
        )
        
        if result.returncode == 0:
            logger.info("✓ %s completed successfully", description)
            return True
        else:
            logger.error("✗ %s failed with exit code %d", description, result.returncode)
            return False
    except Exception as e:
        logger.error("✗ %s failed with exception: %s", description, e)
        import traceback
        traceback.print_exc()
        return False


def main():
    logger.info("Starting automated extract + ingest pipeline")
    
    results = {}
    
    # Step 1: Extract RDS data
    if os.environ.get('SKIP_RDS', '').lower() != '1':
        extract_rds_script = EXTRACTION_DIR / 'extract_rds_to_s3.py'
        results['RDS Extraction'] = run_command(extract_rds_script, 'RDS Extraction')
    else:
        logger.info("Skipping RDS extraction (SKIP_RDS=1)")
        results['RDS Extraction'] = True
    
    # Step 2: Extract API data
    if os.environ.get('SKIP_API', '').lower() != '1':
        extract_api_script = EXTRACTION_DIR / 'extract_api_to_s3.py'
        results['API Extraction'] = run_command(extract_api_script, 'API Extraction')
    else:
        logger.info("Skipping API extraction (SKIP_API=1)")
        results['API Extraction'] = True
    
    # Step 3: Ingest all data idempotently
    if os.environ.get('SKIP_INGEST', '').lower() != '1':
        ingest_script = SCRIPT_DIR / 'ingest_api_parquet_to_postgres.py'
        results['Idempotent Ingestion'] = run_command(ingest_script, 'Idempotent Ingestion (RDS + API)')
    else:
        logger.info("Skipping ingestion (SKIP_INGEST=1)")
        results['Idempotent Ingestion'] = True
    
    # Summary
    logger.info("=" * 80)
    logger.info("PIPELINE SUMMARY")
    logger.info("=" * 80)
    for step, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        logger.info("%s: %s", step, status)
    
    all_success = all(results.values())
    if all_success:
        logger.info("=" * 80)
        logger.info("✓ All pipeline steps completed successfully!")
        logger.info("=" * 80)
        return 0
    else:
        logger.error("=" * 80)
        logger.error("✗ Some pipeline steps failed. Check logs above.")
        logger.error("=" * 80)
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

