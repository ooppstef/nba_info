# NBA 资讯

定时采集中文 NBA 新闻，按球队和球星简单分类，生成手机友好的静态页面。

- **数据源**：虎扑（`m.hupu.com/nba`）、直播吧（`news.zhibo8.com/nba`）
- **采集时间**：每天 11:30 和 19:30（北京时间），由 GitHub Actions 自动运行
- **数据保留**：7 天，过期自动清理
- **分类方式**：基于 `config/teams.json`（30 支球队）和 `config/players.json`（154 位球员/名宿，521 条别名）的词典匹配，不依赖任何大模型或密钥

## 首次使用

1. 把本项目推送到 GitHub 仓库
2. 进入仓库 `Settings` → `Pages`，Source 选择 `Deploy from a branch`，分支选 `main`、目录选 `/ (root)`，保存
3. 进入 `Actions` 标签页，选择「采集 NBA 资讯」，点 `Run workflow` 手动跑一次
4. 跑完后访问 `https://<你的用户名>.github.io/<仓库名>/` 查看页面

之后每天会在 11:30 和 19:30（北京时间）自动更新。页面分五个标签：

| 标签 | 内容 |
| --- | --- |
| 本次新增 | 这一轮刚抓到的新闻（默认打开，适合中午/晚上快速扫一眼） |
| 近 7 天 | 最近 7 天全部新闻，按时间倒序 |
| 按球队 | 30 支球队分组，点开看该队相关新闻 |
| 按球星 | 球星分组，按提及次数排序 |
| 未归类 | 与 NBA 相关但没匹配到具体球队/球星的新闻 |

## 本地运行

```bash
pip install -r requirements.txt
python -m src.main
```

运行后打开根目录的 `index.html` 即可查看。

## 测试

```bash
python -m unittest discover -s tests -t . -v
```

覆盖别名优先级（同名球员如小米切尔/米切尔、安东·沃特森/沃特森）、屏蔽词、7 天清理边界、去重、相关性过滤和 HTML 转义。CI 里每次采集前会先跑这组测试。

## 调整关注范围

- 改球队：编辑 `config/teams.json`，`aliases` 里加上你习惯的叫法（比如「紫金军团」）
- 改球星：编辑 `config/players.json`，加 `name`（显示名）和 `aliases`（标题里可能出现的写法，包括绰号、英文名）
- 长别名优先匹配，匹配过的片段不会重复归类，所以「杰伦·布朗」不会被算成「布朗尼」
- 遇到会被误伤的固定用法（如「富保罗」不该算成保罗），加到 `src/classify.py` 的 `MASK_PHRASES` 里
- 词典改动会在下一轮采集时对全部历史数据生效，不需要手动清理

## 文件说明

| 文件 | 作用 |
| --- | --- |
| `src/sources.py` | 各数据源的采集逻辑 |
| `src/classify.py` | 球队/球星词典匹配 |
| `src/storage.py` | 去重、重新分类、7 天滚动清理、读写 `data/news.json` |
| `src/report.py` | 生成 `index.html` |
| `config/*.json` | 球队/球星词典 |
| `tests/test_pipeline.py` | 不联网的单元测试 |
| `data/news.json` | 最近 7 天的数据 |

## 注意

- 页面只保存新闻标题和原文链接，不转载正文，版权归原网站所有
- 如果某个源改版导致采集失败，页面顶部会显示失败提示，此时需要更新 `src/sources.py` 里的解析规则
