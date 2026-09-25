#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tail_conversations.py —— 看线上最近的对话，并按关键词检索

用来排查「她说了不该说的话」：先定位是哪一句，再顺着 KB 找是哪份资料教她的。

用法：
    <python> tail_conversations.py 30                # 最近 30 条（所有会话）
    <python> tail_conversations.py 30 电脑           # 只看含关键词的
    <python> tail_conversations.py 30 电脑 住在      # 多个关键词（任一命中）
"""
from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import sys

DB = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "data_v4.db"


def text_of(m: dict) -> str:
    c = m.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        out = []
        for seg in c:
            if isinstance(seg, dict):
                out.append(str(seg.get("text") or seg.get("content") or ""))
            else:
                out.append(str(seg))
        return "".join(out)
    return str(c or "")


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    keys = sys.argv[2:]

    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = list(c.execute(
        "select conversation_id, user_id, updated_at, content from conversations "
        "order by updated_at desc"))

    msgs: list[tuple[str, str, str, int, str]] = []
    for conv_id, uid, upd, content in rows:
        try:
            j = json.loads(content or "{}")
        except Exception:
            continue
        h = j.get("history") if isinstance(j, dict) else j
        if not isinstance(h, list):
            continue
        for i, m in enumerate(h):
            if isinstance(m, dict):
                msgs.append((upd, conv_id, uid, i, text_of(m),
                             m.get("role", "?")))
    # 按 (会话更新时间, 序内下标) 排序，取每个会话的尾部
    out = []
    for conv_id, uid, upd, content in rows:
        try:
            j = json.loads(content or "{}")
        except Exception:
            continue
        h = j.get("history") if isinstance(j, dict) else j
        if not isinstance(h, list):
            continue
        for i, m in enumerate(h):
            if not isinstance(m, dict):
                continue
            t = text_of(m)
            if not t:
                continue
            if keys and not any(k in t for k in keys):
                continue
            out.append((upd, conv_id, uid, i, m.get("role", "?"), t))

    if keys:
        print(f"关键词 {keys} 命中 {len(out)} 条\n")
        for upd, conv_id, uid, i, role, t in out[-n:]:
            print(f"--- [{conv_id[:8]}] #{i} {role} | {uid}")
            print("    " + t.replace("\n", "\n    ")[:1200])
            print()
    else:
        # 每个会话各取尾部 n 条
        by_conv: dict[str, list] = {}
        for conv_id, uid, upd, content in rows:
            j = json.loads(content or "{}")
            h = j.get("history") if isinstance(j, dict) else j
            if isinstance(h, list):
                by_conv[conv_id] = [(i, m) for i, m in enumerate(h)
                                    if isinstance(m, dict) and text_of(m)]
        for conv_id, items in by_conv.items():
            print("=" * 74)
            print(f"[{conv_id[:8]}] 共 {len(items)} 条，末尾 {n} 条")
            for i, m in items[-n:]:
                print(f"  #{i} {m.get('role','?'):<9} "
                      f"{text_of(m).replace(chr(10), ' / ')[:150]}")


if __name__ == "__main__":
    main()
