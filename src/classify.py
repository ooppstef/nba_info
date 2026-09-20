from .config import load_players, load_teams

MASK = "\u0000"

MASK_PHRASES = ("富保罗", "圣保罗")

NBA_KEYWORDS = (
    "NBA", "nba", "篮球", "季后赛", "总决赛", "常规赛", "全明星", "选秀", "交易",
    "续约", "合同", "场均", "篮板", "助攻", "盖帽", "三分", "罚球", "主帅", "教练",
    "赛季", "夏季联赛", "季前赛", "MVP", "FMVP", "西部", "东部", "联盟", "状元",
    "新秀", "买断", "自由市场", "主场", "客场", "更衣室", "替补", "首发", "伤病",
    "榜眼", "探花", "名人堂", "总经理", "工资帽", "奢侈税", "连败", "连胜", "复出",
    "签约", "球员", "球衣", "球队",
)


def is_relevant(title: str, teams: list[str], players: list[str]) -> bool:
    if teams or players:
        return True
    return any(keyword in title for keyword in NBA_KEYWORDS)


class Classifier:
    def __init__(self):
        teams = load_teams()
        players = load_players()
        self.team_names = {t["id"]: t["name"] for t in teams}
        self.player_names = {p["id"]: p["name"] for p in players}

        entries = []
        for team in teams:
            for alias in team["aliases"]:
                entries.append((alias, "team", team["id"]))
        for player in players:
            for alias in player["aliases"]:
                entries.append((alias, "player", player["id"]))
        entries.sort(key=lambda entry: len(entry[0]), reverse=True)
        self.entries = entries

    def classify(self, text: str) -> tuple[list[str], list[str]]:
        remaining = text or ""
        for phrase in MASK_PHRASES:
            remaining = remaining.replace(phrase, MASK)
        teams, players = [], []
        for alias, kind, key in self.entries:
            if alias not in remaining:
                continue
            remaining = remaining.replace(alias, MASK)
            bucket = teams if kind == "team" else players
            if key not in bucket:
                bucket.append(key)
        return teams, players

    def team_name(self, key: str) -> str:
        return self.team_names.get(key, key)

    def player_name(self, key: str) -> str:
        return self.player_names.get(key, key)
