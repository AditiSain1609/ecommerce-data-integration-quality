"""Reusable cleaning and validation transformations; rejected rows stay auditable."""
import pandas as pd
from src.quality_checks import email_mask

STATUSES = {"pending", "processing", "shipped", "delivered", "cancelled", "refunded"}

def standardize(frame):
    df = frame.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].map(lambda v: v.strip() if isinstance(v, str) else v)
    if "email" in df: df["email"] = df.email.astype("string").str.strip().str.lower()
    if "category" in df: df["category"] = df.category.astype("string").str.strip().str.title()
    for col in ("order_date", "transaction_date"):
        if col in df:
            parsed = pd.to_datetime(df[col], errors="coerce", utc=True)
            df[col] = parsed.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return df

def transform_entity(entity, frame):
    df = standardize(frame)
    reasons = pd.Series([""] * len(df), index=df.index, dtype="object")
    def reject(mask, message):
        nonlocal reasons
        reasons.loc[mask.fillna(True)] = reasons.loc[mask.fillna(True)].map(lambda x: (x + "; " if x else "") + message)
    if entity == "customers":
        if "email" in df: reject(~email_mask(df.email), "missing or invalid email")
        if "customer_id" in df: reject(df.customer_id.duplicated(keep="first"), "duplicate customer_id")
    elif entity == "products":
        if "price" in df:
            df["price"] = pd.to_numeric(df.price, errors="coerce")
            reject(df.price.isna() | (df.price < 0), "price must be nonnegative")
        if "product_id" in df: reject(df.product_id.duplicated(keep="first"), "duplicate product_id")
    elif entity == "orders":
        if "total_amount" in df:
            df["total_amount"] = pd.to_numeric(df.total_amount, errors="coerce")
            reject(df.total_amount.isna() | (df.total_amount < 0), "invalid total_amount")
        if "order_status" in df: df["order_status"] = df.order_status.astype("string").str.lower()
        if "order_status" in df: reject(~df.order_status.isin(STATUSES), "invalid order_status")
        if "order_date" in df: reject(df.order_date.isna(), "invalid order_date")
        if "order_id" in df: reject(df.order_id.duplicated(keep="first"), "duplicate order_id")
    elif entity == "order_items":
        for c in ("quantity", "unit_price"):
            if c in df: df[c] = pd.to_numeric(df[c], errors="coerce")
        reject(df.quantity.isna() | (df.quantity <= 0), "quantity must be positive")
        reject(df.unit_price.isna() | (df.unit_price < 0), "unit_price must be nonnegative")
        df["line_total"] = df.quantity * df.unit_price
    elif entity == "payments":
        df["payment_amount"] = pd.to_numeric(df.payment_amount, errors="coerce")
        reject(df.payment_amount.isna() | (df.payment_amount < 0), "payment_amount must be nonnegative")
        if "payment_id" in df: reject(df.payment_id.duplicated(keep="first"), "duplicate payment_id")
    df["_reject_reason"] = reasons
    return df[reasons.eq("")].drop(columns="_reject_reason"), df[reasons.ne("")]
