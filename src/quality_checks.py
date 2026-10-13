"""Reusable deterministic quality scoring and issue helpers."""
import pandas as pd

def score(numerator, denominator):
    return 100.0 if denominator == 0 else round(100.0 * numerator / denominator, 2)

def duplicate_mask(frame, keys):
    return frame.duplicated(subset=keys, keep="first")

def email_mask(series):
    return series.fillna("").astype(str).str.strip().str.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

def assess(frame, required, keys=None):
    total = len(frame)
    complete = frame[required].notna().all(axis=1) if total else pd.Series(dtype=bool)
    unique = ~duplicate_mask(frame, keys) if keys and total else pd.Series([True] * total)
    return {"total": total, "valid": int(complete.sum()), "invalid": int((~complete).sum()), "duplicates": int((~unique).sum()), "completeness": score(int(frame[required].notna().sum().sum()), total * len(required)), "validity": score(int(complete.sum()), total), "uniqueness": score(int(unique.sum()), total)}
