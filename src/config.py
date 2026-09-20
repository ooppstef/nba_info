import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
DATA_FILE = ROOT / "data" / "news.json"
REPORT_FILE = ROOT / "index.html"
RETENTION_DAYS = 7
TIMEZONE = "Asia/Shanghai"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_teams():
    return load_json(CONFIG_DIR / "teams.json")


def load_players():
    return load_json(CONFIG_DIR / "players.json")


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()
