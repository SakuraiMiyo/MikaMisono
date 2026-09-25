#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""find_story_logical.py —— 在「物理名 ↔ 逻辑名」对照表里找剧情相关的逻辑名

`ba-bundle-name-map.json` 是 {物理文件名: 逻辑名}。
TableBundles / MediaPatch 的物理名是 `{xxh64(逻辑名)}_{crc32}`，
所以只要逻辑名里带 story / scenario / eden 之类的词，就能直接定位到物理文件。

用法：<python> find_story_logical.py [关键词...]
"""
from __future__ import annotations
import json
import pathlib
import sys
from collections import Counter

MAP = pathlib.Path(r"C:\OneDrive\MikaMisono\docs\archive\ba-bundle-name-map.json")
KW = sys.argv[1:] or ["scenario", "story", "eden", "kyrie", "dialog",
                      "chapter", "episode", "main", "script"]


def main() -> None:
    m = json.loads(MAP.read_text(encoding="utf-8"))
    print(f"对照表 {len(m)} 条\n")

    for kw in KW:
        hits = [(phys, log) for phys, log in m.items() if kw in log.lower()]
        print(f"── “{kw}” 命中 {len(hits)} 条 ──")
        for phys, log in hits[:25]:
            print(f"   {log:<52} {phys}")
        if len(hits) > 25:
            print(f"   … 还有 {len(hits) - 25} 条")
        print()

    # 逻辑名的扩展名分布，先看清都有什么种类的资源
    ext = Counter(pathlib.PurePosixPath(log).suffix.lower() for log in m.values())
    print("── 逻辑名扩展名分布 top25 ──")
    for k, v in ext.most_common(25):
        print(f"   {k or '(无)':<14} {v}")

    print("\n── 以 S 开头、像表名的逻辑名（前 60）──")
    cands = sorted({log for log in m.values()
                    if log.endswith((".db", ".zip", ".json", ".bytes"))})
    for c in cands[:60]:
        print(f"   {c}")
    print(f"   共 {len(cands)} 个表/数据文件")


if __name__ == "__main__":
    main()
