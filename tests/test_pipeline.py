import unittest
from datetime import timedelta

from src import report, storage
from src.classify import Classifier, is_relevant


class ClassifierTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.classifier = Classifier()

    def players_of(self, title):
        _, players = self.classifier.classify(title)
        return players

    def teams_of(self, title):
        teams, _ = self.classifier.classify(title)
        return teams

    def test_longest_alias_wins(self):
        self.assertIn("davion-mitchell", self.players_of("小米切尔：字母哥加盟热火，让我的工作轻松了不少"))
        self.assertNotIn("donovan-mitchell", self.players_of("戴维恩·米切尔：上赛季内心很波动"))
        self.assertNotIn("lebron-james", self.players_of("摄影师晒布朗尼连续完成花式扣篮片段"))
        self.assertNotIn("klay-thompson", self.players_of("阿门·汤普森今日砍下三双"))

    def test_short_name_still_matches(self):
        self.assertIn("donovan-mitchell", self.players_of("米切尔：我今夏招募了詹姆斯"))
        self.assertIn("lebron-james", self.players_of("詹姆斯离开骑士是为了学习赢球"))

    def test_nicknames(self):
        self.assertIn("bam-adebayo", self.players_of("B/R重排17年选秀：塔图姆米切尔热巴前三"))
        self.assertIn("chris-paul", self.players_of("保罗20%有统计以来最差"))
        self.assertIn("paul-george", self.players_of("泡椒在绿军会扮演当年辅佐小卡的角色"))

    def test_team_aliases(self):
        self.assertEqual(["lakers"], self.teams_of("湖人新赛季想争冠防守水平要在联盟前十"))
        self.assertEqual(["mavericks"], self.teams_of("小牛当年那笔交易至今被讨论"))
        self.assertIn("celtics", self.teams_of("绿军阵容深度联盟第一"))

    def test_masked_phrases_do_not_leak(self):
        self.assertNotIn("chris-paul", self.players_of("富保罗：若怀斯曼&库明加发展像塔图姆&布朗一样"))
        self.assertNotIn("dirk-nowitzki", self.players_of("德克萨斯大学晒KD现场观赛照"))

    def test_same_surname_players(self):
        self.assertIn("anton-watson", self.players_of("湖人官方：与前锋安东·沃特森签Ex-10合同"))
        self.assertNotIn("peyton-watson", self.players_of("湖人官方：与前锋安东·沃特森签Ex-10合同"))
        self.assertIn("peyton-watson", self.players_of("沃特森：我觉得自己是球队的重要补充"))

    def test_relevance_filter(self):
        self.assertFalse(is_relevant("今日资讯：文物归国，商标之争，熊猫箍牙，赵家驹夺冠>>", [], []))
        self.assertFalse(is_relevant("从集装箱到酒店，一文浏览名古屋亚运会运动员住宿条件", [], []))
        self.assertTrue(is_relevant("美媒：东部全明星级别球员25个 西部12个", [], []))
        self.assertTrue(is_relevant("随便一个标题", ["lakers"], []))


class StorageTest(unittest.TestCase):
    def test_title_key(self):
        self.assertEqual(storage.title_key("湖人：新赛季，冲冠！"), "湖人新赛季冲冠")
        self.assertEqual(storage.title_key("!!!~~~"), "")

    def test_parse_published(self):
        fallback = storage.now_local()
        parsed, precision = storage.parse_published("2026-09-18 15:02:11", fallback)
        self.assertEqual(precision, "minute")
        self.assertEqual(parsed.hour, 15)
        parsed, precision = storage.parse_published("2026-09-18", fallback)
        self.assertEqual(precision, "day")
        self.assertEqual(parsed.hour, 0)
        parsed, precision = storage.parse_published("", fallback)
        self.assertEqual(precision, "minute")
        self.assertEqual(parsed, fallback)

    def test_prune_keeps_seven_days(self):
        now = storage.now_local()

        def item(days_ago, title):
            stamp = (now - timedelta(days=days_ago)).isoformat(timespec="seconds")
            return {"id": title, "title": title, "first_seen": stamp}

        kept, dropped = storage.prune([item(0.5, "a"), item(6.9, "b"), item(7.1, "c")], now)
        self.assertEqual([entry["title"] for entry in kept], ["a", "b"])
        self.assertEqual(dropped, 1)

    def test_merge_dedupes_and_filters(self):
        classifier = Classifier()
        fetched = [
            {"title": "湖人签下新中锋", "url": "https://a/1", "source": "s", "published": ""},
            {"title": "湖人签下新中锋", "url": "https://a/2", "source": "s", "published": ""},
            {"title": "熊猫箍牙的奇妙故事", "url": "https://a/3", "source": "s", "published": ""},
        ]
        items, added, filtered = storage.merge([], fetched, classifier)
        self.assertEqual(len(items), 1)
        self.assertEqual(len(added), 1)
        self.assertEqual(filtered, 1)
        self.assertEqual(added[0]["teams"], ["lakers"])

        again, added_again, _ = storage.merge(items, fetched, classifier)
        self.assertEqual(len(added_again), 0)
        self.assertEqual(len(again), 1)

    def test_reclassify_updates_stale_items(self):
        classifier = Classifier()
        stale = [
            {
                "id": "old",
                "title": "戴维恩·米切尔：上赛季内心很波动",
                "teams": [],
                "players": ["donovan-mitchell"],
            }
        ]
        changed = storage.reclassify(stale, classifier)
        self.assertEqual(changed, 1)
        self.assertEqual(stale[0]["players"], ["davion-mitchell"])
        self.assertEqual(storage.reclassify(stale, classifier), 0)


class ReportTest(unittest.TestCase):
    def test_renders_empty_state_and_errors(self):
        html = report.render(
            items=[],
            added=[],
            errors=["虎扑: 超时"],
            generated_at=storage.now_local(),
            classifier=Classifier(),
            source_counts={},
        )
        self.assertIn("本次没有新增内容", html)
        self.assertIn("采集失败的源", html)

    def test_escapes_content(self):
        item = {
            "id": "x",
            "title": "<script>alert(1)</script>",
            "url": "https://a/b?c=1&d=2",
            "source": "虎扑",
            "ts": "2026-09-18T12:00:00+08:00",
            "precision": "minute",
            "first_seen": "2026-09-18T12:00:00+08:00",
            "teams": ["lakers"],
            "players": [],
        }
        html = report.render(
            items=[item],
            added=[item],
            errors=[],
            generated_at=storage.now_local(),
            classifier=Classifier(),
            source_counts={"虎扑": 1},
        )
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("https://a/b?c=1&amp;d=2", html)
        self.assertIn("湖人", html)


if __name__ == "__main__":
    unittest.main()
