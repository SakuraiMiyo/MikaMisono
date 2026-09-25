#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dump_history2.py —— 带 tool_calls 标记的完整历史清单

看清楚三件事：
  · 哪些 assistant 条目是**工具调用时的中间话**（`tool_calls=Y`）
  · 它们占了多少字
  · 真正发给用户的正文有多长
"""
from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import sys

DB = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "data_v4.db"
key = sys.argv[1] if len(sys.argv) > 1 else "c09cc3e9"

c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
cid, content = c.execute(
    "select conversation_id, content from conversations where conversation_id like ?",
    (key + "%",)).fetchone()
h = json.loads(content or "{}")
h = h.get("history") if isinstance(h, dict) else h

tot = mid = tool = 0
for i, m in enumerate(h):
    t = m.get("content")
    if isinstance(t, list):
        ss = []
        for s in t:
            if isinstance(s, dict) and s.get("type") == "image_url":
                ss.append("[IMAGE]")
            elif isinstance(s, dict):
                ss.append(str(s.get("text") or ""))
        t = " | ".join(ss)
    t = str(t or "")
    tc = bool(m.get("tool_calls"))
    role = m.get("role", "?")
    tot += len(t)
    if role == "tool":
        tool += len(t)
    elif role == "assistant" and tc:
        mid += len(t)
    print(f"{i:>3} {role:<10} {len(t):>8,} 字  tool_calls={'Y' if tc else '-'}  "
          f"{t[:80]}".replace("\n", " "))
print(f"\n合计 {tot:,} 字  其中 tool 结果 {tool:,}  中间话 {mid:,}  "
      f"（中间话占 {mid / tot:.0%}）")
