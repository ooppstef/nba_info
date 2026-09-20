import json
import re
from datetime import datetime, timedelta

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import UA, normalize_text

TIMEOUT = 25
HUPU_URL = "https://m.hupu.com/nba"
ZHIBO8_URL = "https://news.zhibo8.com/nba/"


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
    )
    retry = Retry(
        total=2,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_hupu(session: requests.Session) -> list[dict]:
    response = session.get(HUPU_URL, timeout=TIMEOUT)
    response.raise_for_status()
    response.encoding = "utf-8"
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        response.text,
        re.S,
    )
    if not match:
        raise RuntimeError("虎扑页面结构变化：未找到 __NEXT_DATA__")

    page_props = json.loads(match.group(1))["props"]["pageProps"]
    items = []
    for row in page_props.get("newsData") or []:
        title = normalize_text(row.get("title"))
        link = (row.get("link") or "").strip()
        if not title or not link.startswith("http"):
            continue
        items.append(
            {
                "title": title,
                "url": link,
                "source": "虎扑",
                "published": normalize_text(row.get("publishTime")),
            }
        )
    if not items:
        raise RuntimeError("虎扑解析到 0 条，页面结构可能已变化")
    return items


def fetch_zhibo8(session: requests.Session, days: int = 3) -> list[dict]:
    response = session.get(ZHIBO8_URL, timeout=TIMEOUT)
    response.raise_for_status()
    response.encoding = "utf-8"

    pattern = re.compile(
        r'<a[^>]+href="(//news\.zhibo8\.com/nba/(20\d\d-\d\d-\d\d)/[^"]+)"[^>]*>([^<]+)</a>'
    )
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    seen = set()
    items = []
    for url, date, title in pattern.findall(response.text):
        title = normalize_text(title)
        url = "https:" + url
        if not title or url in seen or date < cutoff:
            continue
        seen.add(url)
        items.append(
            {
                "title": title,
                "url": url,
                "source": "直播吧",
                "published": date,
            }
        )
    if not items:
        raise RuntimeError("直播吧解析到 0 条，页面结构可能已变化")
    return items


SOURCES = [
    ("虎扑", fetch_hupu),
    ("直播吧", fetch_zhibo8),
]


def collect() -> tuple[list[dict], list[str]]:
    session = build_session()
    items, errors = [], []
    for name, fetcher in SOURCES:
        try:
            fetched = fetcher(session)
            items.extend(fetched)
            print(f"[source] {name}: {len(fetched)} 条")
        except Exception as exc:
            errors.append(f"{name}: {exc}")
            print(f"[source] {name} 失败: {exc}")
    return items, errors
