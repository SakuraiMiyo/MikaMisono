#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""token_breakdown.py —— 把每一轮 20 多万 token 拆开：人格 / 知识库 / 历史 / 输出

回答两个问题：
  1. **知识库是不是每轮都调？** —— 是，见 `astr_main_agent.py` 的 `_apply_kb`
     （`kb_agentic_mode=False` 时每轮无条件跑），但它在总账里只占很小一块。
  2. **那大头在哪？** —— 在**会话历史**。
"""
from __future__ import annotations

import json
import os
import pathlib
import sqlite3

DB = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "data_v4.db"
CFG = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "cmd_config.json"
c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
cfg = json.loads(CFG.read_text(encoding="utf-8-sig"))

def est(s: str) -> int:
    """AstrBot 自己的估算口径：CJK*0.6 + 其他*0.3"""
    cjk = sum(1 for ch in s if "\u4e00" <= ch <= "\u9fff" or "\u3040" <= ch <= "\u30ff")
    return int(cjk * 0.6 + (len(s) - cjk) * 0.3)

live = cfg.get("provider_settings", {}).get("default_personality")
sp = c.execute("select system_prompt, begin_dialogs from personas where persona_id=?",
               (live,)).fetchone() or ("", "")
prompt, bd = sp[0] or "", json.loads(sp[1] or "[]")

print(f"线上人格 [{live}]")
print(f"  system_prompt      {len(prompt):>9,} 字   ≈ {est(prompt):>8,} token")
print(f"  begin_dialogs      {sum(len(x) for x in bd):>9,} 字   ≈ "
      f"{est(''.join(bd)):>8,} token   （{len(bd)} 条）")
print(f"  ── 固定开销合计           ≈ {est(prompt) + est(''.join(bd)):>8,} token")

print("\n最近 8 轮实测（provider_stats）：")
rows = list(c.execute(
    "select created_at, conversation_id, provider_model, token_input_other, "
    "token_input_cached, token_output from provider_stats order by rowid desc limit 8"))
for ts, cid, model, ix, ic, out in rows:
    tot = (ix or 0) + (ic or 0) + (out or 0)
    print(f"  {str(ts)[:19]}  [{str(cid)[:8]}]  {model}")
    print(f"      输入(未命中缓存) {ix or 0:>9,}   输入(命中缓存) {ic or 0:>9,}   "
          f"输出 {out or 0:>6,}   合计 {tot:>9,}")

print("\n各会话的历史体量：")
for cid, uid, content, tok in c.execute(
        "select conversation_id, user_id, content, token_usage from conversations "
        "order by updated_at desc limit 6"):
    try:
        j = json.loads(content or "{}")
        h = j.get("history") if isinstance(j, dict) else j
    except Exception:
        h = []
    ch = sum(len(str(m.get("content", ""))) for m in h if isinstance(m, dict))
    roles: dict[str, int] = {}
    for m in h:
        if isinstance(m, dict):
            roles[m.get("role", "?")] = roles.get(m.get("role", "?"), 0) + 1
    print(f"  [{cid[:8]}] {uid}")
    print(f"      历史 {len(h)} 条 {roles} / {ch:,} 字   ≈ {est('x' * ch):>10,} token（按字数粗估）")
