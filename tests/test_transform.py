import pandas as pd
from src.transform import transform_entity

def test_customer_email_normalized_and_bad_row_quarantined():
    good, bad = transform_entity("customers", pd.DataFrame([{"customer_id":"1","customer_name":" A ","email":" A@EXAMPLE.COM "},{"customer_id":"2","customer_name":"B","email":"broken"}]))
    assert len(good) == 1 and good.iloc[0].email == "a@example.com"
    assert len(bad) == 1

def test_negative_product_price_rejected():
    good, bad = transform_entity("products", pd.DataFrame([{"product_id":"p","product_name":"x","price":-1}]))
    assert good.empty and "nonnegative" in bad.iloc[0]._reject_reason

def test_invalid_date_and_status_rejected():
    frame=pd.DataFrame([{"order_id":"o","customer_id":"c","order_date":"bad","order_status":"made_up","total_amount":3}])
    good,bad=transform_entity("orders",frame)
    assert good.empty and "order_date" in bad.iloc[0]._reject_reason
