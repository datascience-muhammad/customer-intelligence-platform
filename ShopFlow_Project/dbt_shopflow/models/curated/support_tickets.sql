{{ config(materialized='table') }}

-- Curated support tickets: materialize cleaned staging view as a curated table
with src as (
    select *
    from {{ ref('stg_support_tickets') }}
)

select *
from src
