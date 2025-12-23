from pathlib import Path
from dotenv import load_dotenv
import os


def main():
    root = Path(__file__).parent.parent
    env_path = root / '.env'
    if env_path.exists():
        load_dotenv(env_path)

    def _clean(v: str):
      if v is None:
        return ''
      v = v.strip()
      if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        v = v[1:-1]
      return v

    host = _clean(os.getenv('RDS_HOST', ''))
    user = _clean(os.getenv('RDS_USER', ''))
    password = _clean(os.getenv('RDS_PASSWORD', ''))
    port = int(os.getenv('RDS_PORT', '5432'))
    dbname = _clean(os.getenv('RDS_DB', ''))
    schema = _clean(os.getenv('DBT_SCHEMA', 'analytics'))
    threads = int(os.getenv('DBT_THREADS', '4'))

    profiles = f'''shopflow:
  target: dev
  outputs:
    dev:
      type: postgres
      host: "{host}"
      user: "{user}"
      password: "{password}"
      port: {port}
      dbname: "{dbname}"
      schema: "{schema}"
      threads: {threads}
      keepalives_idle: 0
'''

    out_path = Path(__file__).parent / 'profiles_runtime.yml'
    out_path.write_text(profiles)
    print(f"Wrote runtime profiles to {out_path}")


if __name__ == '__main__':
    main()
