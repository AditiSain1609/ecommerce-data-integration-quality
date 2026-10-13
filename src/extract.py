"""File extraction with schema checks and raw ingestion metadata."""
from pathlib import Path
import json
import pandas as pd

REQUIRED = {"customers": ["customer_id", "customer_name", "email"], "products": ["product_id", "product_name", "price"], "orders": ["order_id", "customer_id", "order_date", "order_status", "total_amount"], "order_items": ["order_item_id", "order_id", "product_id", "quantity", "unit_price"], "payments": ["payment_id", "order_id", "payment_amount"]}

def extract_file(path, entity=None):
    path = Path(path)
    entity = entity or path.stem
    frame = pd.read_json(path) if path.suffix.lower() == ".json" else pd.read_csv(path)
    frame.columns = [str(c).strip().lower().replace(" ", "_") for c in frame.columns]
    missing = sorted(set(REQUIRED.get(entity, [])) - set(frame.columns))
    if missing:
        raise ValueError(f"{path.name} is missing required columns: {', '.join(missing)}")
    frame["source_system"] = frame.get("source_system", path.stem)
    return frame

def extract_directory(directory):
    return {p.stem: extract_file(p, p.stem) for p in sorted(Path(directory).glob("*") ) if p.suffix.lower() in {".csv", ".json"}}
