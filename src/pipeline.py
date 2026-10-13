"""Orchestrates extraction, transformation, referential checks, quality and loading."""
import logging
from datetime import datetime, timezone
from sqlalchemy import text
from src.database import engine, initialize
from src.extract import extract_directory
from src.transform import transform_entity
from src.data_integration import validate_references
from src.load import load
from src.quality_checks import score

log = logging.getLogger(__name__)

def run_pipeline(directory, db=None):
    db = db or engine
    initialize(db)
    start = datetime.now(timezone.utc).isoformat()
    with db.begin() as c:
        run_id = c.execute(text("INSERT INTO pipeline_runs(pipeline_name,start_time,status) VALUES('ecommerce_etl',:s,'running')"), {"s":start}).lastrowid
    try:
        extracted = extract_directory(directory)
        clean, rejected = {}, {}
        for entity, frame in extracted.items():
            clean[entity], rejected[entity] = transform_entity(entity, frame)
        # Removing an invalid parent can make its otherwise-valid children
        # orphaned, so repeat reference checks until the clean set is stable.
        refissues = []
        while True:
            current_issues = validate_references(clean)
            if not current_issues:
                break
            for entity, record, column, kind, desc in current_issues:
                issues_rows = clean[entity].index[
                    clean[entity][column].astype(str).eq(desc.split(": ", 1)[-1])
                ]
                if len(issues_rows):
                    idx = issues_rows[0]
                    row = clean[entity].loc[[idx]].copy()
                    row["_reject_reason"] = desc
                    rejected.setdefault(entity, __import__("pandas").DataFrame())
                    rejected[entity] = __import__("pandas").concat(
                        [rejected[entity], row]
                    )
                    clean[entity] = clean[entity].drop(index=idx)
                    refissues.append((entity, record, column, kind, desc))
        counts = load(clean, rejected, refissues, db)
        n_ext = sum(map(len, extracted.values())); n_clean = sum(map(len, clean.values())); n_rej = sum(map(len, rejected.values()))
        n_dup = sum(int(f.duplicated().sum()) for f in extracted.values())
        total = n_ext; valid = n_clean
        with db.begin() as c:
            c.execute(text("UPDATE pipeline_runs SET end_time=:e,status='success',records_extracted=:x,records_processed=:p,records_loaded=:l,records_rejected=:r WHERE run_id=:id"), {"e":datetime.now(timezone.utc).isoformat(),"x":n_ext,"p":n_ext,"l":sum(counts.values()),"r":n_rej,"id":run_id})
            c.execute(text("INSERT INTO data_quality_summary(run_id,total_records,valid_records,invalid_records,duplicate_records,completeness_percentage,validity_percentage,uniqueness_percentage) VALUES(:id,:t,:v,:i,:d,:c,:vscore,:us)"), {"id":run_id,"t":total,"v":valid,"i":n_rej,"d":n_dup,"c":score(valid,total),"vscore":score(valid,total),"us":score(total-n_dup,total)})
        return {"run_id":run_id,"status":"success","extracted":n_ext,"loaded":sum(counts.values()),"rejected":n_rej,"duplicates":n_dup,"counts":counts}
    except Exception as exc:
        log.exception("Pipeline failed")
        with db.begin() as c:
            # Existing installations may still have the original VARCHAR(191)
            # error column; keep the failure path writable without ALTER grants.
            c.execute(text("UPDATE pipeline_runs SET end_time=:e,status='failed',error_message=:m WHERE run_id=:id"), {"e":datetime.now(timezone.utc).isoformat(),"m":str(exc)[:180],"id":run_id})
        raise
