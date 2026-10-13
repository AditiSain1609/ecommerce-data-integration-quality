
"""Database engine and schema helpers (SQLite locally, MySQL when configured)."""

from sqlalchemy import create_engine, inspect, text
from config import APP_ENV, DATABASE_SSL_CA, DATABASE_URL

connect_args = {}
if APP_ENV == "production":
    connect_args = {
        "ssl_ca": DATABASE_SSL_CA,
        "ssl_verify_cert": True,
        "ssl_verify_identity": True,
    }

engine = create_engine(
    DATABASE_URL,
    future=True,
    pool_pre_ping=True,
    connect_args=connect_args,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    email TEXT UNIQUE,
    phone TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT,
    price NUMERIC NOT NULL CHECK(price >= 0),
    stock_quantity INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    order_date TEXT NOT NULL,
    order_status TEXT NOT NULL,
    total_amount NUMERIC NOT NULL,
    source_system TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    unit_price NUMERIC NOT NULL CHECK(unit_price >= 0),
    line_total NUMERIC NOT NULL,
    FOREIGN KEY(order_id) REFERENCES orders(order_id),
    FOREIGN KEY(product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    payment_method TEXT,
    payment_status TEXT,
    payment_amount NUMERIC NOT NULL,
    transaction_date TEXT,
    source_system TEXT,
    FOREIGN KEY(order_id) REFERENCES orders(order_id)
);

CREATE TABLE IF NOT EXISTS data_quality_issues (
    issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_name TEXT NOT NULL,
    record_identifier TEXT,
    column_name TEXT,
    issue_type TEXT NOT NULL,
    issue_description TEXT,
    severity TEXT DEFAULT 'medium',
    detected_at TEXT DEFAULT CURRENT_TIMESTAMP,
    resolution_status TEXT DEFAULT 'open'
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_name TEXT,
    start_time TEXT,
    end_time TEXT,
    status TEXT,
    records_extracted INTEGER DEFAULT 0,
    records_processed INTEGER DEFAULT 0,
    records_loaded INTEGER DEFAULT 0,
    records_rejected INTEGER DEFAULT 0,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS data_quality_summary (
    summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    total_records INTEGER,
    valid_records INTEGER,
    invalid_records INTEGER,
    duplicate_records INTEGER,
    completeness_percentage REAL,
    validity_percentage REAL,
    uniqueness_percentage REAL,
    recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(run_id) REFERENCES pipeline_runs(run_id)
);

CREATE TABLE IF NOT EXISTS raw_records (
    raw_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_name TEXT,
    source_system TEXT,
    payload TEXT,
    ingested_at TEXT DEFAULT CURRENT_TIMESTAMP
);

"""


def initialize(engine_override=None):
    db = engine_override or engine
    schema = SCHEMA

    if db.dialect.name == "mysql":
        schema = schema.replace("TEXT", "VARCHAR(191)")
        schema = schema.replace("NUMERIC", "DECIMAL(12,2)")

        # MySQL requires a date/time type for CURRENT_TIMESTAMP defaults.
        for column in (
            "created_at",
            "updated_at",
            "detected_at",
            "recorded_at",
            "ingested_at",
        ):
            schema = schema.replace(
                f"{column} VARCHAR(191) DEFAULT CURRENT_TIMESTAMP",
                f"{column} DATETIME DEFAULT CURRENT_TIMESTAMP",
            )

        schema = schema.replace(
            "INTEGER PRIMARY KEY AUTOINCREMENT",
            "INTEGER PRIMARY KEY AUTO_INCREMENT",
        )

        schema = schema.replace(
            "payload VARCHAR(191)",
            "payload LONGTEXT",
        )
        schema = schema.replace(
            "error_message VARCHAR(191)",
            "error_message LONGTEXT",
        )

    with db.begin() as conn:
        for statement in schema.split(";"):
            if statement.strip():
                conn.execute(text(statement))

        # MySQL does not accept SQLite's ``CREATE INDEX IF NOT EXISTS`` syntax.
        # Inspect existing indexes so initialization stays safe to rerun on both.
        existing = {
            table: {index["name"] for index in inspect(conn).get_indexes(table)}
            for table in ("orders", "data_quality_issues")
        }
        indexes = (
            ("idx_orders_date", "orders", "order_date"),
            (
                "idx_issues_entity_type",
                "data_quality_issues",
                "entity_name, issue_type",
            ),
        )
        for name, table, columns in indexes:
            if name not in existing[table]:
                conn.execute(text(f"CREATE INDEX {name} ON {table}({columns})"))
