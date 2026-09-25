#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_exceldb.py —— 弄清 ExcelDB.db（202 MB）是什么容器

它不是 SQLite，开头也不是 ZIP 签名。逐条试常见的几种可能：
  · 其实是 ZIP（ZIP 的 EOCD 在文件尾部，开头可以有任意前缀）
  · 是加密 ZIP
  · 前面挂了 header，真实 ZIP 从某个偏移开始
  · 是 BA 自己的 XOR/AES 容器

用法：<python> probe_exceldb.py
"""
from __future__ import annotations
import base64
import io
import json
import pathlib
import sys
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "blue-archive"))
from lib.MersenneTwister import MersenneTwister         # noqa: E402
from lib.XXHashService import CalculateHash             # noqa: E402

GAME = pathlib.Path(r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP"
                    r"\BlueArchive_Data\StreamingAssets")
NAME_MAP = pathlib.Path(r"C:\OneDrive\MikaMisono\docs\archive\ba-bundle-name-map.json")
m = json.loads(NAME_MAP.read_text(encoding="utf-8"))
LOG2PHYS = {log: phys for phys, log in m.items()}

phys = LOG2PHYS["ExcelDB.db"]
p = GAME / "TableBundles" / phys
size = p.stat().st_size
print(f"文件: {p.name}  {size/1024/1024:.1f} MB")

with p.open("rb") as f:
    head = f.read(1 << 20)          # 前 1 MB
    f.seek(-(1 << 16), 2)
    tail = f.read()

print("\n① 前 16 字节:", head[:16].hex(" "))
print("② 目录尾 64 KB 里找 ZIP EOCD (PK\\x05\\x06):", tail.find(b"PK\x05\x06"))
print("③ 前 1 MB 里找 ZIP 本地头 (PK\\x03\\x04):", head.find(b"PK\x03\x04"))
print("④ 前 1 MB 里找 ZIP 中央目录 (PK\\x01\\x02):", head.find(b"PK\x01\x02"))

# 全文件扫 ZIP 本地头（只扫前 8 MB，够判断了）
with p.open("rb") as f:
    chunk = f.read(8 << 20)
hits = []
i = chunk.find(b"PK\x03\x04")
while i != -1 and len(hits) < 5:
    hits.append(i)
    i = chunk.find(b"PK\x03\x04", i + 1)
print("⑤ 前 8 MB 里 PK\\x03\\x04 偏移:", hits)

print("\n⑥ 直接当 ZIP 打开（用物理名算口令）:")
pwd = base64.b64encode(MersenneTwister(CalculateHash(phys)).NextBytes(15))
try:
    with zipfile.ZipFile(p) as z:
        names = z.namelist()
        print(f"   ✓ 成功！{len(names)} 个条目")
        for n in names[:60]:
            print("     ", n)
except Exception as e:
    print("   ✗", type(e).__name__, e)

print("\n⑦ 试 Excel.zip 的口令（有些容器共用口令）:")
for cand, label in [
    (base64.b64encode(MersenneTwister(CalculateHash("Excel.zip")).NextBytes(15)), "Excel.zip"),
    (base64.b64encode(MersenneTwister(CalculateHash("ExcelDB.db")).NextBytes(15)), "ExcelDB.db"),
]:
    try:
        with zipfile.ZipFile(p) as z:
            z.read(z.namelist()[0], pwd=cand)
            print(f"   ✓ {label} 口令可用")
    except Exception as e:
        print(f"   ✗ {label}: {type(e).__name__}")

print("\n⑧ 排除 ZIP 后：看看是不是 BA 的加密容器（找特征字符串）")
for pat in (b"Excel", b"Scenario", b"ScenarioScript", b"Table", b"MemoryPack"):
    print(f"   前 4 MB 里 {pat!r}: {chunk[:4 << 20].find(pat)}")
