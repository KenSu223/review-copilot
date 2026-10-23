"""Runtime settings. Values come from environment variables, loaded from the project .env files."""
import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2]  # .../app
PROJECT_DIR = APP_DIR.parent


def _load_env_files() -> None:
    for env_file in (APP_DIR / ".env", PROJECT_DIR / ".env"):
        if not env_file.exists():
            continue
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


_load_env_files()

DATA_DIR = Path(os.environ.get("RC_DATA_DIR", APP_DIR / "data.nosync"))
PDF_DIR = DATA_DIR / "pdfs"
DB_PATH = DATA_DIR / "app.db"
GROBID_URL = os.environ.get("GROBID_URL", "http://localhost:8070")
CONFIG_DIR = APP_DIR / "config"

PDF_DIR.mkdir(parents=True, exist_ok=True)
