#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""list_tools.py —— 看她现在挂着哪些工具（`persona.tools` 决定）

`astr_main_agent.py:612`：

    if (persona and persona.get("tools") is None) or not persona:
        persona_toolset = tmgr.get_full_tool_set()      # ← tools=None 就给她**全部工具**
    else:
        persona_toolset = ToolSet()
        if persona["tools"]:
            for tool_name in persona["tools"]: ...      # ← 非空 = 白名单

所以：**`tools` 是 None 的时候，她连 shell、文件读写、grep 都有。**

实测后果（2026-09-26 群聊）：为了回答「你对群友有什么印象」，
她跑了 6 次工具——grep 日记目录、Get-ChildItem、读 memory.md、读记忆卡——
**59,937 字工具输出全进了对话历史，占那轮历史的 98%**，
而且内容全是 `misonomika.cn`、`memory/cards`、PC 命令回显这类技术档案。
下一轮她读到自己刚"汇报"过的档案，语气自然就飘了。

用法：<python> list_tools.py [人格名]
"""
from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import sys

DB = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "data_v4.db"
CFG = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "cmd_config.json"

cfg = json.loads(CFG.read_text(encoding="utf-8-sig"))
live = sys.argv[1] if len(sys.argv) > 1 else \
    cfg.get("provider_settings", {}).get("default_personality", "")

c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
row = c.execute("select tools from personas where persona_id=?", (live,)).fetchone()
tools = row[0] if row else None
try:
    tools = json.loads(tools) if tools else None
except Exception:
    pass

print(f"线上人格 [{live}]")
print(f"  tools = {tools!r}")
if tools is None:
    print("  ⚠️ 是 None → 拿到的是**全部工具**（含 shell / 文件 / grep）")
elif not tools:
    print("  ⚠️ 是空列表 → 同样会变成「全部工具」")
else:
    print(f"  非空白名单，共 {len(tools)} 个")

p = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data"
skills = p / "skills"
print(f"\n本机 workspace skills（{skills}）：")
if skills.exists():
    for d in sorted(skills.iterdir()):
        print(f"  {d.name}")
else:
    print("  （没有）")
