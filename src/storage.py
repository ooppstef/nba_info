import hashlib
import json
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import config
from .classify import Classifier, is_relevant

MAX_ITEMS = 4000


def now_local() -> datetime:
    return datetime.now(ZoneInfo(config.TIMEZONE))


def parse_published(raw: str, fallback: datetime) -> tuple[datetime, str]:
    text = (raw or "").strip()
    for fmt, precision in (
        ("%Y-%m-%d %H:%M:%S", "minute"),
        ("%Y-%m-%d %H:%M", "minute"),
        ("%Y-%m-%d", "day"),
    ):
        try:
            parsed = datetime.strptime(text, fmt).replace(tzinfo=ZoneInfo(config.TIMEZONE))
            return parsed, precision
        except ValueError:
            continue
    return fallback, "minute"


def item_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def title_key(title: str) -> str:
    key = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]", "", title or "").lower()
    return key if len(key) >= 4 else ""


def load_items() -> list[dict]:
    if not config.DATA_FILE.exists():
        return []
    try:
        payload = json.loads(config.DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return payload.get("items", [])


def save_items(items: list[dict]) -> None:
    config.DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"items": items}
    config.DATA_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def merge(existing: list[dict], fetched: list[dict], classifier: Classifier) -> tuple[list[dict], list[dict], int]:
    known_ids = {item["id"] for item in existing}
    known_titles = {
        key for key in (title_key(item.get("title", "")) for item in existing) if key
    }
    stamp = now_local().isoformat(timespec="seconds")

    added = []
    filtered = 0
    for raw in fetched:
        url = (raw.get("url") or "").strip()
        title = (raw.get("title") or "").strip()
        if not url or not title:
            continue
        identifier = item_id(url)
        key = title_key(title)
        if identifier in known_ids:
            continue
        if key and key in known_titles:
            continue

        published, precision = parse_published(raw.get("published"), now_local())
        teams, players = classifier.classify(title)
        if not is_relevant(title, teams, players):
            filtered += 1
            continue
        item = {
            "id": identifier,
            "title": title,
            "url": url,
            "source": raw.get("source", ""),
            "ts": published.isoformat(timespec="seconds"),
            "precision": precision,
            "first_seen": stamp,
            "teams": teams,
            "players": players,
        }
        known_ids.add(identifier)
        if key:
            known_titles.add(key)
        added.append(item)

    items = sorted(existing + added, key=lambda item: item["ts"], reverse=True)
    return items, added, filtered


def reclassify(items: list[dict], classifier: Classifier) -> int:
    changed = 0
    for item in items:
        teams, players = classifier.classify(item.get("title", ""))
        if item.get("teams") != teams or item.get("players") != players:
            item["teams"] = teams
            item["players"] = players
            changed += 1
    return changed


def prune(items: list[dict], reference: datetime | None = None) -> tuple[list[dict], int]:
    reference = reference or now_local()
    cutoff = (reference - timedelta(days=config.RETENTION_DAYS)).isoformat(timespec="seconds")
    kept = [item for item in items if item.get("first_seen", "") >= cutoff]
    if len(kept) > MAX_ITEMS:
        kept = kept[:MAX_ITEMS]
    return kept, len(items) - len(kept)
