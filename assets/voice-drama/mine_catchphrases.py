#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mine_catchphrases.py —— 从语料里**自动挖口癖**

不靠印象、不靠二手百科：直接统计「反复出现的短语」。
一个短语如果在**很多条不同的台词**里都出现，那它就不是内容，是口癖。

三份语料一起挖：
  · 配音转写（742 条日文）—— 口癖最全，因为口语最不修饰
  · 剧情台词（992 条中文）
  · MomoTalk（158 条中文，她打字）

用法：<python> mine_catchphrases.py [每份取前多少条]
"""
from __future__ import annotations

import collections
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).parent
CORPUS = HERE.parent / "story-cn" / "corpus"
sys.path.insert(0, str(HERE))
from analyze_particles import load_lists  # noqa: E402

# 挖 n-gram 时把标点和符号切开，避免把「、」也算进短语
SPLIT = re.compile(r"[\s、。，．？！!?…‥「」『』（）()☆♪〜～\-ー—]+")


def ngrams(text: str, lo: int, hi: int):
    for seg in SPLIT.split(text):
        n = len(seg)
        for k in range(lo, min(hi, n) + 1):
            for i in range(n - k + 1):
                yield seg[i:i + k]


def mine(lines: list[str], lo: int, hi: int, min_lines: int, top: int, label: str):
    """统计 n-gram 出现在多少条不同的台词里（按行去重）。"""
    counter = collections.Counter()
    for t in lines:
        for g in set(ngrams(t, lo, hi)):
            counter[g] += 1
    n = len(lines)
    # 只保留「跨多条台词复现」的，并且过滤掉被更长的短语完全包含的
    hits = [(g, c) for g, c in counter.items() if c >= min_lines]
    hits.sort(key=lambda kv: (-kv[1], -len(kv[0])))
    keep = []
    for g, c in hits:
        # 如果存在一个更长的高频短语包含它，且频率相近，就丢掉短的
        if any(g != h and g in h and ch >= c * 0.75 for h, ch in hits):
            continue
        keep.append((g, c))
    print(f"\n{'=' * 72}\n【{label}】{n} 条，反复出现的短语（按出现条数排序）\n{'=' * 72}")
    for g, c in keep[:top]:
        print(f"  {c:>4} 条 ({c / n:>5.1%})  「{g}」")


def main() -> None:
    top = int(sys.argv[1]) if len(sys.argv) > 1 else 30

    ja = [r["text"] for r in load_lists()]
    mine(ja, 2, 6, 4, top, "配音转写（日文）")

    only = json.loads((CORPUS / "mika-only.json").read_text(encoding="utf-8"))
    zh_story = [r["text"] for r in only if r.get("text")]
    mine(zh_story, 2, 6, 5, top, "剧情台词（中文）")

    moto = json.loads((CORPUS / "mika-momotalk.json").read_text(encoding="utf-8"))
    zh_moto = [r["text"] for r in moto
               if r.get("speaker") == "未花" and r.get("text")]
    mine(zh_moto, 2, 6, 3, top, "MomoTalk（中文·打字）")

    # 日文语料里，句首第一个词单独看一遍——招呼语都在这里
    print(f"\n{'=' * 72}\n【配音转写】句首词频（截到第一个标点）\n{'=' * 72}")
    head = collections.Counter()
    for t in ja:
        w = SPLIT.split(t)[0] if SPLIT.split(t) else ""
        if 0 < len(w) <= 8:
            head[w] += 1
    for w, c in head.most_common(40):
        print(f"  {c:>4}  {w}")


if __name__ == "__main__":
    main()
