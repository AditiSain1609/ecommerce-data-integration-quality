import pandas as pd
from sqlalchemy import create_engine, text
from src.database import initialize
from src.pipeline import run_pipeline

def test_pipeline_runs_and_is_idempotent(tmp_path):
    source=tmp_path/"in"; source.mkdir()
    pd.DataFrame([{"customer_id":"c1","customer_name":"A","email":"a@example.com"}]).to_csv(source/"customers.csv",index=False)
    pd.DataFrame([{"product_id":"p1","product_name":"P","category":"home","price":4,"stock_quantity":2}]).to_csv(source/"products.csv",index=False)
    pd.DataFrame([{"order_id":"o1","customer_id":"c1","order_date":"2025-01-01","order_status":"delivered","total_amount":4}]).to_csv(source/"orders.csv",index=False)
    db=create_engine("sqlite:///:memory:",future=True)
    initialize(db)
    first=run_pipeline(source,db); second=run_pipeline(source,db)
    with db.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM orders")).scalar()==1
        assert c.execute(text("SELECT COUNT(*) FROM pipeline_runs")).scalar()==2
    assert first["status"]==second["status"]=="success"

def test_failed_schema_is_recorded(tmp_path):
    source=tmp_path/"bad"; source.mkdir()
    (source/"customers.csv").write_text("wrong\nvalue\n")
    db=create_engine("sqlite:///:memory:",future=True)
    initialize(db)
    try:
        run_pipeline(source,db)
        assert False, "expected required-column validation to fail"
    except ValueError:
        pass
    with db.connect() as c:
        assert c.execute(text("SELECT status FROM pipeline_runs")).scalar()=="failed"

def test_orphan_children_of_rejected_parent_are_quarantined(tmp_path):
    source=tmp_path/"cascade"; source.mkdir()
    pd.DataFrame([{"customer_id":"c1","customer_name":"A","email":"invalid"}]).to_csv(source/"customers.csv",index=False)
    pd.DataFrame([{"product_id":"p1","product_name":"P","category":"home","price":4,"stock_quantity":2}]).to_csv(source/"products.csv",index=False)
    pd.DataFrame([{"order_id":"o1","customer_id":"c1","order_date":"2025-01-01","order_status":"delivered","total_amount":4}]).to_csv(source/"orders.csv",index=False)
    pd.DataFrame([{"order_item_id":"i1","order_id":"o1","product_id":"p1","quantity":1,"unit_price":4}]).to_csv(source/"order_items.csv",index=False)
    pd.DataFrame([{"payment_id":"pay1","order_id":"o1","payment_amount":4}]).to_csv(source/"payments.csv",index=False)
    db=create_engine("sqlite:///:memory:",future=True)
    initialize(db)
    result=run_pipeline(source,db)
    with db.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM orders")).scalar()==0
        assert c.execute(text("SELECT COUNT(*) FROM order_items")).scalar()==0
        assert c.execute(text("SELECT COUNT(*) FROM payments")).scalar()==0
        assert c.execute(text("SELECT COUNT(*) FROM data_quality_issues WHERE issue_type='referential_integrity'")).scalar()==3
    assert result["status"]=="success" and result["rejected"]==4
