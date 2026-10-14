"""Flask dashboard for the e-commerce data quality pipeline."""
from functools import wraps
from pathlib import Path
from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash, abort, g
from sqlalchemy import text, inspect
import secrets
import threading
from config import SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD, DATA_DIR, DEBUG, APP_ENV
from dotenv import load_dotenv
from src.database import engine, initialize
from src.pipeline import run_pipeline

load_dotenv()
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config.update(
    MAX_CONTENT_LENGTH=2 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=APP_ENV == "production",
)
initialize()
_pipeline_lock = threading.Lock()

@app.get("/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return jsonify({"status": "unhealthy"}), 503
    return jsonify({"status": "ok"})

@app.before_request
def csrf_protect():
    if request.method == "POST":
        expected = session.get("csrf_token")
        if not expected or request.form.get("csrf_token") != expected:
            abort(400)

@app.context_processor
def inject_csrf():
    if "csrf_token" not in session: session["csrf_token"] = secrets.token_urlsafe(24)
    return {"csrf_token": session["csrf_token"]}

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("admin"): return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapped

@app.get("/")
def index():
    with engine.connect() as c:
        counts={t:c.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar() for t in ("customers","products","orders","data_quality_issues")}
        counts["revenue"]=c.execute(text("SELECT COALESCE(SUM(total_amount),0) FROM orders WHERE lower(order_status) != 'cancelled'")).scalar()
        counts["latest_run"]=c.execute(text("SELECT status FROM pipeline_runs ORDER BY run_id DESC LIMIT 1")).scalar() or "No runs"
        counts["score"]=c.execute(text("SELECT validity_percentage FROM data_quality_summary ORDER BY summary_id DESC LIMIT 1")).scalar() or 0
        trend=c.execute(text("SELECT substr(order_date,1,7) month, SUM(total_amount) revenue, COUNT(*) orders FROM orders GROUP BY month ORDER BY month")).mappings().all()
        statuses=c.execute(text("SELECT order_status label, COUNT(*) value FROM orders GROUP BY order_status")).mappings().all()
    return render_template("dashboard.html", counts=counts, trend=[dict(r) for r in trend], statuses=[dict(r) for r in statuses])

@app.get("/quality")
def quality():
    entity=request.args.get("entity", "")[:40]; severity=request.args.get("severity", "")[:20]
    sql="SELECT * FROM data_quality_issues WHERE (:entity='' OR entity_name=:entity) AND (:severity='' OR severity=:severity) ORDER BY issue_id DESC LIMIT 100"
    with engine.connect() as c: rows=c.execute(text(sql), {"entity":entity,"severity":severity}).mappings().all()
    return render_template("quality.html", rows=[dict(r) for r in rows], entity=entity, severity=severity)

@app.get("/runs")
def runs():
    with engine.connect() as c: rows=c.execute(text("SELECT * FROM pipeline_runs ORDER BY run_id DESC LIMIT 100")).mappings().all()
    return render_template("runs.html", rows=[dict(r) for r in rows])

@app.post("/runs")
@admin_required
def trigger():
    if not _pipeline_lock.acquire(blocking=False):
        flash("A pipeline run is already in progress.", "warning")
        return redirect(url_for("runs"))
    try:
        result=run_pipeline(DATA_DIR); flash(f"Pipeline {result['status']}: {result['loaded']} records loaded, {result['rejected']} rejected.", "success")
    except Exception:
        flash("Pipeline failed. Review the run record and server log.", "danger")
    finally:
        _pipeline_lock.release()
    return redirect(url_for("runs"))

@app.get("/explorer/<entity>")
def explorer(entity):
    allowed={"customers","products","orders","payments"}
    if entity not in allowed: abort(404)
    query=request.args.get("q", "")[:100]
    with engine.connect() as c:
        cols=[item["name"] for item in inspect(engine).get_columns(entity)]
        if query and cols:
            cast_type = "CHAR" if engine.dialect.name == "mysql" else "TEXT"
            where=" OR ".join(f"CAST({col} AS {cast_type}) LIKE :q" for col in cols)
            rows=c.execute(text(f"SELECT * FROM {entity} WHERE {where} LIMIT 100"), {"q":f"%{query}%"}).mappings().all()
        else: rows=c.execute(text(f"SELECT * FROM {entity} LIMIT 100")).mappings().all()
    return render_template("explorer.html", entity=entity, columns=cols, rows=[dict(r) for r in rows], q=query)

@app.get("/api/dashboard")
def api_dashboard():
    with engine.connect() as c:
        return jsonify({"orders":c.execute(text("SELECT COUNT(*) FROM orders")).scalar(),"customers":c.execute(text("SELECT COUNT(*) FROM customers")).scalar(),"issues":c.execute(text("SELECT COUNT(*) FROM data_quality_issues WHERE resolution_status='open'")).scalar()})

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if ADMIN_PASSWORD and request.form.get("username")==ADMIN_USERNAME and request.form.get("password")==ADMIN_PASSWORD:
            session["admin"]=True; return redirect(request.args.get("next") or url_for("runs"))
        flash("Invalid credentials, or configure ADMIN_PASSWORD in .env.", "danger")
    return render_template("login.html")

@app.post("/logout")
def logout():
    session.clear(); return redirect(url_for("index"))

if __name__ == "__main__": app.run(debug=DEBUG)
