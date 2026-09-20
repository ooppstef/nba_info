from collections import Counter

from . import config, report, storage
from .classify import Classifier
from .sources import collect


def main() -> None:
    classifier = Classifier()
    existing = storage.load_items()
    fetched, errors = collect()
    items, added, filtered = storage.merge(existing, fetched, classifier)
    refreshed = storage.reclassify(items, classifier)
    items, dropped = storage.prune(items)
    storage.save_items(items)

    source_counts = Counter(item["source"] for item in items)
    html = report.render(
        items=items,
        added=added,
        errors=errors,
        generated_at=storage.now_local(),
        classifier=classifier,
        source_counts=dict(source_counts),
    )
    config.REPORT_FILE.write_text(html, encoding="utf-8")

    print(
        f"[done] 抓取 {len(fetched)} 条，新增 {len(added)} 条，"
        f"过滤无关 {filtered} 条，刷新分类 {refreshed} 条，"
        f"清理 {dropped} 条，保留 {len(items)} 条"
    )


if __name__ == "__main__":
    main()
