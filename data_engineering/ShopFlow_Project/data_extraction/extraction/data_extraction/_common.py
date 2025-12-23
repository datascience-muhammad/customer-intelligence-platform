import os
import io
import logging
from pathlib import Path
from dotenv import load_dotenv
from dotenv import find_dotenv

import boto3
import pandas as pd

logger = logging.getLogger(__name__)


_ENV_LOADED = False


def load_env_once(preferred_root: Path | None = None):
    """Idempotent load of .env from repository root (or provided root).

    - Loads only once per process.
    - Uses `os.environ.setdefault` semantics so existing env vars are preserved.
    """
    global _ENV_LOADED
    if _ENV_LOADED:
        logger.debug('Environment already loaded; skipping')
        return

    # determine candidate .env path: prefer provided root, else repo root 3 levels up
    if preferred_root:
        env_path = Path(preferred_root) / '.env'
    else:
        # _common.py is at data_engineering/extraction/data_extraction/_common.py
        # repo root should be 3 parents up
        repo_root = Path(__file__).resolve().parents[3]
        env_path = repo_root / '.env'

    # fallback to find_dotenv if not present at repo_root
    if not env_path.exists():
        found = find_dotenv(usecwd=True)
        if found:
            env_path = Path(found)

    if env_path.exists():
        # use load_dotenv but avoid overwriting existing env vars
        load_dotenv(dotenv_path=env_path, override=False)
        os.environ.setdefault('_ENV_LOADED', '1')
        _ENV_LOADED = True
        logger.info('Loaded .env from %s', env_path)
    else:
        logger.debug('No .env file found at %s', env_path)


def load_env(preferred_root: Path | None = None):
    """Backward-compatible alias for load_env_once."""
    return load_env_once(preferred_root=preferred_root)


def strip_quotes(v):
    if v is None:
        return None
    v = str(v).strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    return v


def get_boto3_session():
    aws_key = strip_quotes(os.environ.get('AWS_ACCESS_KEY_ID'))
    aws_secret = strip_quotes(os.environ.get('AWS_SECRET_ACCESS_KEY'))
    aws_token = strip_quotes(os.environ.get('AWS_SESSION_TOKEN'))
    aws_region = strip_quotes(os.environ.get('AWS_REGION'))

    if aws_key and aws_secret:
        logger.debug('Creating boto3 Session from env credentials')
        return boto3.Session(aws_access_key_id=aws_key,
                             aws_secret_access_key=aws_secret,
                             aws_session_token=aws_token,
                             region_name=aws_region)
    return boto3.Session()


def df_to_parquet_bytes(df: pd.DataFrame, index: bool = False) -> bytes:
    buf = io.BytesIO()
    # Let pandas choose available engine (pyarrow/fastparquet)
    df.to_parquet(buf, index=index)
    buf.seek(0)
    return buf.read()


def write_local_bytes(local_dir: str, filename: str, data_bytes: bytes) -> Path:
    p = Path(local_dir)
    p.mkdir(parents=True, exist_ok=True)
    path = p / filename
    with open(path, 'wb') as f:
        f.write(data_bytes)
    logger.info('Wrote local copy to %s', path)
    return path


def upload_bytes_to_s3(session: boto3.Session, bucket: str, key: str, data_bytes: bytes, content_type: str = 'application/octet-stream'):
    aws_region = strip_quotes(os.environ.get('AWS_REGION'))
    skip = os.environ.get('SKIP_S3_UPLOAD', 'false').lower() in ('1', 'true', 'yes')
    if skip:
        logger.info('SKIP_S3_UPLOAD enabled; skipping S3 upload for s3://%s/%s', bucket, key)
        return
    s3 = session.client('s3', region_name=aws_region) if aws_region else session.client('s3')
    s3.put_object(Bucket=bucket, Key=key, Body=data_bytes, ContentType=content_type)
    try:
        s3.head_object(Bucket=bucket, Key=key)
        logger.info('S3 head_object confirmed for s3://%s/%s', bucket, key)
    except Exception:
        logger.warning('S3 upload may not be visible yet for s3://%s/%s', bucket, key)


def upload_dual(bucket: str, key: str, data_bytes: bytes, local_dir: str = None, content_type: str = 'application/octet-stream', write_local: bool = True, upload_s3: bool = True):
    if write_local and local_dir:
        try:
            # local filename derived from key basename
            filename = Path(key).name
            write_local_bytes(local_dir, filename, data_bytes)
        except Exception as e:
            logger.warning('Failed to write local copy: %s', e)

    if upload_s3:
        skip = os.environ.get('SKIP_S3_UPLOAD', 'false').lower() in ('1', 'true', 'yes')
        if skip:
            logger.info('SKIP_S3_UPLOAD enabled; skipping actual S3 upload for %s', key)
            return
        session = get_boto3_session()
        upload_bytes_to_s3(session, bucket, key, data_bytes, content_type=content_type)


def run_dq_if_enabled(local_root: str, out_report: str | None = None):
    run_dq = os.environ.get('RUN_DQ', 'false').lower() in ('1', 'true', 'yes')
    if not run_dq:
        logger.debug('RUN_DQ not enabled; skipping advanced DQ')
        return None

    try:
        from data_extraction.extraction import data_quality
        local_root_path = Path(local_root)
        report_path = Path(out_report) if out_report else None
        return data_quality.run_local_dq_checks(local_root_path, out_report=report_path)
    except Exception as e:
        logger.warning('Advanced DQ run failed: %s', e)
        return None

