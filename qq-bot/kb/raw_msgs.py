#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""raw_msgs.py —— 原样打印某几条消息（含引用、图片、caption）

`dump_history.py` 会把列表压成一行，看不出引用里到底是什么。这个不做加工。

用法：<python> raw_msgs.py c09cc3e9 11 12 15 16
"""
from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import sys

DB = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "data_v4.db"
key = sys.argv[1] if len(sys.argv) > 1 else "c09cc3e9"
idx = [int(x) for x in sys.argv[2:]] or None

c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
cid, content = c.execute(
    "select conversation_id, content from conversations where conversation_id like ?",
    (key + "%",)).fetchone()
h = json.loads(content or "{}")
h = h.get("history") if isinstance(h, dict) else h
print(f"[{cid[:8]}] 共 {len(h)} 条\n")

for i, m in enumerate(h):
    if idx and i not in idx:
        continue
    print("=" * 74)
    print(f"#{i}  role={m.get('role')}  tool_calls={bool(m.get('tool_calls'))}  "
          f"keys={[k for k in m if k != 'content']}")
    print(json.dumps(m, ensure_ascii=False, indent=1)[:3000])
    print()
