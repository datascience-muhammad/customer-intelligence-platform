import json
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Optional

LOG = logging.getLogger(__name__)


def load_parquet(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    try:
        return pd.read_parquet(path)
    except Exception:
        return None


def check_completeness(df: Optional[pd.DataFrame], cols):
    results = {}
    if df is None:
        for c in cols:
            results[c] = {'status': 'missing_file'}
        return results
    for c in cols:
        if c not in df.columns:
            results[c] = {'status': 'missing_column'}
            continue
        nulls = int(df[c].isna().sum())
        results[c] = {'null_count': nulls, 'passed': nulls == 0}
    return results


def check_uniqueness(df: Optional[pd.DataFrame], cols):
    results = {}
    if df is None:
        for c in cols:
            results[c] = {'status': 'missing_file'}
        return results
    for c in cols:
        if c not in df.columns:
            results[c] = {'status': 'missing_column'}
            continue
        dup = int(df.duplicated(subset=[c]).sum())
        results[c] = {'duplicate_count': dup, 'passed': dup == 0}
    return results


def check_accuracy_orders(df: Optional[pd.DataFrame]):
    if df is None:
        return {'status': 'missing'}
    bad = df[df['order_amount'] <= 0] if 'order_amount' in df.columns else pd.DataFrame()
    return {'bad_count': int(len(bad)), 'passed': int(len(bad)) == 0}


def check_consistency_orders_customers(orders_df: Optional[pd.DataFrame], customers_df: Optional[pd.DataFrame]):
    if orders_df is None or customers_df is None:
        return {'status': 'missing'}
    if 'customer_id' not in orders_df.columns or 'customer_id' not in customers_df.columns:
        return {'status': 'missing_column'}
    missing = orders_df[~orders_df['customer_id'].isin(customers_df['customer_id'])]
    return {'missing_fk_count': int(len(missing)), 'passed': int(len(missing)) == 0}


def check_timeliness_by_file(path: Path, hours=24):
    if not path.exists():
        return {'status': 'missing'}
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    delta = datetime.now() - mtime
    return {'file_mtime': mtime.isoformat(), 'hours_old': delta.total_seconds() / 3600.0, 'passed': delta <= timedelta(hours=hours)}


def run_local_dq_checks(local_root: Path, out_report: Optional[Path] = None) -> dict:
    """Run DQ checks on files under a local_output root and return a report dict."""
    report = {'checks': {}, 'summary': {}}

    curated = local_root / 'curated'
    staging = local_root / 'staging'
    raw = local_root / 'raw'

    # load curated tables if present
    orders = load_parquet(curated / 'fact_orders.parquet')
    customers = load_parquet(curated / 'dim_customers.parquet')
    support = load_parquet(curated / 'support_tickets.parquet')

    report['checks']['completeness'] = {
        'fact_orders': check_completeness(orders, ['order_id', 'customer_id']),
        'stg_support_tickets': check_completeness(support, ['ticket_id', 'customer_id'])
    }

    report['checks']['accuracy'] = {
        'orders_positive_amount': check_accuracy_orders(orders)
    }

    report['checks']['consistency'] = {
        'orders_customers_fk': check_consistency_orders_customers(orders, customers)
    }

    # timeliness
    report['checks']['timeliness'] = {
        'raw_customers': check_timeliness_by_file(raw / 'customers' / 'customers.parquet'),
        'raw_orders': check_timeliness_by_file(raw / 'orders' / 'orders.parquet')
    }

    report['checks']['uniqueness'] = {
        'fact_orders': check_uniqueness(orders, ['order_id']),
        'stg_support_tickets': check_uniqueness(support, ['ticket_id'])
    }

    failures = 0
    for section in report['checks'].values():
        if isinstance(section, dict):
            for k, v in section.items():
                if isinstance(v, dict):
                    if 'passed' in v and v['passed'] is False:
                        failures += 1
                    else:
                        for sub in v.values():
                            if isinstance(sub, dict) and sub.get('passed') is False:
                                failures += 1

    report['summary']['failures'] = failures

    if out_report:
        out_report.parent.mkdir(parents=True, exist_ok=True)
        out_report.write_text(json.dumps(report, default=str, indent=2))
        LOG.info('Data quality report written to %s', out_report)

    return report

