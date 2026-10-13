"""Cross-file relationship validation using explicit business keys."""
def validate_references(data):
    issues = []
    customers = set(data.get("customers", {}).get("customer_id", []))
    products = set(data.get("products", {}).get("product_id", []))
    orders = set(data.get("orders", {}).get("order_id", []))
    for entity, col, known in (("orders", "customer_id", customers), ("order_items", "order_id", orders), ("order_items", "product_id", products), ("payments", "order_id", orders)):
        frame = data.get(entity)
        if frame is not None and col in frame:
            for idx in frame.index[~frame[col].isin(known)]: issues.append((entity, str(frame.loc[idx].get(entity[:-1] + "_id", idx)), col, "referential_integrity", f"Unknown {col}: {frame.loc[idx, col]}"))
    return issues
