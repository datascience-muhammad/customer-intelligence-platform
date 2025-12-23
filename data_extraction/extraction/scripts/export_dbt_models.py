import duckdb
from pathlib import Path

DB_PATH = Path('dbt_shopflow') / 'dev.duckdb'
OUT_ROOT = Path('data_engineering') / 'extraction' / 'local_output'
STAGING_DIR = OUT_ROOT / 'staging'
CURATED_DIR = OUT_ROOT / 'curated'

STAGING_DIR.mkdir(parents=True, exist_ok=True)
CURATED_DIR.mkdir(parents=True, exist_ok=True)

con = duckdb.connect(str(DB_PATH))

tables = con.execute("SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema LIKE 'main_%';").fetchall()
exported = []
errors = []
for schema, table in tables:
    try:
        if schema.lower().endswith('_staging'):
            out = STAGING_DIR / f"{table}.parquet"
        else:
            out = CURATED_DIR / f"{table}.parquet"
        sql = f'COPY (SELECT * FROM "{schema}"."{table}") TO "{out.as_posix()}" (FORMAT PARQUET)'
        con.execute(sql)
        exported.append(str(out))
    except Exception as e:
        errors.append({'schema': schema, 'table': table, 'error': str(e)})

report = {'exported': exported, 'errors': errors}
print(report)

