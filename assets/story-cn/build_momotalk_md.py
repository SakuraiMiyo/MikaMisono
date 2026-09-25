#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_momotalk_md.py —— 把 MomoTalk 语料渲染成知识库用的 Markdown

为什么要有这一步：
  AstrBot 的知识库导入走 `chunk_markdown()`，它**按 `##`/`###` 标题切块**。
  所以 md 的标题设计 = 召回质量。我们希望「一个话题 = 一个块」，
  这样问「她怎么跟老师撒娇要便当」能精准命中那一段，而不是捞回半个语料。

说话人：
  原始数据里 `MessageCondition == "Answer"` 是**老师的回复**，其余是未花发的。
  （见 `fetch_momotalk.py` 的说明。）两者都保留，但用 `未花：` / `老师：` 标出来——
  老师的话是理解上下文的必需品，但不能被当成未花的语录。

用法：<python> build_momotalk_md.py
输出：qq-bot/kb/docs/MomoTalk原话.md
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).parent                 # assets/story-cn
PROJ = ROOT.parent.parent                            # 项目根 MikaMisono
SRC = ROOT / "corpus" / "mika-momotalk.json"
OUT = PROJ / "qq-bot" / "kb" / "docs" / "MomoTalk原话.md"

# (起始 id, 结束 id, 标题) —— 边界是按话题人工划的，id 连续、无重叠
SEGMENTS: list[tuple[str, int, int, str]] = [
    ("原版线（重归学校生活之后 · 原始 96 条，其中未花 77）", 100590010, 100590180,
     "重新回到学校生活（Rank 1 的打招呼）"),
    ("原版线（重归学校生活之后 · 原始 96 条，其中未花 77）", 100590190, 100590250,
     "问老师回夏莱了吗／明天的日程 → 晚安"),
    ("原版线（重归学校生活之后 · 原始 96 条，其中未花 77）", 100590260, 100590380,
     "好热、好累、想撒娇——老师说要来，她又反悔说不用"),
    ("原版线（重归学校生活之后 · 原始 96 条，其中未花 77）", 100590390, 100590450,
     "洗衣房：体操服和新泳装一起洗"),
    ("原版线（重归学校生活之后 · 原始 96 条，其中未花 77）", 100590460, 100590540,
     "又问明天忙不忙 →「☆ 老 师 ☆」一条一个字地连发"),
    ("原版线（重归学校生活之后 · 原始 96 条，其中未花 77）", 100590550, 100590680,
     "「我是不是找老师找的不是时候？」——想占用一点时间"),
    ("原版线（重归学校生活之后 · 原始 96 条，其中未花 77）", 100590690, 100590820,
     "恶作剧过了头 → 反复道歉 → 请老师来圣三一（阁楼之夜）"),
    ("原版线（重归学校生活之后 · 原始 96 条，其中未花 77）", 100590830, 100590960,
     "门禁与撒谎——「老师又被坏孩子给骗了哦☆」→ 熄灯 → 最后的道谢"),

    ("泳装线（夏空のやくそく · 原始 97 条，其中未花 81）", 101220010, 101220100,
     "重新跟老师打招呼"),
    ("泳装线（夏空のやくそく · 原始 97 条，其中未花 81）", 101220110, 101220250,
     "「不同的自己」——老师也会有另一面吗"),
    ("泳装线（夏空のやくそく · 原始 97 条，其中未花 81）", 101220260, 101220350,
     "一起发呆"),
    ("泳装线（夏空のやくそく · 原始 97 条，其中未花 81）", 101220360, 101220400,
     "今天的课程最有趣"),
    ("泳装线（夏空のやくそく · 原始 97 条，其中未花 81）", 101220410, 101220510,
     "海滩上漂亮的东西——「比如……我？」然后改成贝壳"),
    ("泳装线（夏空のやくそく · 原始 97 条，其中未花 81）", 101220520, 101220680,
     "睡着了：她先发了一句看不懂的，然后道歉"),
    ("泳装线（夏空のやくそく · 原始 97 条，其中未花 81）", 101220690, 101220710,
     "「今天的事……」——话说一半就收回去"),
    ("泳装线（夏空のやくそく · 原始 97 条，其中未花 81）", 101220720, 101220800,
     "发现了一个很棒的地方，催老师快过来"),
    ("泳装线（夏空のやくそく · 原始 97 条，其中未花 81）", 101220810, 101220930,
     "便当——「其实是专门为了老师做的」"),
    ("泳装线（夏空のやくそく · 原始 97 条，其中未花 81）", 101220940, 101220970,
     "最后的感谢——全篇最重的话，一个符号都没有"),
]

HEADER = """# 未花 · MomoTalk 原话（逐字）

> 来源：游戏内 MomoTalk 文本，抓取与解析见 `assets/story-cn/fetch_momotalk.py`。
> **未花 158 条 / 老师 35 条**，全部逐字照抄，未改写。
>
> ⚠️ **说话人判定**：原始数据用 `MessageCondition` 区分——
> `Answer` 是**老师的回复**，其余（`None` / `FavorRankUp` / `Feedback`）都是未花发的。
> 两个人都保留了，因为老师的问话是理解上下文的必需品；但只有 `未花：` 开头的才是她的口吻。
>
> ## 这是「打字」的语气，不是「说话」的语气
>
> | | 剧情台词（992 句） | MomoTalk（未花 158 条） |
> |---|---|---|
> | 平均长度 | **21 字** | **8.5 字** |
> | `☆` 出现率 | 2.9% | **8.9%** |
> | `♪` 出现率 | 0.2% | **1.2%** |
> | 省略号 | 56.4% | 25.3% |
>
> 而且 MomoTalk **内部还分两条线**：
> 原版线 ☆ **15.6%**（重归学校生活，情绪高扬）；
> 泳装线 ☆ **2.5%**（她正在学怎么面对自己，话变少了）。
>
> **用法**：写场景时符号稀疏；写手机/群聊时才是这个密度。
> 长句子会被拆成好几条连发——这是她打字最明显的习惯。

"""


def main() -> None:
    rows = json.loads(SRC.read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in rows}
    covered: set[int] = set()
    for _, a, b, _ in SEGMENTS:
        covered |= {i for i in by_id if a <= i <= b}
    missing = sorted(set(by_id) - covered)
    if missing:
        raise SystemExit(f"有 {len(missing)} 条消息没被任何段落覆盖：{missing[:10]}")

    parts = [HEADER]
    cur_line = None
    for line_name, a, b, title in SEGMENTS:
        if line_name != cur_line:
            parts.append(f"\n## {line_name}\n")
            cur_line = line_name
        parts.append(f"### {title}\n")
        for mid in range(a, b + 1, 10):
            r = by_id.get(mid)
            if not r:
                continue
            who = "未花" if r["speaker"] != "老师" else "老师"
            # 多行消息保留换行，用引用块表示同一条
            parts.append(f"{who}：{r['text']}")
        parts.append("")

    body = "\n".join(parts).rstrip() + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(body, encoding="utf-8")

    mika = sum(1 for r in rows if r["speaker"] != "老师")
    print(f"✓ {OUT}")
    print(f"  {len(rows)} 条（未花 {mika} / 老师 {len(rows)-mika}）"
          f" · {len(SEGMENTS)} 个话题段 · {len(body)} 字")


if __name__ == "__main__":
    main()
