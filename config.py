"""Environment based application configuration."""
import os
from pathlib import Path
from sqlalchemy.engine import make_url
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'ecommerce.db'}")
SECRET_KEY = os.getenv("SECRET_KEY", "local-development-key-change-me")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
DATABASE_SSL_CA = os.getenv("DATABASE_SSL_CA", "")
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "sample_data"))
DEBUG = APP_ENV != "production" and os.getenv("FLASK_DEBUG", "0") == "1"

if APP_ENV == "production":
    if not os.getenv("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL must point to the hosted MySQL database in production.")
    if not os.getenv("SECRET_KEY") or SECRET_KEY == "local-development-key-change-me":
        raise RuntimeError("Set a unique SECRET_KEY in the production environment.")
    if not ADMIN_PASSWORD:
        raise RuntimeError("Set ADMIN_PASSWORD in the production environment.")

    database_url = make_url(DATABASE_URL)
    if database_url.get_backend_name() != "mysql":
        raise RuntimeError("Production DATABASE_URL must use the existing MySQL database.")
    if database_url.host in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("Production DATABASE_URL must use a reachable hosted MySQL server.")
    if not all((database_url.host, database_url.username, database_url.password, database_url.database)):
        raise RuntimeError("Production DATABASE_URL must include MySQL host, database, username, and password.")
    if not DATABASE_SSL_CA or not Path(DATABASE_SSL_CA).is_file():
        raise RuntimeError("Set DATABASE_SSL_CA to the mounted CA certificate file for hosted MySQL TLS verification.")
    if database_url.drivername != "mysql+pymysql":
        DATABASE_URL = database_url.set(drivername="mysql+pymysql").render_as_string(hide_password=False)
