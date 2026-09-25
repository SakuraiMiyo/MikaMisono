#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""list_personas.py —— 列出库里所有的人格，看默认用的到底是哪一个

⚠️ 起因：`cmd_config.json` 里写着 `provider_settings.default_personality = '未小花0924'`，
但一直在改的是 `未小花！`——**必须先确认线上真正生效的是哪一个**，
否则改了一整天可能改在了一个没人用的人格上。
"""
from __future__ import annotations

import json
import os
import pathlib
import sqlite3

DB = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "data_v4.db"
CFG = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "cmd_config.json"

c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
cols = [r[1] for r in c.execute("PRAGMA table_info(personas)")]
print("personas 列：", cols)

cfg = json.loads(CFG.read_text(encoding="utf-8-sig"))
ps = cfg.get("provider_settings", {})
default_name = ps.get("default_personality")
print(f"\nprovider_settings.default_personality = {default_name!r}\n")

rows = list(c.execute(
    "select persona_id, system_prompt, begin_dialogs, skills, folder_id, "
    "updated_at from personas order by updated_at desc"))

for pid, sp, bd, sk, folder, upd in rows:
    sp = sp or ""
    try:
        bdn = len(json.loads(bd)) if bd else 0
    except Exception:
        bdn = -1
    try:
        skn = json.loads(sk) if sk else None
    except Exception:
        skn = sk
    mark = "  ← 默认" if pid == default_name else ""
    print(f"[{pid}]{mark}")
    print(f"   system_prompt {len(sp):,} 字   begin_dialogs {bdn} 条   "
          f"skills={skn}   folder={folder}")
    print(f"   更新 {upd}")
    print(f"   开头：{sp[:90].replace(chr(10), ' / ')}")
    print()

# 会话用的是什么
print("会话 → persona_id：")
for cid, uid, pid in c.execute(
        "select conversation_id, user_id, persona_id from conversations "
        "order by updated_at desc"):
    print(f"  {cid[:8]}  persona_id={pid!r}  {uid}")
