"""
ShopFlow Data Extraction: RDS to S3
Extract data from PostgreSQL RDS and upload to S3 raw layer as Parquet files
"""

import pandas as pd
import psycopg2
import boto3
from datetime import datetime
import logging
from pathlib import Path
from dotenv import load_dotenv
import os
import io
from pathlib import Path
from data_extraction.extraction import data_quality
from data_extraction.extraction import _common as common

# Load environment variables from .env
common.load_env()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_env_config():
    """Get configuration from environment variables"""
    config = {
        'rds': {
            'host': os.getenv('RDS_HOST'),
            'port': int(os.getenv('RDS_PORT', 5432)),
            'database': os.getenv('RDS_DB'),
            'username': os.getenv('RDS_USER'),
            'password': os.getenv('RDS_PASSWORD'),
            'tables': os.getenv('RDS_TABLES', 'customers,orders,products,events,inventory').split(',')
        },
        's3': {
            'bucket_name': os.getenv('S3_BUCKET'),
            'region': os.getenv('AWS_REGION'),
            'raw_layer': os.getenv('S3_RAW_LAYER')
        }
    }
    return config


def validate_config(config):
    """Validate required environment variables"""
    # If SKIP_S3_UPLOAD is enabled we don't require S3-specific vars
    skip_s3 = os.environ.get('SKIP_S3_UPLOAD', 'false').lower() in ('1', 'true', 'yes')
    required = [
        ('RDS_HOST', config['rds']['host']),
        ('RDS_DB', config['rds']['database']),
        ('RDS_USER', config['rds']['username']),
        ('RDS_PASSWORD', config['rds']['password']),
    ]
    if not skip_s3:
        required.extend([
            ('S3_BUCKET', config['s3']['bucket_name']),
            ('AWS_REGION', config['s3']['region'])
        ])

    missing = [name for name, value in required if not value]
    if missing:
        logger.error(f"Missing environment variables: {', '.join(missing)}")
        raise ValueError(f"Missing required env vars: {missing}")
    
    logger.info("Configuration validated successfully")


def connect_to_rds(rds_config):
    """Connect to RDS PostgreSQL database"""
    logger.info("Connecting to RDS PostgreSQL...")
    conn = psycopg2.connect(
        host=rds_config['host'],
        port=rds_config['port'],
        database=rds_config['database'],
        user=rds_config['username'],
        password=rds_config['password']
    )
    logger.info("Connected successfully!")
    return conn


def extract_table(conn, table_name):
    """Extract table data from RDS"""
    logger.info(f"Extracting table: {table_name}")
    query = f"SELECT * FROM {table_name}"
    df = pd.read_sql(query, conn)
    logger.info(f"Extracted {len(df)} rows from {table_name}")
    return df


def upload_to_s3(df, table_name, s3_config):
    """Upload DataFrame to S3 as Parquet"""
    def _strip_quotes(v):
        return common.strip_quotes(v)

    def to_parquet_bytes(df: pd.DataFrame) -> bytes:
        return common.df_to_parquet_bytes(df, index=False)

    # Prepare S3 key with date partition
    extract_date = datetime.utcnow().strftime('%Y-%m-%d')
    s3_key = f"{s3_config.get('raw_layer','')}{table_name}/extract_date={extract_date}/{table_name}.parquet"

    data_bytes = to_parquet_bytes(df)

    # Build boto3 session preferring explicit creds in env/.env
    aws_key = _strip_quotes(os.environ.get('AWS_ACCESS_KEY_ID'))
    aws_secret = _strip_quotes(os.environ.get('AWS_SECRET_ACCESS_KEY'))
    aws_token = _strip_quotes(os.environ.get('AWS_SESSION_TOKEN'))
    aws_region = _strip_quotes(os.environ.get('AWS_REGION') or s3_config.get('region'))

    logger.info(f"Uploading {table_name} to s3://{s3_config['bucket_name']}/{s3_key} ({len(data_bytes)} bytes)")
    if aws_key and aws_secret:
        session = boto3.Session(aws_access_key_id=aws_key,
                                aws_secret_access_key=aws_secret,
                                aws_session_token=aws_token,
                                region_name=aws_region)
    else:
        session = boto3.Session()

    s3_client = session.client('s3', region_name=aws_region) if aws_region else session.client('s3')
    s3_client.put_object(Bucket=s3_config['bucket_name'], Key=s3_key, Body=data_bytes)
    logger.info(f"Upload complete for {table_name}")


def upload_dual_table(bucket, table_name, data_bytes, layer, local_dir_root, region=None, write_local=True, upload_s3=True):
    """Write local copy and upload to S3 for a specific layer and table."""
    safe_layer = layer.rstrip('/')
    key = f"{safe_layer}/{table_name}/extract_date={datetime.utcnow().strftime('%Y-%m-%d')}/{table_name}.parquet"

    # local path under local_dir_root/<layer>/
    if write_local and local_dir_root:
        try:
            local_dir = Path(local_dir_root) / safe_layer / table_name
            local_dir.mkdir(parents=True, exist_ok=True)
            local_path = local_dir / f"{table_name}.parquet"
            with open(local_path, 'wb') as f:
                f.write(data_bytes)
            logger.info('Wrote local copy to %s', local_path)
        except Exception as e:
            logger.warning('Failed to write local copy for %s: %s', table_name, e)

    if upload_s3:
        # delegate upload to common helper
        session = common.get_boto3_session()
        common.upload_bytes_to_s3(session, bucket, key, data_bytes)
        logger.info('Uploaded %s to s3://%s/%s', table_name, bucket, key)


def run_quality_checks_table(df: pd.DataFrame, null_threshold: float = 0.5) -> bool:
    if df is None:
        logger.error('DataFrame is None')
        return False
    if df.empty:
        logger.warning('Extracted table is empty')
        return True

    if 'id' in df.columns:
        dup_count = df['id'].duplicated().sum()
        if dup_count > 0:
            logger.warning('Found %d duplicate id values in table', int(dup_count))

    null_frac = df.isna().mean()
    high_null = null_frac[null_frac > null_threshold]
    if not high_null.empty:
        for col, frac in high_null.items():
            logger.warning('High null fraction in column %s: %.2f', col, float(frac))
    return True


def main():
    """Main extraction process"""
    logger.info("=" * 60)
    logger.info("Starting RDS to S3 Extraction Process")
    logger.info("=" * 60)
    
    try:
        # Get and validate configuration
        config = get_env_config()
        validate_config(config)
        
        rds_config = config['rds']
        s3_config = config['s3']
        
        # Connect to RDS
        conn = connect_to_rds(rds_config)
        
        try:
            # Extract each table
            # determine export layers
            export_layers = [l.strip() for l in os.environ.get('EXPORT_LAYERS', 'raw').split(',') if l.strip()]
            null_threshold = float(os.environ.get('DQ_NULL_THRESHOLD', '0.5'))
            fail_on_dq = os.environ.get('FAIL_ON_DQ', 'false').lower() in ('1', 'true', 'yes')
            # Determine local output root
            # 1) Use env var LOCAL_OUTPUT_ROOT if provided
            # 2) Else default to top-level data_extraction/local_output
            local_output_root = os.environ.get('LOCAL_OUTPUT_ROOT') or str(Path(__file__).resolve().parents[2] / 'local_output')

            for table_name in rds_config['tables']:
                table_name = table_name.strip()
                try:
                    # Extract data
                    df = extract_table(conn, table_name)

                    # data quality checks
                    dq_ok = run_quality_checks_table(df, null_threshold=null_threshold)
                    if not dq_ok and fail_on_dq:
                        logger.error('Data quality failed for %s and FAIL_ON_DQ set; skipping', table_name)
                        continue

                    # convert to parquet bytes once
                    data_bytes = common.df_to_parquet_bytes(df, index=False)

                    # upload to specified layers
                    for layer in export_layers:
                        try:
                            # build s3 key and upload via shared helper
                            safe_layer = layer.rstrip('/')
                            key = f"{safe_layer}/{table_name}/extract_date={datetime.utcnow().strftime('%Y-%m-%d')}/{table_name}.parquet"
                            local_dir = os.path.join(local_output_root, safe_layer)
                            common.upload_dual(s3_config['bucket_name'], key, data_bytes, local_dir=local_dir, write_local=True, upload_s3=True)
                            # optional: run advanced DQ after writing local copies
                            # advanced DQ delegated to common helper
                            local_root = Path(local_output_root)
                            report_path = local_root / 'test_files' / f'parquet_quality_report_{table_name}_{layer}.json'
                            try:
                                rpt = common.run_dq_if_enabled(local_root, out_report=report_path)
                                if rpt is not None:
                                    logger.info('DQ run complete for table %s layer %s: failures=%s', table_name, layer, rpt['summary'].get('failures'))
                            except Exception as e:
                                logger.warning('DQ run failed for %s layer %s: %s', table_name, layer, e)
                        except Exception as e:
                            logger.error('Failed upload for table %s layer %s: %s', table_name, layer, e)
                            continue

                    logger.info(f"✓ Successfully processed {table_name}")

                except Exception as e:
                    logger.error(f"✗ Failed to process {table_name}: {str(e)}")
                    continue
            
            logger.info("=" * 60)
            logger.info("✓ Extraction process completed!")
            logger.info("=" * 60)
            
        finally:
            conn.close()
            logger.info("Database connection closed")
    
    except Exception as e:
        logger.error(f"✗ Critical error: {str(e)}")
        raise


if __name__ == "__main__":
    main()

