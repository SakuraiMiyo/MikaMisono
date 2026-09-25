#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_all.py —— 把「未花相关原始剧情」完整下到 raw/（可重复运行，幂等）

## 产出结构

    raw/
      Vol.3/           Vol.3 伊甸条约篇 全 77 节（31010 … 33250）
      原版羁绊/         100592 / 100593 / 100595 / 100596
      泳装羁绊/         101222 / 101223 / 101225 / 101226 / 101228 / 101229
      其他/            任务剧情（含 210「海边的袭击者」夏活前置）

## 用法

    <python> fetch_all.py            # 缺什么补什么
    <python> fetch_all.py --all-other # 顺带把全部任务剧情也下下来
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import pathlib
import re
import sys

import httpx

ROOT = pathlib.Path(r"C:\OneDrive\MikaMisono\assets\story-cn")
RAW = ROOT / "raw"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
HOST = "https://preview.blue-archive.io"

FAVOR_MIKA = {
    "100592": "原版第1话_重归平稳的日常",
    "100593": "原版第2话_义务劳动",
    "100595": "原版第3话_阁楼里的公主殿下",
    "100596": "原版第4话_伤痕",
}
FAVOR_MIKA_SWIM = {
    "101222": "泳装第1话_连自己都不了解的自己",
    "101223": "泳装第2话_课程的后续",
    "101225": "泳装第3话_海滩上发光的东西",
    "101226": "泳装第4话_从蹒跚学步的我开始",
    "101228": "泳装第5话_致某时某刻的自己",
    "101229": "泳装第6话_已经没关系了",
}


def jsnum(s: str) -> int:
    return int(s.split("e")[0]) * 10 ** int(s.split("e")[1]) if "e" in s else int(s)


def vol3_ids(c: httpx.Client) -> list[int]:
    """从官方目录里取 Vol.3 全部 story_id（比手写区间可靠）"""
    html = c.get(HOST).text
    entry = re.search(r'src="(/assets/index-[A-Za-z0-9_\-]+\.js)"', html).group(1)
    idx = c.get(HOST + entry).text
    m = re.search(r"assets/(playerUtils-[A-Za-z0-9_\-]+\.js)", idx) or \
        re.search(r'"(\./playerUtils-[A-Za-z0-9_\-]+\.js)"', idx)
    js = c.get(f"{HOST}/assets/{m.group(1).lstrip('./')}").text
    ids = {jsnum(x) for x in re.findall(r"story_id:(\d+(?:e\d+)?)", js)}
    # ⚠️ 这里**不要**再写 `31000 <= i < 34000` 这种硬编码区间。
    # 之前就是那么写的：把 Vol.3 的边界当成了「31xxx–33xxx」，
    # 而实际上 Vol.3 有**四章**（第四位是章号，Ch4 会是 34xxx），
    # 那个条件会把第四章整个排除在外。现在改成「取目录里所有 3xxxx 的节」，
    # 并且把**各章各收了多少节**打出来，让缺失一眼可见。
    return sorted(i for i in ids if 30000 <= i < 40000)


def report_coverage(ids: list[int]) -> None:
    """按章号统计，暴露「某章一节都没收到」的情况。"""
    from collections import Counter
    by_ch = Counter(str(i)[1] for i in ids)      # 第二位 = 章号
    print(f"   按章统计（共 {len(ids)} 节）：")
    for ch in sorted(by_ch):
        print(f"     第{ch}章  {by_ch[ch]:>3} 节")
    if "4" not in by_ch:
        print("   ⚠️ 第4章 0 节 —— 要么源站没有，要么 ID 规则不是 3x0xx。"
              "**不要**因为这里没报错就认为已经收全。")


def fetch(c: httpx.Client, url: str) -> dict | None:
    try:
        r = c.get(url, timeout=45)
        if r.status_code != 200:
            return None
        j = r.json()
        return j if isinstance(j, dict) and "content" in j else None
    except Exception as e:
        print("   ✗", url, type(e).__name__)
        return None


def save(j: dict, sub: str, name: str) -> int:
    d = RAW / sub
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{name}.json"
    p.write_text(json.dumps(j, ensure_ascii=False, indent=1), encoding="utf-8")
    return p.stat().st_size


def main() -> None:
    want_other = "--all-other" in sys.argv
    with httpx.Client(headers=UA, timeout=45, follow_redirects=True) as c:
        v3 = vol3_ids(c)
        print(f"① Vol.3 目录：{len(v3)} 节  {v3[0]} … {v3[-1]}")
        report_coverage(v3)

        tasks: list[tuple[str, str, str]] = []      # (url, 子目录, 文件名)
        for sid in v3:
            tasks.append((f"{HOST}/story/main/{sid}.json", "Vol.3", str(sid)))
        for sid, name in FAVOR_MIKA.items():
            tasks.append((f"{HOST}/story/favor/{sid[:5]}/{sid}.json", "原版羁绊",
                          f"{sid}_{name}"))
        for sid, name in FAVOR_MIKA_SWIM.items():
            tasks.append((f"{HOST}/story/favor/{sid[:5]}/{sid}.json", "泳装羁绊",
                          f"{sid}_{name}"))
        if want_other:
            for sid in list(range(100, 1000)):
                tasks.append((f"{HOST}/story/other/{sid}.json", "其他", str(sid)))

        print(f"② 下载 {len(tasks)} 篇 …")

        def work(t):
            url, sub, name = t
            j = fetch(c, url)
            if not j:
                return sub, name, 0
            return sub, name, save(j, sub, name)

        ok = miss = 0
        with cf.ThreadPoolExecutor(8) as ex:
            for sub, name, size in ex.map(work, tasks):
                if size:
                    ok += 1
                else:
                    miss += 1
                    if not want_other:
                        print(f"   △ 取不到 {sub}/{name}")
        print(f"\n✓ 成功 {ok} 篇，失败 {miss} 篇")

    print("\n③ 汇总 raw/")
    for d in sorted(RAW.iterdir()):
        if d.is_dir():
            fs = list(d.glob("*.json"))
            print(f"   {d.name:<12} {len(fs):>3} 篇  "
                  f"{sum(f.stat().st_size for f in fs)/1024/1024:>7.2f} MB")


if __name__ == "__main__":
    main()
