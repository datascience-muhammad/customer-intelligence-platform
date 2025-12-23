FROM apache/airflow:2.8.1-python3.11

# Install OS-level deps if needed and switch to root
USER root

# Avoid interactive prompts during apt operations
ENV DEBIAN_FRONTEND=noninteractive

# Update OS packages and install build deps separately so failures are easier to debug.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dbt and common project dependencies
# The build context is the repository root, so the requirements file lives in ./docker/
COPY ./docker/requirements-airflow.txt /requirements-airflow.txt

# Upgrade pip and setuptools, then install Python requirements without cache.
RUN python3 -m pip install --upgrade pip setuptools wheel --no-cache-dir \
    && python3 -m pip install --no-cache-dir -r /requirements-airflow.txt

# Ensure console scripts installed by pip are available on PATH for all users
ENV PATH="/usr/local/bin:/home/airflow/.local/bin:${PATH}"

# Also explicitly install dbt packages system-wide to avoid user-local-only installs
# Do not mask failures so build will fail loudly if a dependency is missing.
RUN python3 -m pip install --no-cache-dir dbt-core==1.5.6 dbt-postgres==1.5.6

USER airflow

WORKDIR /opt/airflow

# Expect the project to be mounted at /opt/airflow/project

# Install dbt into the Airflow user's local site so console scripts live in /home/airflow/.local/bin
RUN python3 -m pip install --user dbt-core==1.5.6 dbt-postgres==1.5.6 || true
