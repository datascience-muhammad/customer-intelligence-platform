{% macro set_config_duckdb_home() %}
  -- Set the home directory for DuckDB parquet extension
  {% if execute %}
    {% set sql = "SET home_directory='/tmp'" %}
    {% do run_query(sql) %}
  {% endif %}
{% endmacro %}
