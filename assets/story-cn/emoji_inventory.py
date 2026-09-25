#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""emoji_inventory.py —— 统计未花在 MomoTalk 里实际用过的「小表情」

用途：给预设对话加表情时**有据可依**，而不是凭感觉塞 emoji。

用法：<python> emoji_inventory.py
"""
from __future__ import annotations

import collections
import json
import pathlib
import re
import unicodedata

ROOT = pathlib.Path(__file__).parent
d = json.loads((ROOT / "corpus" / "mika-momotalk.json").read_text(encoding="utf-8"))
txt = [m["text"] for m in d]

# 视为「普通字符」的：汉字、常见中文标点、ASCII
NORMAL_PUNCT = set("，。！？、…—－·：；“”‘’（）《》〈〉「」【】～　 ")
odd: collections.Counter = collections.Counter()
for t in txt:
    for ch in t:
        o = ord(ch)
        if 0x4E00 <= o <= 0x9FFF:
            continue
        if ch in NORMAL_PUNCT:
            continue
        if ch.isascii() and (ch.isalnum() or ch in " _-.,!?'\""):
            continue
        odd[ch] += 1

print(f"MomoTalk 共 {len(txt)} 条\n")
print("用过的非常规字符：")
for ch, n in odd.most_common(40):
    try:
        name = unicodedata.name(ch)
    except ValueError:
        name = "?"
    print(f"   {ch!r:<6} U+{ord(ch):04X}  {n:>3} 次   {name}")

print("\n含「括号类」的整条（颜文字 / 内心话）：")
for t in txt:
    if re.search(r"[（(][^）)]{1,14}[）)]", t):
        print("   ", t)

print("\n含全角波浪的整条：")
for t in txt:
    if "〜" in t or "～" in t or "~" in t:
        print("   ", t)
