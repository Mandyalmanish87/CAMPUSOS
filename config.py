import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / "campusos.db")))
STATIC_DIR = BASE_DIR / "static"
CAMPUS_DATA_PATH = STATIC_DIR / "data" / "campus_data.json"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
GEMMA_MODEL_NAME = os.getenv("GEMMA_MODEL_NAME", "gemma4:e4b")
AI_TIMEOUT_SECONDS = float(os.getenv("AI_TIMEOUT_SECONDS", "120.0"))
