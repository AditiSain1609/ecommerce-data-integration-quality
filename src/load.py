"""Transactional, parameterized persistence with idempotent business-key upserts."""
import json
from sqlalchemy import text
from src.database import engine

TABLES = {"customers": ["customer_id","customer_name","email","phone","city","state","country"], "products": ["product_id","product_name","category","price","stock_quantity"], "orders": ["order_id","customer_id","order_date","order_status","total_amount","source_system"], "order_items": ["order_item_id","order_id","product_id","quantity","unit_price","line_total"], "payments": ["payment_id","order_id","payment_method","payment_status","payment_amount","transaction_date","source_system"]}

def load(data, rejected=None, issues=None, db=None):
    db = db or engine
    counts = {}
    with db.begin() as conn:
        for entity in ("customers", "products", "orders", "order_items", "payments"):
            frame = data.get(entity)
            if frame is None: continue
            cols = [c for c in TABLES[entity] if c in frame.columns]
            if not cols: continue
            rows = [{c: (None if str(row[c]) == "<NA>" else row[c]) for c in cols} for _, row in frame[cols].iterrows()]
            if rows:
                updates = ", ".join(f"{c}=excluded.{c}" for c in cols[1:])
                if db.dialect.name == "mysql":
                    sql = f"INSERT INTO {entity} ({', '.join(cols)}) VALUES ({', '.join(':'+c for c in cols)}) ON DUPLICATE KEY UPDATE " + ", ".join(f"{c}=VALUES({c})" for c in cols[1:])
                else:
                    sql = f"INSERT INTO {entity} ({', '.join(cols)}) VALUES ({', '.join(':'+c for c in cols)}) ON CONFLICT({cols[0]}) DO UPDATE SET {updates}"
                conn.execute(text(sql), rows)
            counts[entity] = len(rows)
        for entity, frame in (rejected or {}).items():
            for _, row in frame.iterrows():
                reason = str(row.get("_reject_reason", "rejected"))
                issue_type = (
                    "referential_integrity"
                    if reason.startswith("Unknown ")
                    else "validation"
                )
                conn.execute(text("INSERT INTO raw_records(entity_name,source_system,payload) VALUES(:e,:s,:p)"), {"e":entity,"s":str(row.get("source_system", "unknown")),"p":json.dumps(row.to_dict(), default=str)})
                conn.execute(text("INSERT INTO data_quality_issues(entity_name,record_identifier,column_name,issue_type,issue_description,severity) VALUES(:e,:r,:c,:t,:d,:s)"), {"e":entity,"r":str(row.get(entity[:-1] + "_id", "unknown")),"c":None,"t":issue_type,"d":reason,"s":"high"})
    return counts
