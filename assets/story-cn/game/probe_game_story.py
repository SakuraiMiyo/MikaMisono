#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_game_story.py —— 打开 ExcelDB.db 与 JP_CH*.zip，看剧情数据到底在哪

背景：TableBundles 的全部 6440 个逻辑名里，只有 `Excel.zip`（74 张表，野外/小游戏）
和 `ExcelDB.db` 两个像表；主线剧情表不在 `Excel.zip` 里。
MediaPatch 里有 189 个 `JP_CH####.zip`。

用法：<python> probe_game_story.py
"""
from __future__ import annotations
import base64
import json
import pathlib
import sqlite3
import sys
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "blue-archive"))
from lib.MersenneTwister import MersenneTwister        # noqa: E402
from lib.XXHashService import CalculateHash            # noqa: E402

GAME = pathlib.Path(r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP"
                    r"\BlueArchive_Data\StreamingAssets")
NAME_MAP = pathlib.Path(r"C:\OneDrive\MikaMisono\docs\archive\ba-bundle-name-map.json")
m = json.loads(NAME_MAP.read_text(encoding="utf-8"))
LOG2PHYS = {log: phys for phys, log in m.items()}


def pwd_for(phys: str) -> bytes:
    return base64.b64encode(MersenneTwister(CalculateHash(phys)).NextBytes(15))


def probe_exceldb() -> None:
    phys = LOG2PHYS.get("ExcelDB.db")
    p = GAME / "TableBundles" / phys
    print(f"══ ExcelDB.db → {phys}  ({p.stat().st_size/1024/1024:.1f} MB) ══")
    head = p.open("rb").read(64)
    print("  头部字节:", head[:32])
    print("  是 SQLite:", head[:15] == b"SQLite format 3")

    # 先试 SQLite
    try:
        con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
        tabs = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print(f"  SQLite 表 {len(tabs)} 张")
        for t in tabs[:60]:
            print("   ", t)
        con.close()
        return
    except Exception as e:
        print("  SQLite 打开失败:", type(e).__name__, e)

    # 不是 SQLite → 试解密后看
    data = p.read_bytes()
    print("  前 200 字节 ascii:", data[:200])


def probe_jp_ch(n: int = 6) -> None:
    names = sorted(l for l in LOG2PHYS if l.startswith("JP_CH"))
    print(f"\n══ JP_CH*.zip 共 {len(names)} 个，先看 {n} 个 ══")
    for log in names[:n]:
        phys = LOG2PHYS[log]
        p = GAME / "MediaPatch" / phys
        print(f"\n-- {log}  ({p.stat().st_size/1024/1024:.2f} MB)")
        try:
            with zipfile.ZipFile(p) as z:
                entries = z.namelist()
                print(f"   条目 {len(entries)} 个")
                for e in entries[:12]:
                    print("     ", e)
                if len(entries) > 12:
                    print(f"      … 还有 {len(entries)-12} 个")
        except Exception as e:
            print("   ✗", type(e).__name__, e)


if __name__ == "__main__":
    probe_exceldb()
    probe_jp_ch()
