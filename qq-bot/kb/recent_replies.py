#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""recent_replies.py —— 看她最近实际发出去的话（口吻/符号体检）

改了提示词之后「语气还是怪」，先用这个看**实际产出**，别凭印象。
重点看四件事：
  · 符号密度：☆ ♪ ~ 用了几个（对照实测：MomoTalk 打字 ☆ 8.9% / ♪ 1.3%）
  · 句末有没有句号
  · 有没有舞台指示（「她愣了一下」「身子一僵」）
  · 一条回复拆成几条、每条多少字（规范：2–4 条 × 10–30 字）

用法：<python> recent_replies.py [条数] [会话前8位]
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sqlite3
import statistics
import sys

DB = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "data_v4.db"
n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
key = sys.argv[2] if len(sys.argv) > 2 else None

c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
q = ("select conversation_id, user_id, content from conversations "
     "order by updated_at desc")
rows = list(c.execute(q))

STAGE = re.compile(r"（[^）]{0,40}(抬头|低头|愣|僵|停顿|眨眼|凑近|皱眉|歪头|抿|转身|呼吸)[^）]{0,40}）")
THIRD = re.compile(r"她(的)?(愣了一下|的眼睛|的脸|的手|身子|笑容|声音)")

for cid, uid, content in rows:
    if key and not cid.startswith(key):
        continue
    j = json.loads(content or "{}")
    h = j.get("history") if isinstance(j, dict) else j
    if not isinstance(h, list):
        continue
    msgs = []
    for m in h:
        if not isinstance(m, dict) or m.get("role") != "assistant":
            continue
        t = m.get("content")
        if isinstance(t, list):
            t = "".join(str(s.get("text") or "") for s in t if isinstance(s, dict))
        t = str(t or "").strip()
        if t:
            msgs.append(t)
    if not msgs:
        continue
    print("=" * 76)
    print(f"[{cid[:8]}] {uid}   共 {len(msgs)} 条她的回复，显示最后 {min(n, len(msgs))} 条")
    print("=" * 76)
    for t in msgs[-n:]:
        lines = [x for x in t.split("\n") if x.strip()]
        star, note, tilde = t.count("☆"), t.count("♪"), t.count("~") + t.count("～")
        dot = sum(1 for x in lines if x.rstrip().endswith("。"))
        ln = [len(x.strip()) for x in lines]
        print(f"\n── {len(lines)} 段 / {sum(ln)} 字   ☆{star} ♪{note} ~{tilde}   "
              f"句末句号 {dot} 处   段长 {ln}")
        for x in lines:
            print("   " + x.strip())
        if STAGE.search(t):
            print("   ⚠ 有舞台指示：" + STAGE.search(t).group(0))
        if THIRD.search(t):
            print("   ⚠ 有第三人称叙述：" + THIRD.search(t).group(0))
    print()
