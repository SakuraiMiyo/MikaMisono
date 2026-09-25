#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""find_story_bundles.py —— 从 Unity Addressables 目录里找出「剧情脚本」的 bundle

`catalog_Remote.json` 的 `m_InternalIds` 里每条都是
`{Path}\\<逻辑名>-<日期>_assets_all_<crc>.bundle`，**逻辑名是明文**，
所以可以直接按关键词捞，不用去猜 xxh64。

用法：<python> find_story_bundles.py [关键词...]
"""
from __future__ import annotations
import json
import pathlib
import re
import sys
from collections import Counter

GAME = pathlib.Path(r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP"
                    r"\BlueArchive_Data\StreamingAssets")
CAT = GAME / "catalog_Remote.json"

KW = sys.argv[1:] or ["scenario", "story", "eden", "treaty", "kyrie",
                      "mainstory", "dialog", "script"]


def main() -> None:
    j = json.loads(CAT.read_text(encoding="utf-8"))
    ids = j["m_InternalIds"]
    print(f"catalog 内 bundle 路径 {len(ids)} 条\n")

    # 逻辑名：取最后一段、去掉前缀路径，抽出一个「像名字」的片段
    names = []
    for p in ids:
        last = re.split(r"[\\/]", p)[-1]
        last = re.sub(r"\.bundle$", "", last)
        names.append((last, p))

    for kw in KW:
        hits = [(n, p) for n, p in names if kw in n.lower()]
        print(f"── “{kw}” 命中 {len(hits)} 条 ──")
        for n, p in hits[:40]:
            print(f"   {n}")
        if len(hits) > 40:
            print(f"   … 还有 {len(hits) - 40} 条")
        print()

    # 名字的「词前缀」分布，方便找规律
    pref = Counter(re.split(r"[-_]", n)[0] for n, _ in names)
    print("── 逻辑名首段 top40 ──")
    for k, v in pref.most_common(40):
        print(f"   {k:<42} {v}")

    # 把所有含 scenario/story 的名字存下来供后续用
    out = pathlib.Path(__file__).parent / "_story-bundle-names.json"
    keep = sorted({n for n, _ in names
                   if any(k in n.lower() for k in
                          ("scenario", "story", "eden", "treaty", "kyrie"))})
    out.write_text(json.dumps(keep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ {out.name}（{len(keep)} 条）")


if __name__ == "__main__":
    main()
