#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_conversations.py —— 看线上每个会话里还剩多少历史

用来回答「改了人格提示词之后要不要重置对话」：

- **persona 是每轮现读的**（`astr_main_agent.py:1045` → `_ensure_persona_and_skills`
  → `persona_manager.resolve_selected_persona()`），改了立刻生效，**不用重启**。
- 但 `conversations.content` 里存着**过去所有的 user/assistant 消息**。
  模型模仿自己上一条的力度，往往大过模仿 system prompt——
  所以历史越长、越旧，被旧文风拖回去的力量越大。

⚠️ `conversations.persona_id` 也要看一眼：如果某个会话被固定成了别的人格，
新提示词根本不会生效（`resolve_selected_persona` 优先用会话自己的 persona_id）。

用法：<python> check_conversations.py [--dump <id>]
"""
from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import sys

DB = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "data_v4.db"
c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
cols = [r[1] for r in c.execute("PRAGMA table_info(conversations)")]
rows = list(c.execute(
    f"select conversation_id, inner_conversation_id, platform_id, user_id, "
    f"persona_id, updated_at, title, content, token_usage "
    f"from conversations order by updated_at desc"))

print(f"conversations 列：{cols}")
print(f"共 {len(rows)} 个会话\n")
for (conv_id, inner, pid, uid, persona, upd, title, content, tok) in rows:
    try:
        j = json.loads(content or "{}")
        h = j.get("history") if isinstance(j, dict) else None
        if h is None:
            h = j if isinstance(j, list) else []
    except Exception:
        h = []
    roles: dict[str, int] = {}
    for m in h:
        if isinstance(m, dict):
            r = m.get("role", "?")
            roles[r] = roles.get(r, 0) + 1
    chars = sum(len(str(m.get("content", ""))) for m in h if isinstance(m, dict))
    print(f"[{conv_id[:8]}] {upd}   persona={persona!r}")
    print(f"   平台={pid}  用户={uid}  标题={title!r}  tokens={tok}")
    print(f"   历史 {len(h)} 条 {roles}  共 {chars:,} 字")
    print()

if "--dump" in sys.argv:
    key = sys.argv[sys.argv.index("--dump") + 1]
    for (conv_id, _, _, _, _, _, _, content, _) in rows:
        if conv_id.startswith(key):
            j = json.loads(content or "{}")
            h = j.get("history") if isinstance(j, dict) else j
            print(f"==== {conv_id} 全部 {len(h)} 条 ====")
            for m in h[:8]:
                print(f"  {m.get('role'):<10} {str(m.get('content'))[:110]}")
            if len(h) > 8:
                print(f"  … 中间 {len(h) - 14} 条 …")
                for m in h[-6:]:
                    print(f"  {m.get('role'):<10} {str(m.get('content'))[:110]}")
            break
