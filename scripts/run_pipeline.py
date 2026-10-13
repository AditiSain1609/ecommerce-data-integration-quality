import logging
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DATA_DIR, BASE_DIR
from src.pipeline import run_pipeline

log_dir = BASE_DIR / "logs"
log_dir.mkdir(exist_ok=True)
handler = RotatingFileHandler(log_dir / "pipeline.log", maxBytes=2_000_000, backupCount=3)
logging.basicConfig(level=logging.INFO, handlers=[handler, logging.StreamHandler()])
result = run_pipeline(DATA_DIR)
print(result)
