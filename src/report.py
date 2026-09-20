import html
from datetime import datetime

STYLE = """
:root{color-scheme:light dark;--bg:#fff;--fg:#16181d;--muted:#6b7280;--card:#f6f7f9;--line:#e6e8eb;--accent:#c8102e;--chip:#eef1f5}
@media (prefers-color-scheme:dark){:root{--bg:#0f1115;--fg:#e9eaec;--muted:#9aa0a6;--card:#171a21;--line:#262b33;--accent:#ff5875;--chip:#222732}}
*{box-sizing:border-box}
body{margin:0;padding:16px 14px 48px;font:16px/1.55 -apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--fg);-webkit-text-size-adjust:100%}
header{max-width:900px;margin:0 auto 14px}
h1{margin:0 0 6px;font-size:22px;letter-spacing:.5px}
.meta{color:var(--muted);font-size:13px}
.meta b{color:var(--fg);font-weight:600}
.tabs{position:sticky;top:0;z-index:5;display:flex;gap:6px;overflow-x:auto;padding:10px 0;margin:0 auto;max-width:900px;background:linear-gradient(var(--bg) 70%,transparent)}
.tab{flex:0 0 auto;padding:7px 14px;border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:999px;font-size:14px;cursor:pointer}
.tab.active{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600}
main{max-width:900px;margin:0 auto}
section[hidden]{display:none}
.group{background:var(--card);border:1px solid var(--line);border-radius:12px;margin:0 0 12px;overflow:hidden}
.group>summary{cursor:pointer;padding:11px 14px;font-weight:600;font-size:15px;display:flex;align-items:center;gap:8px;list-style:none}
.group>summary::-webkit-details-marker{display:none}
.group>summary::before{content:"▸";color:var(--muted);font-size:12px;transition:transform .15s}
.group[open]>summary::before{transform:rotate(90deg)}
.count{color:var(--muted);font-weight:400;font-size:13px}
ul{list-style:none;margin:0;padding:0 14px 12px}
li{padding:9px 0;border-top:1px solid var(--line);font-size:15px}
li:first-child{border-top:none}
li a{color:var(--fg);text-decoration:none}
li a:active,li a:hover{color:var(--accent)}
li .meta{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:4px;font-size:12px;color:var(--muted)}
.src{padding:1px 6px;border-radius:4px;background:var(--chip);color:var(--muted)}
.new{color:var(--accent);font-weight:600}
.chip{padding:1px 6px;border-radius:4px;background:var(--chip);color:var(--muted)}
.empty{color:var(--muted);padding:24px 4px;font-size:14px}
footer{max-width:900px;margin:24px auto 0;color:var(--muted);font-size:12px;line-height:1.7}
"""

SCRIPT = """
const tabs = document.querySelectorAll('.tab');
const sections = document.querySelectorAll('main section');
function activate(id){
  const match = document.querySelector('.tab[data-target="' + id + '"]');
  const target = (match && id) || (tabs[0] && tabs[0].dataset.target);
  tabs.forEach(b => b.classList.toggle('active', b.dataset.target === target));
  sections.forEach(s => { s.hidden = s.id !== target; });
  history.replaceState(null, '', '#' + target);
}
tabs.forEach(b => b.addEventListener('click', () => activate(b.dataset.target)));
activate((location.hash || '').slice(1));
"""


def esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def fmt_time(item: dict) -> str:
    try:
        parsed = datetime.fromisoformat(item["ts"])
    except (KeyError, ValueError):
        return item.get("ts", "")
    if item.get("precision") == "day":
        return parsed.strftime("%m-%d")
    return parsed.strftime("%m-%d %H:%M")


def render_item(item: dict, added_ids: set[str], labels: dict[str, list[str]]) -> str:
    flag = '<span class="new">NEW</span>' if item["id"] in added_ids else ""
    chips = "".join(
        f'<span class="chip">{esc(label)}</span>'
        for label in labels.get(item["id"], [])[:3]
    )
    return (
        f'<li><a href="{esc(item["url"])}" target="_blank" rel="noopener">{esc(item["title"])}</a>'
        f'<span class="meta"><span class="src">{esc(item["source"])}</span>'
        f'<span>{fmt_time(item)}</span>{flag}{chips}</span></li>'
    )


def render_group(title: str, items: list[dict], added_ids: set[str], labels, open_by_default: bool = False) -> str:
    body = "".join(render_item(item, added_ids, labels) for item in items)
    return (
        f'<details class="group"{" open" if open_by_default else ""}>'
        f'<summary>{esc(title)}<span class="count">{len(items)} 条</span></summary>'
        f"<ul>{body}</ul></details>"
    )


def render_section(section_id: str, groups, added_ids: set[str], labels, open_by_default: bool = False, empty_text: str = "暂无数据") -> str:
    if not groups:
        return f'<section id="{section_id}"><p class="empty">{esc(empty_text)}</p></section>'
    blocks = "".join(
        render_group(title, items, added_ids, labels, open_by_default)
        for title, items in groups
    )
    return f'<section id="{section_id}">{blocks}</section>'


def render(items: list[dict], added: list[dict], errors: list[str], generated_at: datetime, classifier, source_counts: dict) -> str:
    added_ids = {item["id"] for item in added}

    labels = {
        item["id"]: [classifier.team_name(key) for key in item.get("teams", [])]
        + [classifier.player_name(key) for key in item.get("players", [])]
        for item in items
    }

    team_groups = [
        (classifier.team_name(key), group) for key, group in _group(items, "teams")
    ]
    player_groups = [
        (classifier.player_name(key), group) for key, group in _group(items, "players")
    ]

    others = [
        item for item in items
        if not item.get("teams") and not item.get("players")
    ]

    latest_groups = [("全部（近 7 天）", items)] if items else []
    sections = [
        render_section(
            "added",
            [("本次新增", added)] if added else [],
            added_ids,
            labels,
            open_by_default=True,
            empty_text="本次没有新增内容",
        ),
        render_section("latest", latest_groups, added_ids, labels, open_by_default=True),
        render_section("teams", team_groups, added_ids, labels),
        render_section("players", player_groups, added_ids, labels),
        render_section(
            "others",
            [("未归类", others)] if others else [],
            added_ids,
            labels,
            open_by_default=True,
            empty_text="未归类内容为空",
        ),
    ]

    source_line = " · ".join(
        f"{esc(name)} {count} 条" for name, count in source_counts.items()
    )
    sources_footer = "、".join(esc(name) for name in source_counts) or "虎扑、直播吧"
    error_line = (
        f'<div class="meta">⚠️ 本次采集失败的源：{esc("；".join(errors))}</div>'
        if errors else ""
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>NBA 资讯 · {generated_at.strftime("%m-%d %H:%M")}</title>
<style>{STYLE}</style>
</head>
<body>
<header>
<h1>NBA 资讯</h1>
<div class="meta">更新于 <b>{generated_at.strftime("%Y-%m-%d %H:%M")}</b> · 共 <b>{len(items)}</b> 条 · 本次新增 <b>{len(added)}</b> 条</div>
<div class="meta">{source_line}</div>
{error_line}
</header>
<nav class="tabs">
<button class="tab" data-target="added">本次新增</button>
<button class="tab" data-target="latest">近 7 天</button>
<button class="tab" data-target="teams">按球队</button>
<button class="tab" data-target="players">按球星</button>
<button class="tab" data-target="others">未归类</button>
</nav>
<main>
{"".join(sections)}
</main>
<footer>保留最近 7 天数据 · 每天 11:30 / 19:30（北京时间）自动更新<br>来源：{sources_footer} · 仅保留标题与链接，版权归原网站所有</footer>
<script>{SCRIPT}</script>
</body>
</html>
"""


def _group(items: list[dict], field: str):
    groups: dict[str, list[dict]] = {}
    for item in items:
        for key in item.get(field, []):
            groups.setdefault(key, []).append(item)
    return sorted(groups.items(), key=lambda entry: -len(entry[1]))
