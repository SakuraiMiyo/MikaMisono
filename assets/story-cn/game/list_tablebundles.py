#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""list_tablebundles.py —— 列出 TableBundles 目录里每个物理文件对应的逻辑名

`ba-bundle-name-map.json` 覆盖 TableBundles(6440) + MediaPatch(4261) = 10701 条。
按目录把逻辑名归一下组，就能看出「剧情表」在哪几个 zip 里。

用法：<python> list_tablebundles.py
"""
from __future__ import annotations
import json
import pathlib
import re
from collections import Counter

GAME = pathlib.Path(r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP"
                    r"\BlueArchive_Data\StreamingAssets")
NAME_MAP = pathlib.Path(r"C:\OneDrive\MikaMisono\docs\archive\ba-bundle-name-map.json")


def main() -> None:
    m = json.loads(NAME_MAP.read_text(encoding="utf-8"))
    # 物理名没有扩展名，形如 `16300795542385574620_4128271700`，
    # 所以直接拿整名比对，不能取 stem。
    tb = {p.name for p in (GAME / "TableBundles").iterdir() if p.is_file()}
    mp = {p.name for p in (GAME / "MediaPatch").iterdir() if p.is_file()}
    print(f"磁盘 TableBundles {len(tb)} 个 / MediaPatch {len(mp)} 个\n")

    groups = {"TableBundles": [], "MediaPatch": [], "其它": []}
    for phys, log in m.items():
        key = "TableBundles" if phys in tb else \
              "MediaPatch" if phys in mp else "其它"
        groups[key].append(log)

    for k, v in groups.items():
        print(f"── {k}: {len(v)} 个逻辑名 ──")
        if k == "TableBundles":
            for log in sorted(v):
                print(f"   {log}")
        else:
            # 只打形状
            shape = Counter(re.sub(r"\d+", "#", log) for log in v)
            for s, c in shape.most_common(15):
                print(f"   {s:<60} {c}")
        print()


if __name__ == "__main__":
    main()
