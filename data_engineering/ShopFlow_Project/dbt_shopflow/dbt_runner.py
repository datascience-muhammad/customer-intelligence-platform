import os
import sys
import subprocess
import shutil
from pathlib import Path
from dotenv import load_dotenv


def main():
    here = Path(__file__).parent
    project_root = here.parent
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded .env from: {env_path}")
    else:
        print(f"No .env at {env_path}; relying on existing environment variables")

    # Build environment for subprocess
    env = os.environ.copy()

    # Default dbt command and project dir
    # Prefer the system 'dbt' binary if present (installed console_script), otherwise
    # fall back to running the dbt package as a module entrypoint `dbt.main`.
    dbt_path = shutil.which('dbt')
    if dbt_path and os.access(dbt_path, os.X_OK):
        dbt_cmd = [dbt_path]
    else:
        dbt_cmd = [sys.executable, '-m', 'dbt.main']
    project_dir = str(project_root / 'dbt_shopflow')

    # Accept extra args (e.g., run/test) passed through
    args = sys.argv[1:] if len(sys.argv) > 1 else ['run', '--models', 'staging+']
    cmd = dbt_cmd + args + ['--project-dir', project_dir, '--profiles-dir', project_dir]

    print('Running:', ' '.join(cmd))

    try:
        result = subprocess.run(cmd, env=env)
    except PermissionError:
        print("Permission denied when attempting to execute dbt.\n"
              "If running inside a container, ensure the dbt binary is installed and executable,\n"
              "or configure the DAG to run dbt inside a dbt Docker image via DockerOperator.")
        sys.exit(1)
    if result.returncode != 0:
        print(f'dbt exited with code {result.returncode}')
        sys.exit(result.returncode)


if __name__ == '__main__':
    main()
