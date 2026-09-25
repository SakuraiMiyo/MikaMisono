#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""catalog_ba_archive.py —— 从 ba-archive 前端 bundle 抽出完整剧情目录

前端把整张目录表内联在 `playerUtils-*.js` 里。本脚本把它还原成 JSON：

    [{ "title_cn": "Vol.3 伊甸条约篇 第1章", "cover": "eden_treaty_chapter1",
       "sections": [ {"id":31010, "title_cn":"第一话;序章", "title_jp":"…",
                      "prev":0, "next":31020, "after_battle":false}, … ] }, … ]

节标题在前端里有时 `TextCn` 为空（只有日/韩文），此时回落到 `TextJp`；
两者都空的是「战斗后日谈」段，靠 `prev` 挂到上一节。

用法：<python> catalog_ba_archive.py
"""
from __future__ import annotations

import json
import pathlib
import re

import httpx

ROOT = pathlib.Path(r"C:\OneDrive\MikaMisono\assets\story-cn")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
HOST = "https://preview.blue-archive.io"

# 目录树：{released, title:{…}, avatar:"…", sections:[ {…}, … ]}
VOL = re.compile(
    r'\{released:(?:!0|!1),title:\{TextJp:"(?P<vjp>[^"]*)",TextCn:"(?P<vcn>[^"]*)"'
    r'.*?avatar:"/image/story_cover/(?P<cover>[A-Za-z0-9_\-]+)\.webp",'
    r'sections:\[(?P<body>.*?)\]\}(?=,\{released|\];function)',
    re.S)


def jsnum(s: str) -> int:
    return int(s.split("e")[0]) * 10 ** int(s.split("e")[1]) if "e" in s else int(s)


TITLE_OBJ = re.compile(r'title:\{([^{}]*)\}')
KEY = re.compile(r'(TextCn|TextJp|TextKr|TextEn|TextTw|TextTh):"([^"]*)"')


def pick_title(inner: str) -> tuple[str, str]:
    """前端里 title 对象的键顺序不固定 → 逐个键取，别用位置匹配。"""
    got = {k: v for k, v in KEY.findall(inner)}
    return got.get("TextCn", ""), got.get("TextJp", "")


def parse_section(blob: str) -> list[dict]:
    """从卷的 sections 原文里逐节抠出 id / 标题 / 前后链接。"""
    out: list[dict] = []
    titles = [(m.start(), *pick_title(m.group(1)))
              for m in TITLE_OBJ.finditer(blob)]
    for m in re.finditer(r"story_id:(\d+(?:e\d+)?)", blob):
        sid = jsnum(m.group(1))
        head = blob[:m.start()]
        tail = blob[m.start():m.start() + 300]
        t = None
        for tp in titles:
            if tp[0] < m.start():
                t = tp
            else:
                break
        prev = re.search(r"previous:(\d+)", tail)
        nxt = re.search(r"next:(\d+)", tail)
        out.append({
            "id": sid,
            "title_cn": t[1] if t else "",
            "title_jp": t[2] if t else "",
            "prev": jsnum(prev.group(1)) if prev else 0,
            "next": jsnum(nxt.group(1)) if nxt else 0,
            "after_battle": "is_after_battle:!0" in head[-260:],
        })
    return out


def main() -> None:
    c = httpx.Client(headers=UA, timeout=90, follow_redirects=True)
    html = c.get(HOST).text
    entry = re.search(r'src="(/assets/index-[A-Za-z0-9_\-]+\.js)"', html).group(1)
    idx = c.get(HOST + entry).text
    m = re.search(r"assets/(playerUtils-[A-Za-z0-9_\-]+\.js)", idx) or \
        re.search(r'"(\./playerUtils-[A-Za-z0-9_\-]+\.js)"', idx)
    js = c.get(f"{HOST}/assets/{m.group(1).lstrip('./')}").text
    print(f"playerUtils = {m.group(1)}  ({len(js)} bytes)")

    vols = []
    for vm in VOL.finditer(js):
        secs = parse_section(vm.group("body"))
        if not secs:
            continue
        vols.append({"cover": vm.group("cover"),
                     "title_cn": vm.group("vcn") or vm.group("vjp"),
                     "sections": secs})

    out = ROOT / "catalog-ba-archive.json"
    out.write_text(json.dumps(vols, ensure_ascii=False, indent=1), encoding="utf-8")
    n = sum(len(v["sections"]) for v in vols)
    print(f"✓ {len(vols)} 卷 / {n} 节 → {out.name}\n")
    for v in vols:
        print(f"[{v['cover']}] {v['title_cn']}  ({len(v['sections'])} 节)")
        for s in v["sections"]:
            ab = " (后日谈)" if s["after_battle"] else ""
            print(f"   {s['id']:>8}  {s['title_cn'] or s['title_jp']}{ab}")


if __name__ == "__main__":
    main()
