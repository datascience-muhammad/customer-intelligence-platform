-- Staging model for support tickets
with raw as (
  select * from {{ source('raw_api', 'support_tickets') }}
)

select
  cast(ticket_id as text) as ticket_id,
  cast(customer_id as text) as customer_id,
  cast(created_date as timestamp) as created_date,
  cast(resolved_date as timestamp) as resolved_date,
  cast(issue_type as text) as subject,  -- map issue_type to subject for compatibility
  cast(priority as text) as priority,
  -- canonicalize status values and normalize (Title Case)
  case
    when lower(trim(status)) in ('open','opened') then 'Open'
    when lower(trim(status)) in ('in progress','in_progress','pending') then 'In Progress'
    when lower(trim(status)) in ('resolved','closed','done') then 'Resolved'
    else upper(substr(lower(trim(status)),1,1)) || substr(lower(trim(status)),2)
  end as status,
  -- resolution / open indicators
  case when lower(trim(status)) in ('resolved','closed','done') or resolved_date is not null then true else false end as is_resolved,
  -- resolution_hours from raw data
  cast(resolution_hours as double precision) as resolution_hours,
  -- hours_open: if resolved use resolution_hours, else calculate from created_date
  case
    when cast(created_date as timestamp) is null then null
    when lower(trim(status)) in ('resolved','closed','done') then cast(resolution_hours as double precision)
    else extract(epoch from (current_timestamp - cast(created_date as timestamp))) / 3600.0
  end as hours_open,
  -- satisfaction_score from raw data
  cast(satisfaction_score as numeric) as satisfaction_score
from raw
 

