#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_qq_output.py —— 看她**实际发出去**的话里有多少语气词

`analyze_*.py` 量的是语料（她"该"怎么说）。这个脚本量的是**线上产物**
（她"实际"怎么说）——AstrBot 把消息存在 `~/.astrbot/data/data_v4.db` 里。

两边一对比就知道差在哪：如果语料是 51% 带语气词、线上是 10%，那是模型没听话；
如果线上也是 50%，那问题就不在语气词，而在别处。

用法：<python> check_qq_output.py [最近多少条]
"""
from __future__ import annotations

import collections
import json
import os
import pathlib
import sqlite3
import sys

DB = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "data_v4.db"
STRICT = ["吧", "呢", "啊", "哦", "呀", "嘛", "啦", "喔", "嘞", "咯", "吗", "呐"]
INTERJ = ["嗯", "诶", "欸", "哈", "哎", "唉", "呜", "哼", "咦", "嗷"]


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    tables = [r[0] for r in c.execute(
        "select name from sqlite_master where type='table' order by name")]
    print("表：", ", ".join(tables), "\n")

    target = None
    for t in ("platform_message_history", "messages", "conversations"):
        if t in tables:
            cols = [r[1] for r in c.execute(f"PRAGMA table_info({t})")]
            n = c.execute(f"select count(*) from {t}").fetchone()[0]
            print(f"{t}: {n} 行  {cols}")
            if target is None and n:
                target = t
    if target is None:
        print("找不到消息表")
        return

    cols = [r[1] for r in c.execute(f"PRAGMA table_info({target})")]
    tcol = next((x for x in ("content", "text", "message") if x in cols), None)
    rcol = next((x for x in ("sender_id", "role", "sender") if x in cols), None)
    if not tcol:
        print("找不到内容列")
        return
    print(f"\n用 {target}.{tcol}（角色列 {rcol}）\n")

    q = f"select {tcol}" + (f", {rcol}" if rcol else "") + f" from {target} order by rowid desc limit {limit * 6}"
    rows = list(c.execute(q))
    texts = []
    for r in rows:
        body = r[0]
        if not body:
            continue
        # 内容是 JSON：{"type":"bot","message":[{"type":"plain","text":"..."}]}
        try:
            j = json.loads(body)
        except Exception:
            j = None
        segs = j.get("message") if isinstance(j, dict) else None
        if not segs:
            continue
        if isinstance(j, dict) and j.get("type") not in (None, "bot", "assistant"):
            continue  # 是老师发的
        text = "".join(s.get("text", "") for s in segs if isinstance(s, dict))
        if text.strip():
            texts.append(text)
        if len(texts) >= limit:
            break

    if not texts:
        print("没取到 assistant 消息")
        return

    n = len(texts)
    has = sum(1 for t in texts if any(p in t for p in STRICT))
    fin = sum(1 for t in texts if t.rstrip("。！？!?…~～ ")[-1:] in STRICT)
    cnt = sum(sum(t.count(p) for p in STRICT) for t in texts)
    ij = sum(1 for t in texts if any(p in t for p in INTERJ))
    star = sum(1 for t in texts if "☆" in t)
    tilde = sum(1 for t in texts if "～" in t or "~" in t)
    dot = sum(1 for t in texts if t.rstrip().endswith("。"))
    avg = sum(len(t) for t in texts) / n

    print(f"最近 {n} 条她发的话：")
    print(f"  含语气词         {has:>3}/{n} = {has / n:>6.1%}   （语料基准 51.2%）")
    print(f"  句末是语气词     {fin:>3}/{n} = {fin / n:>6.1%}   （语料基准 33.7%）")
    print(f"  平均每条语气词   {cnt / n:.2f} 个              （语料基准 0.74）")
    print(f"  含嗯/诶/哈等     {ij:>3}/{n} = {ij / n:>6.1%}   （语料基准 16.2%）")
    print(f"  含 ☆             {star:>3}/{n} = {star / n:>6.1%}")
    print(f"  含 ～            {tilde:>3}/{n} = {tilde / n:>6.1%}")
    print(f"  以句号结尾       {dot:>3}/{n} = {dot / n:>6.1%}   ← 应该是 0")
    print(f"  平均长度         {avg:.1f} 字")

    cc = collections.Counter()
    for t in texts:
        for p in STRICT:
            cc[p] += t.count(p)
    print("\n  语气词分布：" + "  ".join(f"{p}{v}" for p, v in cc.most_common()))

    print("\n── 最近 12 条原文 ──")
    for t in texts[:12]:
        print("  " + t.replace("\n", " / ")[:90])


if __name__ == "__main__":
    main()
