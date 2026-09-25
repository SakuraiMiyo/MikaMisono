#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_sources_ch4.py —— 四处找 Vol.3 第四章的原文

已知：
  · 第四章「忘れられた神々のためのキリエ」前/中/後編，2022-05-25 / 06-08 / 08-09 配信
  · preview.blue-archive.io 只放了序章 + Vol.3 前三章（连 Vol.1/2/4/5 都没有）→ 残缺镜像
本脚本去试正式站与其它镜像。

用法：<python> probe_sources_ch4.py
"""
from __future__ import annotations
import json

import httpx

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}

# 第四章的 story_id 推测：Vol.3 = 3x，Chapter 4 → 34010 起
CANDIDATES = ["34010", "34020", "34030", "34060", "34100", "34200",
              "33300", "33260", "33270", "33330"]

HOSTS = [
    "https://blue-archive.io",
    "https://preview.blue-archive.io",
    "https://www.blue-archive.io",
]

TEMPLATES = [
    "/story/main/{sid}.json",
    "/data/story/main/{sid}.json",
    "/api/story/main/{sid}.json",
]

c = httpx.Client(headers=UA, timeout=30, follow_redirects=True)

print("══ 1. 各站点根路径可用性 ══")
for h in HOSTS:
    try:
        r = c.get(h)
        print(f"  {h:<36} {r.status_code}  {len(r.content)}  bytes")
    except Exception as e:
        print(f"  {h:<36} ERR {type(e).__name__}: {e}")

print("\n══ 2. 目录页探测（列出全部章节的接口）══")
for h in HOSTS:
    for path in ["/story/main/index.json", "/config/json/mainstory.json",
                 "/config/json/story.json"]:
        try:
            r = c.get(h + path)
            mark = "✓" if r.status_code == 200 else " "
            print(f" {mark} {h}{path}  {r.status_code}  {len(r.content)}")
        except Exception as e:
            print(f"   {h}{path}  ERR {type(e).__name__}")

print("\n══ 3. 直接试第四章 story_id ══")
for h in HOSTS:
    for tpl in TEMPLATES:
        for sid in CANDIDATES[:4]:
            try:
                r = c.get(h + tpl.format(sid=sid))
                if r.status_code == 200 and len(r.content) > 2000:
                    print(f"  ✓ {h}{tpl.format(sid=sid)}  {len(r.content)}")
            except Exception:
                pass

print("\n══ 4. 正式站的前端 bundle 里的目录（看有没有第四章）══")
try:
    r = c.get("https://blue-archive.io")
    html = r.text
    import re
    entry = re.search(r'src="(/assets/index-[A-Za-z0-9_\-]+\.js)"', html)
    print("  entry:", entry.group(1) if entry else "未找到")
    if entry:
        idx = c.get("https://blue-archive.io" + entry.group(1)).text
        m = re.search(r"assets/(playerUtils-[A-Za-z0-9_\-]+\.js)", idx)
        print("  playerUtils:", m.group(1) if m else "未找到")
        if m:
            pj = c.get("https://blue-archive.io/assets/" + m.group(1)).text
            ids = sorted({int(x.split("e")[0]) * 10 ** int(x.split("e")[1])
                          if "e" in x else int(x)
                          for x in re.findall(r"story_id:(\d+(?:e\d+)?)", pj)})
            print(f"  正式站目录 story_id 共 {len(ids)} 个")
            print(f"  34000 以上: {[i for i in ids if i >= 34000]}")
            print(f"  Vol.3 段(31xxx-34xxx): {[i for i in ids if 31000 <= i < 35000]}")
            print(f"  最大 id: {max(ids) if ids else '-'}")
except Exception as e:
    print("  ERR", type(e).__name__, e)
