#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dump_history.py —— 把某个会话的历史逐条列出来（时间线 + 大小）

用来回答「我明明重置了，为什么还带着历史」：
重置会把 `content.history` 清成 []，但之后每来一条消息就会重新累积。
逐条看时间/大小，就能判断是**没清掉**还是**清完又长回来了**。

用法：<python> dump_history.py c09cc3e9
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
rows = list(c.execute(
    "select conversation_id, content, created_at, updated_at from conversations "
    "where conversation_id like ?", (key + "%",)))
for cid, content, ca, ua in rows:
    j = json.loads(content or "{}")
    h = (j.get("history") if isinstance(j, dict) else j) or []
    print(f"[{cid[:8]}]  created={ca}   updated={ua}   {len(h)} 条")
    for i, m in enumerate(h):
        t = m.get("content")
        if isinstance(t, list):
            parts = []
            for s in t:
                if isinstance(s, dict):
                    parts.append("[IMAGE]" if s.get("type") == "image_url"
                                 else str(s.get("text") or ""))
            t = " | ".join(parts)
        t = str(t or "")
        role = m.get("role", "?")
        print(f"  #{i:<3} {role:<10} {len(t):>9,} 字  {t[:110]}".replace("\n", " "))
