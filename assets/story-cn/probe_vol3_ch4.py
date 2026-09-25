#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_vol3_ch4.py —— 查 Vol.3 第四章到底存不存在（把 31xxx–39xxx 全扫一遍）

背景：之前的 `fetch_all.py` 用 `31000 <= i < 34000` 筛 Vol.3，
并且「完整性校验」是拿自己抽的目录去比自己的结果 —— 循环论证。
本脚本不依赖任何目录表，直接对 ID 空间做穷举。

用法：<python> probe_vol3_ch4.py
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import pathlib
import re

import httpx

ROOT = pathlib.Path(r"C:\OneDrive\MikaMisono\assets\story-cn")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
HOST = "https://preview.blue-archive.io"
MIKA = re.compile(r"^(?:\d+|#na);미카[^;]*;", re.M)


def probe(c: httpx.Client, sid: int):
    try:
        r = c.get(f"{HOST}/story/main/{sid}.json", timeout=40)
        if r.status_code != 200:
            return None
        j = r.json()
    except Exception:
        return None
    content = j.get("content") or []
    if not content:
        return None
    title = ""
    for u in content:
        t = (u.get("TextCn") or "").strip()
        if t and not t.startswith("["):
            title = t.replace("\n", " ")[:40]
            break
    mika = sum(1 for u in content if MIKA.search(u.get("ScriptKr") or ""))
    return {"id": sid, "title": title, "units": len(content), "mika": mika,
            "group": j.get("GroupId")}


def main() -> None:
    # 31xxx – 39xxx，步长 5（BA 的 story id 末位基本是 0/5）
    ids = [b + i for b in range(31000, 40000, 1000) for i in range(0, 1000, 5)]
    print(f"扫描 {len(ids)} 个候选 id（31xxx–39xxx，步长 5）…")
    hits: list[dict] = []
    with httpx.Client(headers=UA, timeout=40, follow_redirects=True) as c:
        with cf.ThreadPoolExecutor(8) as ex:
            for r in ex.map(lambda s: probe(c, s), ids):
                if r:
                    hits.append(r)

    hits.sort(key=lambda h: h["id"])
    print(f"\n可取 {len(hits)} 篇\n")
    by_ch: dict[int, list[dict]] = {}
    for h in hits:
        by_ch.setdefault(int(str(h["id"])[:2]), []).append(h)
    for ch in sorted(by_ch):
        hs = by_ch[ch]
        mk = sum(h["mika"] for h in hs)
        print(f"── {ch}xxx 共 {len(hs)} 篇，未花 {mk} 句 ──")
        for h in hs:
            flag = " ★" if h["mika"] else "  "
            print(f"{flag} {h['id']}  {h['mika']:>3}句  {h['title']}")

    (ROOT / "_vol3-scan.json").write_text(
        json.dumps(hits, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ _vol3-scan.json")


if __name__ == "__main__":
    main()
