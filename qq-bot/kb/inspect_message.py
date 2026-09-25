#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""inspect_message.py —— 看历史里那几条几百万字的"消息"到底是什么

发现：群会话 14,281,016 字里 **97.9% 是 `user` 角色**，
单条最大 **3,611,907 字**。开头都是 `[{"type":"text","text":"[图片]"}, ...`。
八成是**图片被当成 base64 塞进历史**，每轮都要重新带上。

用法：<python> inspect_message.py [会话前8位] [消息下标]
"""
from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import sys

DB = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "data_v4.db"
key = sys.argv[1] if len(sys.argv) > 1 else "c09cc3e9"
idx = int(sys.argv[2]) if len(sys.argv) > 2 else 134

c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
row = c.execute("select conversation_id, content from conversations "
                "where conversation_id like ?", (key + "%",)).fetchone()
cid, content = row
j = json.loads(content or "{}")
h = j.get("history") if isinstance(j, dict) else j
m = h[idx]
t = m.get("content")
print(f"[{cid[:8]}] #{idx}  role={m.get('role')}  类型={type(t).__name__}")

if isinstance(t, str):
    print(f"总长 {len(t):,}")
    try:
        segs = json.loads(t)
    except Exception:
        print("不是 JSON，前 400：", t[:400])
        raise SystemExit(0)
else:
    segs = t

print(f"段数 {len(segs)}\n")
for i, s in enumerate(segs):
    if not isinstance(s, dict):
        print(f"  [{i}] {type(s).__name__} {str(s)[:80]}")
        continue
    keys = list(s.keys())
    body = s.get("text") or s.get("data") or s.get("url") or s.get("file") or ""
    body = str(body)
    print(f"  [{i}] type={s.get('type')!r}  keys={keys}  len={len(body):,}")
    # 找可疑的大字段
    for k, v in s.items():
        if isinstance(v, str) and len(v) > 200:
            vv = v[:160].replace("\n", " ")
            looks_b64 = all(ch.isalnum() or ch in "+/=" for ch in v[:200])
            print(f"        {k}: {len(v):,} 字  {'（像 base64）' if looks_b64 else ''}")
            print(f"           {vv}…")
