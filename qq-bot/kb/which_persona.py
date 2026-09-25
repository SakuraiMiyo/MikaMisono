#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""which_persona.py —— 决断：线上真正生效的是哪一份提示词？

`persona_mgr.resolve_selected_persona()` 的取用顺序是：

    1. session_service_config.persona_id   （会话级强制指定，多半为空）
    2. conversation.persona_id             （会话自己的，全是 None）
    3. provider_settings.default_personality  ← 兜底

而 `cmd_config.json` 里写的是 `未小花0924`，不是我一直改的 `未小花！`。
所以必须查清楚：**到底哪一份在跑**，以及两份分别停在哪一天的版本。

做法：对每一份人格，检查它有没有包含今天陆续加进去的那几个标志性小节。
"""
from __future__ import annotations

import json
import os
import pathlib
import sqlite3

DB = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "data_v4.db"
CFG = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "cmd_config.json"
c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

# 今天依次加进去的标记（越靠后越新）
MARKERS = [
    ("语气词硬配额（补丁2）", "语气词的硬配额"),
    ("开口的那一下（补丁3）", "开口的那一下"),
    ("吃音（补丁3）", "吃音"),
    ("口头禅（补丁4）", "口头禅：招呼"),
    ("小圣娅称呼（本轮）", "小圣娅"),
    ("标志性句式核校（补丁5）", "这一节 2026-09-24 全部重核过"),
    ("你住在夏莱（补丁6）", "你住在夏莱"),
    ("主语检验法（本轮）", "把这句里的「我」换成"),
    ("记忆锚点·钥匙不是家", "钥匙，不是家"),
]

cfg = json.loads(CFG.read_text(encoding="utf-8-sig"))
default = cfg.get("provider_settings", {}).get("default_personality")
print(f"default_personality = {default!r}\n")

# 会话级强制指定
print("preferences 里的 session_service_config（会话级人格覆盖）：")
found_override = False
try:
    for scope, sid, key, val in c.execute(
            "select scope, scope_id, key, value from preferences "
            "where key like '%persona%' or key like '%session_service%'"):
        found_override = True
        print(f"  [{scope}] {sid}  {key} = {str(val)[:120]}")
except Exception as e:
    print("  （读不到 preferences：", e, "）")
if not found_override:
    print("  （无）")

print("\n各人格的版本进度：")
for pid, sp, bd, upd in c.execute(
        "select persona_id, system_prompt, begin_dialogs, updated_at from personas "
        "order by length(system_prompt) desc"):
    sp = sp or ""
    mark = "  ★ 默认（线上生效）" if pid == default else ""
    print(f"\n[{pid}]{mark}  {len(sp):,} 字  updated={upd}")
    hit = [name for name, key in MARKERS if key in sp]
    missing = [name for name, key in MARKERS if key not in sp]
    print(f"   有：{'、'.join(hit) if hit else '（无）'}")
    print(f"   缺：{'、'.join(missing) if missing else '（无）'}")
