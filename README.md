# E-Commerce Data Integration and Quality System

A locally runnable data engineering portfolio project that ingests related commerce files, standardizes and validates rows, quarantines failures, loads clean records idempotently, and exposes database-backed metrics in Flask. SQLite is the default to make the first run simple; set `DATABASE_URL` to use MySQL with SQLAlchemy/PyMySQL.

## Architecture

```mermaid
flowchart LR
  A[Orders / Customers / Products / Payments CSV or JSON] --> B[Extraction and schema checks]
  B --> C[Raw audit records]
  B --> D[Transform and integrate]
  D --> E[Data quality validation]
  E --> F[Clean records]
  E --> G[Rejected records and issue log]
  F --> H[(MySQL or SQLite)]
  G --> H
  H --> I[Flask dashboard and explorer]
```

## Features

- Deterministic generator for 500 customers, 100 products, 1,000 orders, more than 1,500 order items, and 1,001 payment rows with deliberate defects.
- CSV and JSON extraction; normalized headers, whitespace, emails, categories, statuses, dates, and numeric values.
- Quarantine for invalid emails, duplicate identifiers, invalid prices, statuses, dates, quantities, and amounts. Raw rejected row payloads and issue descriptions are persisted for audit.
- Cross-entity foreign-key validation and transactional upserts keyed by source business ID.
- Pipeline run history, quality summary scores, dashboard KPIs, charts, issue browsing, searchable entity explorer, and protected pipeline trigger.
- Parameterized SQL for user inputs and CSRF tokens for POST actions.

## Requirements and setup

Python 3.9+ and MySQL 8+ (optional; SQLite is bundled). On macOS use `python3`; on Windows use `py`.

```bash
python3 -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
cp .env.example .env                      # Windows: copy .env.example .env
python scripts/generate_sample_data.py
python scripts/initialize_db.py
python scripts/run_pipeline.py
python app.py
```

Open http://127.0.0.1:5000. Set a unique `SECRET_KEY` and `ADMIN_PASSWORD` in `.env`; the run trigger is disabled until a non-empty admin password is configured. The development server is for local use only.

### MySQL setup

Create the database and a least-privilege local user in MySQL:

```sql
CREATE DATABASE ecommerce_quality CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'ecommerce_user'@'localhost' IDENTIFIED BY 'change-this-password';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, INDEX ON ecommerce_quality.* TO 'ecommerce_user'@'localhost';
```

Set `DATABASE_URL=mysql+pymysql://ecommerce_user:URL_ENCODED_PASSWORD@localhost:3306/ecommerce_quality?charset=utf8mb4` in `.env`, then run initialize and pipeline commands above. URL-encode special characters in the password. SQLite is useful for unit tests and does not require a server.

For an existing MySQL database created by an earlier project version, `CREATE TABLE IF NOT EXISTS` does not change existing column types. Have a database administrator run `mysql -u root -p ecommerce_quality < scripts/migrate_mysql_precision.sql` once. Then rerun the pipeline so decimal amounts are rewritten with cents. The runtime application account does not need `ALTER` privileges.

## Public demo deployment (Render + hosted MySQL)

The checked-in `render.yaml` prepares a Render Free Python web service. Render does not provide managed MySQL on its free plan, so use a separate MySQL provider. Aiven currently offers a no-card Free MySQL service with 1 vCPU, 1 GB RAM, and 1 GB storage. It is single-node without an availability SLA and can power down after extended inactivity; it is suited to a small portfolio demo, not a high-availability production workload. Render Free web services sleep after 15 minutes without traffic, have an ephemeral filesystem, and may take about a minute to wake. The hosted database is separate from that filesystem and remains the durable store. Check provider terms and limits before creating resources.

Before deploying:

1. Create an Aiven Free MySQL service and database named `ecommerce_quality`. Create a dedicated application user with only `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `CREATE`, and `INDEX` grants. Aiven documents that its default `avnadmin` user and ordinary newly created service users have admin-level access unless restricted; use the Aiven user API's `mysql_grants` field (or equivalent supported Terraform setting) to request only those grants. The app's existing startup initializer only creates missing tables/indexes; it does not alter or drop existing tables. Never point it at your Mac's local MySQL server.
2. Download the Aiven service CA certificate. In Render, create a Blueprint from this repository and upload the certificate under **Environment → Secret Files** as `mysql-ca.pem`.
3. Configure the Blueprint's prompted values in Render: `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `DATABASE_URL`. Use a SQLAlchemy URL in this form: `mysql+pymysql://USER:URL_ENCODED_PASSWORD@HOST:PORT/ecommerce_quality?charset=utf8mb4`. Put the CA file path `/etc/secrets/mysql-ca.pem` in `DATABASE_SSL_CA`. Keep all credentials and the CA certificate in Render's environment/secret-file settings; never put them in Git. Render generates `SECRET_KEY` from the Blueprint.
4. Review the database setup before the first deploy. Importing the Flask app runs the existing safe initializer (`CREATE TABLE IF NOT EXISTS` and missing-index creation). On a newly created, empty database that creates the project's tables but does not import or generate records. Existing local database records are not migrated. Do not run `scripts/run_pipeline.py` or trigger `/runs` until you have reviewed the target database and deliberately chosen to load data.
5. Set the database user's privileges without `DROP` or `ALTER`; the initializer needs `CREATE` to remain idempotent at app startup. Use `https://<service>.onrender.com/health` to check the application and database connection after deploy.

The web service does not generate sample data or run the ETL pipeline during deployment. The existing `/runs` trigger remains administrator-only and continues to read the repository's configured `DATA_DIR` when an administrator starts it manually.

### Deployment environment variables

Render sets `APP_ENV=production`, a generated `SECRET_KEY`, and `PYTHON_VERSION=3.11.11`. Configure these values in Render's dashboard when prompted:

- `DATABASE_URL`: hosted MySQL SQLAlchemy connection URL, using the database name `ecommerce_quality` and a URL-encoded password.
- `DATABASE_SSL_CA`: `/etc/secrets/mysql-ca.pem`, the mounted Aiven CA file path; production verifies the certificate and hostname.
- `ADMIN_USERNAME` and `ADMIN_PASSWORD`: unique credentials for the protected pipeline controls.

Production startup refuses a local/SQLite database URL or missing credentials. Local development continues to use `.env` and the existing SQLite fallback when no URL is configured.

### GitHub repository setup

The deployment Blueprint must be in a GitHub repository that Render can access. Verify the Git root before publishing: this project currently sits under a Git repository rooted at the user's home directory, with no commits or remote. Do not push that repository. First create an isolated Git repository containing only this project directory, inspect `git status` and `git check-ignore .env`, database files, and backup files, and then connect that repository to GitHub and Render. No repository or deployment has been published from this workspace.

## Data and rules

The generator uses a fixed seed (`41`); rerun it to recreate the same scenario. Orders identify a source system, customer matching uses customer IDs from this simulated canonical source, and no name-only customer merges are performed. Existing business IDs are updated via upsert. Invalid records are not loaded; rejected values are retained as JSON in `raw_records`, with explanations in `data_quality_issues`.

Revenue is the sum of `orders.total_amount` for orders not marked cancelled. The dashboard aggregates order headers without joining line items or payments, so revenue is not multiplied. Order-item totals are `quantity × unit_price`. Accuracy is not asserted without a trusted external reference.

Scores in this MVP are row based: completeness is non-null required cells divided by required cells across rows; validity is rows passing the entity's implemented validations divided by rows checked; uniqueness is distinct business-key rows divided by rows checked. Referential integrity is checked and reported as individual issues; the current summary schema does not expose a separate referential score. Overall score is not averaged into a misleading scalar. Empty populations score 100 by convention. Unexpected schema columns are accepted; missing required columns fail extraction.

## Database layers

- **Raw:** rejected payloads retained in `raw_records`.
- **Staging:** extracted pandas frames in memory during the run.
- **Clean:** normalized validated entities in relational tables.
- **Rejected:** invalid records persisted to raw audit storage and quality issue rows.

Schema definitions and indexes are in `src/database.py`; `schema.sql` points to the initializer. Documentation: [architecture](docs/architecture.md), [data dictionary](docs/data_dictionary.md), [ETL workflow](docs/etl_workflow.md), [quality rules](docs/data_quality_rules.md).

## Tests

```bash
python -m pytest -q
```

Unit tests use in-memory SQLite and temporary CSVs. No production database is required.

## Troubleshooting

- `missing required columns`: compare the CSV headers with the required fields in `src/extract.py`.
- MySQL connection errors: confirm the server is running, the URL is correct, and the account can create/use the schema.
- Admin run button unavailable: set `ADMIN_PASSWORD` in `.env`, restart Flask, then sign in with `ADMIN_USERNAME`.
- Pipeline failures are recorded in `pipeline_runs`; server logs go to `logs/pipeline.log` when using the CLI script.
- Ensure the selected `DATA_DIR` contains the named CSV/JSON inputs; the app does not accept arbitrary uploads.

## Interview walkthrough

Explain the source contracts, staging boundary, deterministic defects, per-entity transformations, quarantine rationale, referential checks, and transaction/upsert strategy. Demonstrate a run twice to show idempotency, inspect rejected records/issues, then explain why revenue uses order headers and why accuracy needs a trusted reference. Discuss the current limitations and how you would extend schema evolution, source-specific mappings, concurrency-safe run locking, and production authentication.

## GitHub publishing

Create an empty repository on GitHub, then in this project run `git init`, `git add .`, `git commit -m "Build ecommerce data quality system"`, `git branch -M main`, `git remote add origin <repository-url>`, and `git push -u origin main`. Verify `.env` and database files are ignored before pushing.

## Current limitations

The project is a local portfolio application, not a hardened production service. Pagination, full status/resolution filters, per-source schema mapping, concurrent run locking, database-backed session authentication, and persistent clean staging tables are not implemented yet. MySQL-compatible schema setup is available but the integration test exercises SQLite. The UI uses Bootstrap and Chart.js from public CDNs.
