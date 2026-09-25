#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""token_report.py —— 看每一次请求到底吃了多少 token，以及吃在哪

AstrBot 每轮都会往 `provider_stats` 写一行：输入（不缓存）/ 输入（缓存）/ 输出。
这是唯一的**真实账本**——比按字数估算准得多。

用法：<python> token_report.py [最近多少轮]
"""
from __future__ import annotations

import os
import pathlib
import sqlite3
import sys

DB = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "data_v4.db"
c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

print("provider_stats 列：",
      [r[1] for r in c.execute("PRAGMA table_info(provider_stats)")])

n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
cols = [r[1] for r in c.execute("PRAGMA table_info(provider_stats)")]
if not {"token_input_other", "token_input_cached", "token_output"} <= set(cols):
    print("列名不对，实际：", cols)
    raise SystemExit(1)

ts_col = next((x for x in ("created_at", "updated_at", "id") if x in cols), cols[0])
rows = list(c.execute(
    f"select {ts_col}, conversation_id, agent_type, token_input_other, "
    f"token_input_cached, token_output from provider_stats "
    f"order by rowid desc limit {n}"))

print(f"\n最近 {len(rows)} 轮：")
print(f"{'时间':<24}{'会话':<10}{'输入(新)':>9}{'输入(缓存)':>10}{'输出':>7}{'合计':>8}")
tot = 0
for ts, cid, atype, ix, ic, out in rows:
    s = (ix or 0) + (ic or 0) + (out or 0)
    tot += s
    print(f"{str(ts)[:23]:<24}{str(cid)[:8]:<10}{ix or 0:>9,}{ic or 0:>10,}{out or 0:>7,}{s:>8,}")
if rows:
    print(f"\n  这 {len(rows)} 轮平均：{tot // len(rows):,} token/轮")

# 按会话汇总
print("\n按会话汇总（全部历史）：")
agg = {}
for cid, s in c.execute(
        "select conversation_id, sum(coalesce(token_input_other,0)+"
        "coalesce(token_input_cached,0)+coalesce(token_output,0)) "
        "from provider_stats group by conversation_id order by 2 desc"):
    agg[cid] = s
for cid, s in list(agg.items())[:10]:
    print(f"  {str(cid)[:8]:<10}{s:>14,}")
print(f"  {'合计':<10}{sum(agg.values()):>14,}")
