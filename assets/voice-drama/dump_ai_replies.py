#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dump_ai_replies.py —— 按时间列出她实际发出去的话（带时间戳）

`check_qq_output.py` 只给统计。这个给**时间线**——
用来判断某条回复是"改动之前"还是"改动之后"发的。

用法：<python> dump_ai_replies.py [条数]
"""
from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import sys

DB = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "data_v4.db"


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    cols = [r[1] for r in c.execute("PRAGMA table_info(platform_message_history)")]
    rows = list(c.execute(
        "select created_at, platform_id, sender_name, content "
        "from platform_message_history order by rowid desc limit ?", (limit,)))
    print(f"platform_message_history 列：{cols}\n")
    for created, pid, name, body in rows:
        try:
            j = json.loads(body)
        except Exception:
            print(f"[{created}] <非JSON> {str(body)[:60]}")
            continue
        segs = j.get("message") if isinstance(j, dict) else None
        kind = j.get("type") if isinstance(j, dict) else "?"
        text = "".join(s.get("text", "") for s in segs or [] if isinstance(s, dict))
        text = text.replace("\n", " / ")
        print(f"[{created}] {kind:<6} {name or '':<16} {pid or '':<10} {text[:150]}")


if __name__ == "__main__":
    main()
