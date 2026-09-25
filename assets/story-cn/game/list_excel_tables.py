#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""list_excel_tables.py —— 列出游戏 Excel.zip 里**全部**表名

之前的结论「`ScenarioScriptMain*`／`LocalizeScenarioExcel` 在本 build 里不存在」
是在只看了几张表的情况下下的，不可靠。这个脚本把 Excel.zip 完整列一遍，用事实说话。

密码规则（`lib/TableService.py`）：`base64(MT(xxh32(物理文件名)).NextBytes(15))`

用法：<python> list_excel_tables.py [关键词...]
"""
from __future__ import annotations
import base64
import json
import pathlib
import re
import sys
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "blue-archive"))
from lib.MersenneTwister import MersenneTwister            # noqa: E402
from lib.XXHashService import CalculateHash                # noqa: E402

GAME = pathlib.Path(r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP"
                    r"\BlueArchive_Data\StreamingAssets")
NAME_MAP = pathlib.Path(r"C:\OneDrive\MikaMisono\docs\archive\ba-bundle-name-map.json")

KW = sys.argv[1:] or ["scenario", "story", "localize", "dialog", "main", "script", "kyrie"]


def main() -> None:
    m = json.loads(NAME_MAP.read_text(encoding="utf-8"))
    phys = {log: p for p, log in m.items()}
    if "Excel.zip" not in phys:
        print("对照表里没有 Excel.zip"); return
    path = GAME / "TableBundles" / phys["Excel.zip"]
    print(f"Excel.zip 物理文件: {path.name}  ({path.stat().st_size/1024/1024:.1f} MB)")

    pwd = base64.b64encode(MersenneTwister(CalculateHash(path.name)).NextBytes(15))
    print(f"口令: {pwd.decode()}\n")

    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        print(f"Excel.zip 内共 {len(names)} 个条目\n")
        for kw in KW:
            hits = [n for n in names if kw in n.lower()]
            print(f"── “{kw}” 命中 {len(hits)} 条 ──")
            for h in hits[:40]:
                print(f"   {h}")
            if len(hits) > 40:
                print(f"   … 还有 {len(hits)-40} 条")
            print()
        out = pathlib.Path(__file__).parent / "_excel-entries.txt"
        out.write_text("\n".join(sorted(names)), encoding="utf-8")
        print(f"→ 全部条目名写入 {out.name}")


if __name__ == "__main__":
    main()
