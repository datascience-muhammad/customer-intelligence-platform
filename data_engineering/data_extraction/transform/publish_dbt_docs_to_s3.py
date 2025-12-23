#!/usr/bin/env python3
"""Publish dbt `target/` artifacts to S3 under a timestamped prefix.

Uploads all files under `dbt_shopflow/target/` to
`s3://{S3_BUCKET}/dbt_docs/extract_date=YYYY-MM-DD/<filename>` and confirms with head_object.
"""
import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
import boto3

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


def s3_session_from_env():
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


def publish_target(s3_bucket, s3_prefix='dbt_docs/'):
    base = Path(__file__).resolve().parents[2] / 'dbt_shopflow' / 'target'
    if not base.exists():
        logger.error('dbt target directory not found: %s', base)
        return

    sess = s3_session_from_env()
    s3 = sess.client('s3')

    date_str = datetime.now(timezone.utc).date().isoformat()

    files_uploaded = 0
    for root, _, files in os.walk(base):
        for fn in files:
            full = Path(root) / fn
            rel = full.relative_to(base)
            key = f"{s3_prefix}extract_date={date_str}/{rel.as_posix()}"
            logger.info('Uploading %s -> s3://%s/%s', full, s3_bucket, key)
            with open(full, 'rb') as fh:
                s3.put_object(Bucket=s3_bucket, Key=key, Body=fh)
            # confirm
            s3.head_object(Bucket=s3_bucket, Key=key)
            files_uploaded += 1

    logger.info('Uploaded %d files from %s to s3://%s/%s', files_uploaded, base, s3_bucket, s3_prefix)


def main():
    load_env()
    s3_bucket = os.environ.get('S3_BUCKET')
    if not s3_bucket:
        logger.error('S3_BUCKET not set in environment/.env')
        sys.exit(1)

    publish_target(s3_bucket)


if __name__ == '__main__':
    main()

