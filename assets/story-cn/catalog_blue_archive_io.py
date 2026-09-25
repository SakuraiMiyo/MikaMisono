#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""catalog_blue_archive_io.py —— 从**正式站**抽完整剧情目录，看有没有第四章

preview 和正式站是同一套站点、但构建号不同，之前只抽了 preview 的目录。
本脚本按「找不到 playerUtils 就在所有 chunk 里搜 story_id」的方式硬抽，
不依赖具体文件名。

用法：<python> catalog_blue_archive_io.py
"""
from __future__ import annotations
import json
import pathlib
import re
import concurrent.futures as cf

import httpx

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
HOST = "https://blue-archive.io"
OUT = pathlib.Path(__file__).parent

c = httpx.Client(headers=UA, timeout=60, follow_redirects=True)


def jsnum(s: str) -> int:
    return int(s.split("e")[0]) * 10 ** int(s.split("e")[1]) if "e" in s else int(s)


def main() -> None:
    html = c.get(HOST).text
    entry = re.search(r'src="(/assets/index-[A-Za-z0-9_\-]+\.js)"', html).group(1)
    idx = c.get(HOST + entry).text
    chunks = sorted(set(re.findall(r"assets/([A-Za-z0-9_\-]+\-[A-Za-z0-9_\-]{8}\.js)", idx))
                    | set(re.findall(r'"\./([A-Za-z0-9_\-]+\-[A-Za-z0-9_\-]{8}\.js)"', idx)))
    print(f"entry={entry}  懒加载 chunk {len(chunks)} 个")

    found: dict[str, list[int]] = {}

    def scan(name: str):
        try:
            js = c.get(f"{HOST}/assets/{name}").text
        except Exception:
            return None
        ids = sorted({jsnum(x) for x in re.findall(r"story_id:(\d+(?:e\d+)?)", js)})
        return (name, ids, js) if ids else None

    with cf.ThreadPoolExecutor(8) as ex:
        for r in ex.map(scan, chunks):
            if r:
                found[r[0]] = r[1]
                print(f"  {r[0]:<46} story_id {len(r[1])} 个  "
                      f"max={max(r[1])}  含34xxx={[i for i in r[1] if i >= 34000]}")
                if len(r[1]) > 50:
                    (OUT / f"_catalog-{r[0]}").write_text(r[2], encoding="utf-8")

    allids = sorted({i for v in found.values() for i in v})
    print(f"\n全站 story_id 合计 {len(allids)} 个")
    print(f"  31000-34999 段: {[i for i in allids if 31000 <= i < 35000]}")
    print(f"  最大: {max(allids) if allids else '-'}")
    (OUT / "_blue-archive-io-ids.json").write_text(
        json.dumps(allids), encoding="utf-8")


if __name__ == "__main__":
    main()
