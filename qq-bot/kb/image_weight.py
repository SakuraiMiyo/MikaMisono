#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""image_weight.py —— 量化：历史里的图片到底占多少

`history_hogs.py` 说群会话 1428 万字里 97.9% 是 user 消息。
再看一层：那些 user 消息里，**图片段**占多少、有没有 caption。
"""
from __future__ import annotations

import json
import os
import pathlib
import sqlite3

DB = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "data_v4.db"
c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

for cid, uid, content in c.execute(
        "select conversation_id, user_id, content from conversations "
        "order by updated_at desc limit 4"):
    j = json.loads(content or "{}")
    h = j.get("history") if isinstance(j, dict) else j
    if not isinstance(h, list):
        continue
    img_chars = txt_chars = cap_chars = 0
    n_img = 0
    for m in h:
        if not isinstance(m, dict):
            continue
        segs = m.get("content")
        if isinstance(segs, str):
            try:
                segs = json.loads(segs)
            except Exception:
                txt_chars += len(segs)
                continue
        if not isinstance(segs, list):
            continue
        for s in segs:
            if not isinstance(s, dict):
                continue
            if s.get("type") == "image_url":
                n_img += 1
                blob = s.get("image_url")
                img_chars += len(json.dumps(blob, ensure_ascii=False))
            else:
                t = str(s.get("text") or "")
                txt_chars += len(t)
                if "<image_caption>" in t:
                    cap_chars += len(t)
    tot = img_chars + txt_chars
    print(f"[{cid[:8]}] {uid}")
    print(f"   历史 {len(h)} 条")
    print(f"   图片段 {n_img} 个，占 {img_chars:>12,} 字  "
          f"({img_chars / tot:.1%} of {tot:,})" if tot else "   （空）")
    print(f"   文字   {txt_chars:>12,} 字，其中带 <image_caption> 的 {cap_chars:,} 字")
    print()
