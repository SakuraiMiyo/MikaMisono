#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""backup_conversations.py —— 把线上会话历史整份导出（只读，不动线上）

老师要自己在 QQ 里发 `/reset`，所以**这个脚本只做备份，绝不写入**。
打开方式是 `mode=ro`，物理上写不了。

导出内容：
  · `_conversation-backup/<时间戳>/conversations-all.json`  全量原始导出
  · `_conversation-backup/<时间戳>/<会话前8位>-<平台>-<用户>.md`  人读版
  · `_conversation-backup/<时间戳>/INDEX.md`  一览表

用法：<python> backup_conversations.py
"""
from __future__ import annotations

import datetime
import json
import os
import pathlib
import re
import sqlite3

DB = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "data_v4.db"
OUT_ROOT = pathlib.Path(__file__).parent / "_conversation-backup"
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
OUT = OUT_ROOT / STAMP

SAFE = re.compile(r"[^\w\u4e00-\u9fff.-]+")


def parse_history(content: str) -> list[dict]:
    try:
        j = json.loads(content or "{}")
    except Exception:
        return []
    if isinstance(j, dict):
        return j.get("history") or []
    return j if isinstance(j, list) else []


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    cols = [r[1] for r in c.execute("PRAGMA table_info(conversations)")]
    rows = list(c.execute(
        "select conversation_id, inner_conversation_id, created_at, updated_at, "
        "platform_id, user_id, title, persona_id, token_usage, content "
        "from conversations order by updated_at desc"))

    # ① 全量原始导出（一个字节都不动）
    raw = [dict(zip(cols, (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9])))
           for r in rows]
    # 按 columns 名对齐
    raw = []
    for r in rows:
        d = {"conversation_id": r[0], "inner_conversation_id": r[1],
             "created_at": r[2], "updated_at": r[3], "platform_id": r[4],
             "user_id": r[5], "title": r[6], "persona_id": r[7],
             "token_usage": r[8], "content": r[9]}
        d["history"] = parse_history(r[9])
        raw.append(d)
    (OUT / "conversations-all.json").write_text(
        json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")

    index = [f"# 会话历史备份 {STAMP}", "",
             f"> 来源 `{DB}`（**只读导出**，线上未被改动）", "",
             "| 会话 | 平台 | 用户 | 历史 | 字数 | tokens | 最后更新 | 文件 |",
             "|---|---|---|---:|---:|---:|---|---|"]
    total = 0

    for d in raw:
        h = d["history"]
        chars = sum(len(str(m.get("content", ""))) for m in h)
        total += chars
        roles: dict[str, int] = {}
        for m in h:
            r = m.get("role", "?") if isinstance(m, dict) else "?"
            roles[r] = roles.get(r, 0) + 1
        stem = SAFE.sub("_", f"{d['conversation_id'][:8]}-{d['user_id']}")[:80]
        fn = f"{stem}.md"
        lines = [f"# 会话 {d['conversation_id']}", "",
                 f"- 平台：`{d['platform_id']}`",
                 f"- 用户：`{d['user_id']}`",
                 f"- 标题：{d['title']!r}",
                 f"- persona_id：{d['persona_id']!r}",
                 f"- 建立 / 最后更新：`{d['created_at']}` / `{d['updated_at']}`",
                 f"- 历史 **{len(h)} 条** {roles}，共 {chars:,} 字",
                 f"- token_usage：{d['token_usage']}", "",
                 "---", ""]
        for i, m in enumerate(h):
            if not isinstance(m, dict):
                lines.append(f"**[{i}]** `{m!r}`\n")
                continue
            role = m.get("role", "?")
            body = str(m.get("content", ""))
            if len(body) > 4000:
                body = body[:4000] + f"\n…（本条共 {len(body):,} 字，已截断）"
            lines.append(f"### [{i}] {role}\n\n{body}\n")
        (OUT / fn).write_text("\n".join(lines), encoding="utf-8")

        index.append(f"| `{d['conversation_id'][:8]}` | {d['platform_id']} | "
                     f"{d['user_id']} | {len(h)} | {chars:,} | {d['token_usage']} | "
                     f"{d['updated_at']} | `{fn}` |")

    index += ["", f"**合计 {len(raw)} 个会话，{total:,} 字。**", ""]
    (OUT / "INDEX.md").write_text("\n".join(index), encoding="utf-8")

    print(f"✓ 备份到 {OUT}")
    print(f"  conversations-all.json（全量原始）")
    print(f"  {len(raw)} 个会话人读版 + INDEX.md")
    print(f"  合计 {total:,} 字")
    print("\n  ⚠️ 线上一个字都没改。清空请自己在 QQ 里发 /reset。")


if __name__ == "__main__":
    main()
