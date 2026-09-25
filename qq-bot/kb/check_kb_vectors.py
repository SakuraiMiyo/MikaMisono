#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_kb_vectors.py —— 确认每个知识库的向量都在（不是只上传了文档）

事故（2026-09-26）里 ollama 挂了，稠密检索全失败。要确认两件事：
  1. 文档上传时**向量真的算出来了**（不是空索引）
  2. 条数和 `mika_kb.py --status` 报的块数对得上

用 AstrBot 自己的 faiss 读索引文件，按 1024 维 float32 反推条数。
"""
from __future__ import annotations

import os
import pathlib
import sqlite3

KB_DIR = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "knowledge_base"
DB = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "data_v4.db"

DIM = 1024
BYTES_PER = DIM * 4  # float32

names: dict[str, str] = {}
try:
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    for row in c.execute("select id, name from kb"):
        names[row[0]] = row[1]
except Exception as exc:  # noqa: BLE001
    print(f"（读不到 kb 表：{exc}）")

try:
    import faiss  # type: ignore

    print("用 faiss 读：")
    for d in sorted(KB_DIR.iterdir()):
        f = d / "index.faiss"
        if not f.is_file():
            continue
        idx = faiss.read_index(str(f))
        print(f"  {names.get(d.name, d.name[:8]):<20} ntotal={idx.ntotal:<5} "
              f"dim={idx.d}  文件 {f.stat().st_size:,} B")
except ImportError:
    print("（没装 faiss，改用文件大小反推：1024 维 float32 = 4,096 B/条）")
    for d in sorted(KB_DIR.iterdir()):
        f = d / "index.faiss"
        if not f.is_file():
            continue
        n = f.stat().st_size / BYTES_PER
        print(f"  {names.get(d.name, d.name[:8]):<20} ≈ {n:8.2f} 条  "
              f"文件 {f.stat().st_size:,} B")
