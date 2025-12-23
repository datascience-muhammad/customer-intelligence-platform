import os
import requests
import logging
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

here = Path(__file__).parent
# project root is two levels up from extraction
env_path = here.parent.parent / '.env'
if env_path.exists():
    load_dotenv(str(env_path))
    logger.info('Loaded .env from %s', env_path)

# Prefer the API env names used by extractors
api_base = os.getenv('SHOPFLOW_API_URL') or os.getenv('API_BASE_URL')
api_key = os.getenv('SHOPFLOW_API_KEY') or os.getenv('API_KEY')

if not api_base or not api_key:
    logger.error('Missing SHOPFLOW_API_URL or SHOPFLOW_API_KEY in environment')
    raise SystemExit(1)

url = f"{api_base.rstrip('/')}/health"
logger.info('Checking health endpoint: %s', url)

try:
    resp = requests.get(url, headers={
        'x-api-key': api_key,
        'accept': 'application/json'
    }, timeout=15)
    logger.info('STATUS: %s', resp.status_code)
    logger.info(resp.text)
    if resp.status_code != 200:
        raise SystemExit(2)
except Exception as e:
    logger.exception('Health check failed: %s', e)
    raise

