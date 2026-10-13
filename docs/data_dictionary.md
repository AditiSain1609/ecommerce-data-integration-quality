# Data dictionary

| Table | Purpose | Key fields |
|---|---|---|
| customers | Canonical customer contact/location | customer_id PK, email unique |
| products | Sellable catalog | product_id PK, nonnegative price |
| orders | Order header and source attribution | order_id PK, customer_id FK, total_amount |
| order_items | Order line facts | order_item_id PK, order_id/product_id FKs |
| payments | Payment transaction facts | payment_id PK, order_id FK |
| raw_records | Rejected source payload audit | raw_id PK, entity, source, JSON payload |
| data_quality_issues | Individual failed checks | issue_id PK, entity, record, type, severity |
| pipeline_runs | Execution lifecycle/counts | run_id PK, status and counts |
| data_quality_summary | Per-run aggregate quality | summary_id PK, run_id FK, counts and scores |

Dates are ISO-8601 text in the portable schema; monetary values use SQL NUMERIC. Production MySQL deployments should migrate these date columns to `DATETIME` and monetary columns to an explicitly sized `DECIMAL`.
