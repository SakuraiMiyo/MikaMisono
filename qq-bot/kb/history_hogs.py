#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""history_hogs.py —— 会话历史里到底是什么占了几百万字

每轮 22 万 token 的锅不在人格也不在知识库，在**历史**。
这个脚本把历史里最大的那些条按大小排出来，看看是哪一类在吃 token：
是老师的消息、她的回复，还是**工具返回**（网页正文、图片描述、出图结果……）。

用法：<python> history_hogs.py [会话前8位] [看前多少条]
"""
from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import sys

DB = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "data_v4.db"
key = sys.argv[1] if len(sys.argv) > 1 else "c09cc3e9"
top = int(sys.argv[2]) if len(sys.argv) > 2 else 15

c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
row = c.execute("select conversation_id, user_id, content from conversations "
                "where conversation_id like ?", (key + "%",)).fetchone()
if not row:
    print("找不到会话")
    raise SystemExit(1)
cid, uid, content = row
j = json.loads(content or "{}")
h = j.get("history") if isinstance(j, dict) else j
print(f"[{cid[:8]}] {uid}  历史 {len(h)} 条\n")

items = []
for i, m in enumerate(h):
    if not isinstance(m, dict):
        continue
    t = m.get("content")
    s = t if isinstance(t, str) else json.dumps(t, ensure_ascii=False)
    items.append((len(s), i, m.get("role", "?"), s))

total = sum(x[0] for x in items)
print(f"总字数 {total:,}")
by_role: dict[str, int] = {}
for n, _, r, _ in items:
    by_role[r] = by_role.get(r, 0) + n
for r, n in sorted(by_role.items(), key=lambda kv: -kv[1]):
    print(f"  {r:<12}{n:>14,}  ({n / total:.1%})")

print(f"\n最大的 {top} 条：")
for n, i, r, s in sorted(items, reverse=True)[:top]:
    head = s.replace("\n", " ")[:120]
    print(f"  #{i:<4} {r:<10} {n:>10,} 字 | {head}")
