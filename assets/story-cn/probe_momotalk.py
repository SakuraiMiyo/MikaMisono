#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_momotalk.py —— 找 MomoTalk（手机聊天）数据的取数路径

为什么要查：`agent/SKILL.md` 把 ☆ 写成「高频」「会连着甩」，但剧情台词里
☆ 只占 2.9%、♪ 只占 0.2%。怀疑那个风格来自 **MomoTalk**（手机聊天），
而 MomoTalk 不在当前语料里（只下了 main / favor / other）。
两个文档的「☆ 频率」矛盾，很可能是**register 不同**，不是谁写错了。

用法：<python> probe_momotalk.py
"""
from __future__ import annotations
import re

import httpx

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
HOST = "https://preview.blue-archive.io"
c = httpx.Client(headers=UA, timeout=40, follow_redirects=True)

js = c.get(f"{HOST}/assets/MomotalkContainer-CU6hJNVL.js").text
print(f"chunk {len(js)} bytes\n")

print("── 字符串里的路径 ──")
for m in sorted(set(re.findall(r"[\"'`](/[A-Za-z0-9_\-./{}$\[\]]{2,70})[\"'`]", js))):
    if any(k in m.lower() for k in ("story", "talk", "json", "api", "data")):
        print("  ", m)

print("\n── .get( ... ) 调用 ──")
for m in re.finditer(r"\.get\(([^)]{0,140})", js):
    print("   get:", m.group(1)[:130])

print("\n── 直接试探几条可能的 URL ──")
for p in ["/story/momotalk/index.json",
          "/story/momotalk/10059/index.json",
          "/story/momotalk/10059.json",
          "/momotalk/index.json",
          "/config/json/momotalk.json",
          "/story/ai/momotalk/10059/index.json"]:
    try:
        r = c.get(HOST + p)
        print(f"   {r.status_code}  {p}  {len(r.content)}")
    except Exception as e:
        print(f"   ERR {p} {type(e).__name__}")
