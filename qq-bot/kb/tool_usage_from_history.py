# -*- coding: utf-8 -*-
"""tool_usage_from_history.py —— 从真实对话历史里数「她到底调用过哪些工具」

## 为什么这个比推理靠谱

白名单最怕两件事：**留了没用的**（白留，白花钱）和**砍了有用的**（她会突然做不成某件事，
而且不报错，只是"这次没做"）。前者看清单能猜，**后者只能靠证据**。

对话历史里每次工具调用都留了 `"name": "..."`。所以直接从
`data_v4.db` 的 conversations 表把历史拉出来数一遍——
**用过的留下，从没用过的才有资格砍。**

用法：<python> tool_usage_from_history.py [--db <路径>] [--top N]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sqlite3
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_DB = pathlib.Path.home() / ".astrbot" / "data" / "data_v4.db"
# 匹配 tool_calls 里的 name 字段，以及 "function": {"name": "..."}
RX_FUNC = re.compile(r'"function"\s*:\s*\{[^}]*?"name"\s*:\s*"([^"]+)"')
RX_NAME = re.compile(r'"name"\s*:\s*"([A-Za-z0-9_\-\.]{2,64})"')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--top", type=int, default=200)
    a = ap.parse_args()

    db = pathlib.Path(a.db)
    if not db.exists():
        print(f"✗ 找不到 {db}")
        sys.exit(1)

    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    if "conversations" not in tables:
        print(f"✗ 没有 conversations 表。有的是：{tables}")
        sys.exit(1)

    cur.execute("SELECT content FROM conversations")
    rows = cur.fetchall()
    con.close()

    print(f"读了 {len(rows)} 条会话记录\n")

    calls: Counter = Counter()
    blob_total = 0
    for (content,) in rows:
        if not content:
            continue
        blob_total += len(content)
        for rx in (RX_FUNC, RX_NAME):
            for m in rx.finditer(content):
                calls[m.group(1)] += 1

    print(f"历史总文本 {blob_total:,} 字符")
    print(f"抽出 {len(calls)} 个不同的 name，合计 {sum(calls.values()):,} 次\n")

    # 工具名有明显前缀特征，把明显不是工具名的过滤掉
    HINT = ("astrbot_", "send_message", "astr_kb", "web_search", "exa_",
            "llm_", "pc_", "mika_", "yun_", "search_", "send_", "steal_",
            "pic_", "reverse_", "anysearch", "hapi_", "get_", "run_wyc",
            "call_wyc", "play_song", "score_", "complain_", "create-order",
            "query-", "delivery-", "calculate-", "order-list", "draw-")
    tools = {n: c for n, c in calls.items() if any(n.startswith(h) or h in n for h in HINT)}

    print(f"{'调用次数':>8}  工具名")
    print("─" * 60)
    for n, c in sorted(tools.items(), key=lambda kv: -kv[1])[:a.top]:
        print(f"{c:>8}  {n}")

    out = pathlib.Path(r"C:\OneDrive\MikaMisono\qq-bot\kb\_tool_usage.json")
    out.write_text(json.dumps(dict(sorted(tools.items(), key=lambda kv: -kv[1])),
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n✓ 明细写到 {out}")


if __name__ == "__main__":
    main()
