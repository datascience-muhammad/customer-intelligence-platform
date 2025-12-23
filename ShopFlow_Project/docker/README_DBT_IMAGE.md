# Building the dbt image

This explains how to build and optionally push the dbt image used by the `DockerOperator` in `airflow/dags/etl_pipeline_astronomer.py`.

Files:
- `docker/Dockerfile.dbt` — Dockerfile that copies `dbt_shopflow` into the image (based on `dbt-labs/dbt:1.5.6-postgres`).
- `docker/build_and_push.ps1` — PowerShell helper to build and optionally push the image to a registry.

Local build (no push):

```powershell
# from repo root
.\docker\build_and_push.ps1 -Registry "" -ImageName "shopflow/dbt" -Tag "latest"
```

Build and push to a registry:

```powershell
# Example pushing to GitHub Container Registry (ghcr.io)
.\docker\build_and_push.ps1 -Registry "ghcr.io/myorg" -ImageName "shopflow/dbt" -Tag "latest"
```

Using the image in Astronomer / Airflow:
- If the image is pushed to a registry, update the `image` property in `airflow/dags/etl_pipeline_astronomer.py` to the full registry tag (for example `ghcr.io/myorg/shopflow/dbt:latest`).
- If you built the image locally and did not push, ensure the Airflow worker node (Astronomer or local Docker) can access the local image; for Astronomer Cloud you must push to a registry.

Security:
- Use your registry's authentication and do not commit credentials to the repo. Use Astronomer secrets / environment variables to store sensitive values.
