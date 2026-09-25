#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_expression_stats.py —— 核对 CSP 给出的「表达指纹」统计是否属实

CSP 声称：
  · 992 句中约 56.4% 含省略号，28.4% 含问号
  · `☆` 只出现在 29 句，`♪` 只出现在 2 句

而项目现有的 `agent/SKILL.md` 把 ☆ / ♪ 描述成「高频」，还写了「☆ 会连着甩」。
两者矛盾，按语料实测为准。

用法：<python> check_expression_stats.py
"""
from __future__ import annotations
import json
import pathlib
from collections import Counter

ROOT = pathlib.Path(__file__).parent
turns = json.loads((ROOT / "corpus" / "mika-turns.json").read_text(encoding="utf-8"))
mika = [t["text"] for t in turns if t["mika"]]
n = len(mika)


def pct(k: int) -> str:
    return f"{k:>4} 句  {k / n * 100:>5.1f}%"


print(f"未花台词 {n} 句\n")
print("── 符号出现率（按「句」计）──")
for name, ch in [("☆", "☆"), ("♪", "♪"), ("～/〜/~", None), ("……", None),
                 ("？/?", None), ("！/!", None), ("☆或♪", None)]:
    if ch:
        k = sum(1 for s in mika if ch in s)
    elif name == "～/〜/~":
        k = sum(1 for s in mika if any(c in s for c in "～〜~"))
    elif name == "……":
        k = sum(1 for s in mika if "……" in s or "..." in s or "…" in s)
    elif name == "？/?":
        k = sum(1 for s in mika if "？" in s or "?" in s)
    elif name == "！/!":
        k = sum(1 for s in mika if "！" in s or "!" in s)
    else:
        k = sum(1 for s in mika if "☆" in s or "♪" in s)
    print(f"  {name:<8} {pct(k)}")

print("\n── 单句符号个数分布（☆ / ♪ / 拖长音）──")
c = Counter(sum(s.count(x) for x in "☆♪") for s in mika)
for k in sorted(c):
    print(f"  含 {k} 个符号：{c[k]:>4} 句")

print("\n── 抖长音个数分布（～ 类）──")
c2 = Counter(sum(s.count(x) for x in "～〜~") for s in mika)
for k in sorted(c2)[:8]:
    print(f"  含 {k} 个拖长音：{c2[k]:>4} 句")

print("\n── 含 ☆ 或 ♪ 的句子（全部）──")
for s in mika:
    if "☆" in s or "♪" in s:
        print(f"   {s[:80]}")

print("\n── 句长分布 ──")
lens = sorted(len(s) for s in mika)
print(f"  平均 {sum(lens)/n:.1f} 字 / 中位 {lens[n//2]} / 最短 {lens[0]} / 最长 {lens[-1]}")
