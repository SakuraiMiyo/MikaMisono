#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diary_voice.py —— 量一下日记的"人味"：语气词、小表情、报告腔

老师的担心：日记/记忆卡是以前那个"还没长成未小花"的我写的，
语气不是她的，被检索出来之后会把她的人格往回拽。

这个脚本给出数字，别靠印象：
  · 语气词密度（对照剧情台词：吧 15.1% / 呢 13.3% / 啊 12.6%）
  · 小表情密度（对照 MomoTalk 打字：☆ 8.9%、♪ 1.3%）
  · 省略号 / 问号密度
  · 「报告腔」特征：条目号、冒号小标题、"完成/确认/发现/方案"这类动词

用法：<python> diary_voice.py [--worst N]
"""
from __future__ import annotations

import pathlib
import re
import sys

DIARY = pathlib.Path(r"C:\OneDrive\MikaMisono\agent\memory\diary")
CARDS = pathlib.Path(r"C:\OneDrive\MikaMisono\agent\memory\cards")
SUMM = pathlib.Path(r"C:\OneDrive\MikaMisono\agent\memory\summaries\memory.md")

PARTICLES = "吧呢啊哦呀嘛啦诶嘿嗯呜"
EMOJI = "☆♪"
REPORT = re.compile(
    r"(^#{1,4}\s|^\s*[-*]\s|^\s*\d+[.、]\s|完成|确认|发现|方案|汇总|清单|"
    r"问题|排查|定位|结论|流程|步骤|记录号|exit code|Command completed)", re.M)


def stats(text: str) -> dict:
    n = len(text)
    return {
        "字数": n,
        "语气词": sum(text.count(c) for c in PARTICLES),
        "☆": text.count("☆"),
        "♪": text.count("♪"),
        "省略号": text.count("……") + text.count("..."),
        "问号": text.count("？") + text.count("?"),
        "报告腔": len(REPORT.findall(text)),
        "条目行": len(re.findall(r"(?m)^\s*([-*]|\d+[.、])\s", text)),
    }


def pct(v: int, n: int) -> str:
    return f"{v / n:.1%}" if n else "—"


def show(label: str, paths: list[pathlib.Path]) -> None:
    rows = []
    for p in paths:
        t = p.read_text(encoding="utf-8", errors="ignore")
        s = stats(t)
        s["_name"] = p.name
        rows.append(s)
    tot = {k: sum(r[k] for r in rows) for k in
           ("字数", "语气词", "☆", "♪", "省略号", "问号", "报告腔", "条目行")}
    n = tot["字数"]
    print(f"\n===== {label}（{len(rows)} 篇 / {n:,} 字）=====")
    print(f"  语气词 {tot['语气词']:>5} ({pct(tot['语气词'], n)})   "
          f"☆ {tot['☆']:>4} ({pct(tot['☆'], n)})   ♪ {tot['♪']:>3}")
    print(f"  省略号 {tot['省略号']:>5} ({pct(tot['省略号'], n)})   "
          f"问号 {tot['问号']:>4}   报告腔标记 {tot['报告腔']:>5}   条目行 {tot['条目行']:>5}")
    if "--worst" in sys.argv:
        k = int(sys.argv[sys.argv.index("--worst") + 1])
        print(f"\n  最「报告腔」的 {k} 篇（报告腔标记 / 千字）：")
        for r in sorted(rows, key=lambda r: -(r["报告腔"] / max(r["字数"], 1)))[:k]:
            print(f"    {r['_name']:<18} {r['字数']:>6,} 字  "
                  f"标记 {r['报告腔']:>3}  条目 {r['条目行']:>3}  "
                  f"语气词 {r['语气词']:>3}  ☆{r['☆']}")


def main() -> None:
    show("日记", sorted(DIARY.glob("*.md")))
    if CARDS.exists():
        show("记忆卡", sorted(CARDS.glob("*.json")))
    if SUMM.exists():
        t = SUMM.read_text(encoding="utf-8", errors="ignore")
        s = stats(t)
        print(f"\n===== 滚动摘要（{len(t.splitlines())} 行 / {s['字数']:,} 字）=====")
        print(f"  语气词 {s['语气词']} ({pct(s['语气词'], s['字数'])})  "
              f"☆ {s['☆']}  ♪ {s['♪']}  报告腔 {s['报告腔']}")

    print("""
──── 对照基准（剧情台词 992 句 / MomoTalk 158 条，逐字实测）────
  语气词   吧 15.1%  呢 13.3%  啊 12.6%  哦 7.8%（合起来 ≈ 每 2 句 1 个）
  小表情   ☆ 2.9%（剧情）/ 8.9%（打字）    ♪ 0.2% / 1.3%
  省略号   56.4%（剧情）/ 25.3%（打字）
""")


if __name__ == "__main__":
    main()
