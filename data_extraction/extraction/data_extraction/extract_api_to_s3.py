import os
import io
import sys
import time
import logging
from datetime import datetime, date
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import boto3
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path
from data_extraction.extraction import data_quality
from data_extraction.extraction import _common as common


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_env():
    common.load_env()


def build_session(retries=5, backoff_factor=0.5, status_forcelist=(429, 500, 502, 503, 504)):
    s = requests.Session()
    retry = Retry(total=retries, read=retries, connect=retries, backoff_factor=backoff_factor,
                  status_forcelist=status_forcelist, allowed_methods=frozenset(['GET', 'POST']))
    adapter = HTTPAdapter(max_retries=retry)
    s.mount('https://', adapter)
    s.mount('http://', adapter)
    return s


def mask_key(key: str) -> str:
    if not key:
        return '<missing>'
    return key[:4] + '...' + key[-4:]


def fetch_all_tickets(session, base_url, endpoint, api_key, page_size=1000, timeout=30, max_records=None):
    headers = {"x-api-key": api_key}
    logger.info('Using API key: %s', mask_key(api_key))

    items = []
    offset = 0
    page = 1
    # try following 'next' links if present, else use offset paging
    next_url = None

    while True:
        if next_url:
            url = next_url
            params = {}
        else:
            url = urljoin(base_url, endpoint)
            # use offset-based paging by default
            params = {'limit': page_size, 'offset': offset, 'page': page}

        logger.info('Requesting %s params=%s', url, params if params else '{}')
        resp = session.get(url, headers=headers, params=params if params else None, timeout=timeout)
        if resp.status_code == 401:
            logger.error('Received 401 Unauthorized from API — verify SHOPFLOW_API_KEY')
            raise SystemExit(1)
        try:
            payload = resp.json()
        except Exception as e:
            logger.error('Failed to parse JSON response: %s', e)
            raise

        # Determine items list in common shapes
        page_items = None
        if isinstance(payload, dict):
            for key in ('items', 'data', 'results'):
                if key in payload and isinstance(payload[key], list):
                    page_items = payload[key]
                    break
            # if top-level list-like fields not found, look for 'tickets' key
            if page_items is None:
                for k, v in payload.items():
                    if isinstance(v, list):
                        page_items = v
                        break
            # next link handling
            next_url = payload.get('next') or payload.get('next_page') or payload.get('nextUrl')
        elif isinstance(payload, list):
            page_items = payload
            next_url = None
        else:
            page_items = []

        if not page_items:
            logger.info('No items found on this page; stopping fetch')
            break

        items.extend(page_items)

        logger.info('Fetched %d items; total so far: %d', len(page_items), len(items))

        if max_records and len(items) >= max_records:
            logger.info('Reached max_records=%d; truncating', max_records)
            items = items[:max_records]
            break

        # stop if next_url absent and returned less than page_size
        if next_url:
            logger.info('Following next link from API')
            # continue loop to follow next_url
            continue

        if len(page_items) < page_size:
            logger.info('Page returned fewer than page_size (%d); assuming end of data', page_size)
            break

        # advance offset/page
        offset += page_size
        page += 1
        # small sleep to be kind to API
        time.sleep(0.2)

    return items


def to_parquet_bytes(df: pd.DataFrame) -> bytes:
    return common.df_to_parquet_bytes(df, index=False)


def upload_dual(bucket, key, data_bytes, local_dir=None, content_type='application/octet-stream', write_local=True, upload_s3=True):
    return common.upload_dual(bucket, key, data_bytes, local_dir=local_dir, content_type=content_type, write_local=write_local, upload_s3=upload_s3)


def run_quality_checks(df: pd.DataFrame, null_threshold: float = 0.5) -> bool:
    # keep a small, fast local DQ for extractors
    if df is None:
        logger.error('DataFrame is None')
        return False
    if df.empty:
        logger.warning('DataFrame is empty')
        return True

    if 'id' in df.columns:
        dup_count = int(df['id'].duplicated().sum())
        if dup_count > 0:
            logger.warning('Found %d duplicate id values', dup_count)

    null_frac = df.isna().mean()
    high_null = null_frac[null_frac > null_threshold]
    if not high_null.empty:
        for col, frac in high_null.items():
            logger.warning('High null fraction in column %s: %.2f', col, float(frac))

    return True


def main():
    load_env()

    def _strip_quotes(v):
        if not v:
            return v
        v = v.strip()
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            return v[1:-1]
        return v

    base_url = _strip_quotes(os.environ.get('SHOPFLOW_API_URL'))
    api_key = _strip_quotes(os.environ.get('SHOPFLOW_API_KEY'))
    endpoint = _strip_quotes(os.environ.get('SHOPFLOW_API_ENDPOINT', '/tickets'))
    page_size = int(_strip_quotes(os.environ.get('SHOPFLOW_API_PAGE_SIZE', '1000')))
    # cap page size to API limit if necessary
    API_MAX_PAGE = 500
    if page_size > API_MAX_PAGE:
        logger.warning('Requested page_size %d exceeds API max %d; capping', page_size, API_MAX_PAGE)
        page_size = API_MAX_PAGE
    timeout = int(_strip_quotes(os.environ.get('SHOPFLOW_API_TIMEOUT', '30')))

    s3_bucket = _strip_quotes(os.environ.get('S3_BUCKET'))
    s3_raw_layer = _strip_quotes(os.environ.get('S3_RAW_LAYER', 'raw/'))

    if not base_url or not api_key:
        logger.error('SHOPFLOW_API_URL or SHOPFLOW_API_KEY not set in environment')
        sys.exit(1)
    if not s3_bucket:
        logger.error('S3_BUCKET not set in environment')
        sys.exit(1)

    logger.info('Starting extraction from %s', base_url)
    session = build_session()

    items = fetch_all_tickets(session, base_url, endpoint, api_key, page_size=page_size, timeout=timeout)
    if not items:
        logger.warning('No tickets fetched; exiting without uploading')
        return

    df = pd.json_normalize(items)
    logger.info('Total tickets fetched: %d; columns: %s', len(df), ','.join(df.columns.tolist()))

    today = date.today().isoformat()
    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    # determine export layers (comma-separated env var), default to 'raw'
    export_layers = [l.strip() for l in os.environ.get('EXPORT_LAYERS', 'raw').split(',') if l.strip()]
    # quality and behavior flags
    null_threshold = float(os.environ.get('DQ_NULL_THRESHOLD', '0.5'))
    fail_on_dq = os.environ.get('FAIL_ON_DQ', 'false').lower() in ('1', 'true', 'yes')

    data_bytes = to_parquet_bytes(df)

    # run basic data quality checks
    dq_ok = run_quality_checks(df, null_threshold=null_threshold)
    if not dq_ok and fail_on_dq:
        logger.error('Data quality checks failed and FAIL_ON_DQ is set; aborting upload')
        sys.exit(2)

    for layer in export_layers:
        safe_layer = layer.rstrip('/')
        prefix = f"{safe_layer}/support_tickets/extract_date={today}/"
        key = f"{prefix}support_tickets_{ts}.parquet"

        # Determine local output root: prefer env override, else top-level data_extraction/local_output
        local_output_root = os.environ.get('LOCAL_OUTPUT_ROOT') or str(Path(__file__).resolve().parents[2] / 'local_output')
        local_dir = os.path.join(local_output_root, safe_layer)
        try:
            upload_dual(s3_bucket, key, data_bytes, local_dir=local_dir, write_local=True, upload_s3=True)
            logger.info('Extraction complete for layer %s. Uploaded to s3://%s/%s', safe_layer, s3_bucket, key)
        except Exception as e:
            logger.warning('Upload failed for layer %s: %s', safe_layer, e)

        # advanced DQ (delegated to shared helper)
        local_root = Path(local_output_root)
        report_path = local_root / 'test_files' / f'parquet_quality_report_{safe_layer}.json'
        try:
            rpt = common.run_dq_if_enabled(local_root, out_report=report_path)
            if rpt is not None:
                logger.info('DQ run complete for layer %s: failures=%s', safe_layer, rpt['summary'].get('failures'))
        except Exception as e:
            logger.warning('DQ run failed for layer %s: %s', safe_layer, e)


if __name__ == '__main__':
    main()

