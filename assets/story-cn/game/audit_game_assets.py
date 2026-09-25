#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_game_assets.py —— 摸清本机客户端到底有什么（哪些包已下载、故事数据在哪）

`catalog_Remote.json` 记录了 173,774 个 bundle，但磁盘上只有 3 万多个 —— 说明
客户端是按需下载的，很多包本地还没有。先把「已下载」和「目录里有但没下」分清楚。

用法：<python> audit_game_assets.py
"""
from __future__ import annotations
import json
import pathlib
import re
import sys
import zipfile
from collections import Counter

GAME = pathlib.Path(r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP"
                    r"\BlueArchive_Data\StreamingAssets")
NAME_MAP = pathlib.Path(r"C:\OneDrive\MikaMisono\docs\archive\ba-bundle-name-map.json")


def prefixes(names, n=40):
    c = Counter(re.split(r"[_\-.]", x)[0] for x in names)
    return c.most_common(n)


def main() -> None:
    m = json.loads(NAME_MAP.read_text(encoding="utf-8"))
    print(f"name map {len(m)} 条（= 本机已下载的 TableBundles + MediaPatch）\n")

    mp = {p.name for p in (GAME / "MediaPatch").iterdir() if p.is_file()}
    tb = {p.name for p in (GAME / "TableBundles").iterdir() if p.is_file()}
    mplogs = [log for phys, log in m.items() if phys in mp]
    tblogs = [log for phys, log in m.items() if phys in tb]

    print("── MediaPatch 逻辑名前缀 top30 ──")
    for k, v in prefixes(mplogs):
        print(f"   {k:<34} {v}")

    print("\n── TableBundles 逻辑名前缀 top30 ──")
    for k, v in prefixes(tblogs):
        print(f"   {k:<34} {v}")

    # 目录里登记了多少 bundle
    cat = json.loads((GAME / "catalog_Remote.json").read_text(encoding="utf-8"))
    ids = cat["m_InternalIds"]
    print(f"\n── catalog_Remote.json 登记 {len(ids)} 个 bundle ──")
    keyed = Counter()
    for p in ids:
        last = re.split(r"[\\/]", p)[-1]
        keyed[re.split(r"[-_]", last)[0]] += 1
    for k, v in keyed.most_common(30):
        print(f"   {k:<40} {v}")

    # 已下载的 AssetBundles
    ab = [p.name for p in (GAME / "AssetBundles").iterdir() if p.is_file()]
    print(f"\n── AssetBundles 已下载 {len(ab)} 个，前缀 top20 ──")
    for k, v in prefixes(ab, 20):
        print(f"   {k:<40} {v}")

    # 含关键词的、目录里登记的 bundle
    print("\n── catalog 里名字含 story/scenario 的 bundle ──")
    for p in ids:
        last = re.split(r"[\\/]", p)[-1]
        if re.search(r"(scenario|_story|story_)", last, re.I) and last.endswith(".bundle"):
            print("   ", last)


if __name__ == "__main__":
    main()
