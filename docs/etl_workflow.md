# ETL workflow

1. Extract every CSV/JSON file in the configured input directory and enforce required columns.
2. Normalize headers, trim text, lowercase email, title-case categories, parse dates, and coerce numeric fields.
3. Apply entity rules and retain failures with reasons. Rows with unresolved foreign keys are quarantined.
4. Load clean entities in parent-first order in one transaction. Business primary keys make reruns idempotent.
5. Record run status, counts, duplicate count, and aggregate scores. Exceptions mark the run failed.

Revenue analytics use non-cancelled order headers to avoid multiplication from item/payment joins.
