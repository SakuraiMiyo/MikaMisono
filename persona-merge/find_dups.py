#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""find_dups.py —— 在人格提示词里找重复/近似重复的段落

为什么需要：
  这份 merged 稿是多次合并（原件 + CSP + 后续修订）叠出来的，
  同一件事往往在好几个 `##` 节里各说一遍。靠眼睛扫一定会漏。
  先量出来，再决定合并成哪一处。

判重口径：
  - 按空行切块（标题单独成块，并记录它所属的二级标题）
  - 归一化：去掉 markdown 标记、列表符号、编号、空白
  - 完全重复 → 一组
  - 近似重复（difflib 相似度 ≥ 阈值）→ 一组；短的优先并入长的

用法：<python> find_dups.py [文件] [--th 0.72] [--min 24]
"""
from __future__ import annotations

import argparse
import difflib
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).parent
DEFAULT = HERE / "qq-bot-personality.merged.md"

MD_RE = re.compile(r"[*`>#]|^\s*[-•]\s*|^\s*\d+[.、)]\s*", re.M)


def normalize(s: str) -> str:
    s = MD_RE.sub("", s)
    s = re.sub(r"\s+", "", s)
    return s


def blocks(text: str) -> list[dict]:
    out: list[dict] = []
    h2 = h1 = ""
    for i, raw in enumerate(text.split("\n"), 1):
        pass
    # 按行扫，记录标题上下文；按空行切块
    cur: list[str] = []
    start = 1
    h1 = h2 = ""

    def flush(end: int) -> None:
        nonlocal cur, start
        body = "\n".join(cur).strip()
        if body:
            out.append({"line": start, "end": end, "h1": h1, "h2": h2, "raw": body,
                        "norm": normalize(body)})
        cur = []

    for i, line in enumerate(text.split("\n"), 1):
        m = re.match(r"^(#{1,3})\s+(.*)$", line)
        if m:
            flush(i - 1)
            lvl, title = len(m.group(1)), m.group(2).strip()
            if lvl == 1:
                h1, h2 = title, ""
            elif lvl == 2:
                h2 = title
            else:
                h2 = h2 or title
            cur = [line]
            start = i
            continue
        if not line.strip():
            flush(i - 1)
            cur = []
            start = i + 1
            continue
        if not cur:
            start = i
        cur.append(line)
    flush(len(text.split("\n")))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", default=str(DEFAULT))
    ap.add_argument("--th", type=float, default=0.72, help="近似重复阈值")
    ap.add_argument("--min", type=int, default=24, help="最小归一化长度")
    a = ap.parse_args()

    p = pathlib.Path(a.file)
    bs = [b for b in blocks(p.read_text(encoding="utf-8")) if len(b["norm"]) >= a.min]
    print(f"{p.name}: {len(bs)} 个候选块（归一化 ≥{a.min} 字）\n")

    used = [False] * len(bs)
    groups: list[list[int]] = []

    # 1) 完全重复
    by_norm: dict[str, list[int]] = {}
    for i, b in enumerate(bs):
        by_norm.setdefault(b["norm"], []).append(i)
    for idxs in by_norm.values():
        if len(idxs) > 1:
            groups.append(idxs)
            for i in idxs:
                used[i] = True

    # 2) 近似重复（只在还没归组的之间找）
    rest = [i for i in range(len(bs)) if not used[i]]
    for ai in range(len(rest)):
        i = rest[ai]
        if used[i]:
            continue
        grp = [i]
        for bj in range(ai + 1, len(rest)):
            j = rest[bj]
            if used[j]:
                continue
            r = difflib.SequenceMatcher(None, bs[i]["norm"], bs[j]["norm"]).ratio()
            if r >= a.th:
                grp.append(j)
                used[j] = True
        if len(grp) > 1:
            used[i] = True
            groups.append(grp)

    groups.sort(key=lambda g: -len(g))
    total_saved = 0
    for g in groups:
        g.sort()
        lens = [len(bs[i]["norm"]) for i in g]
        total_saved += sum(sorted(lens)[:-1])
        print(f"── 重复组（{len(g)} 处） ──")
        for i in g:
            b = bs[i]
            print(f"   L{b['line']:<5} [{b['h2'][:26]}]  {b['raw'][:88].replace(chr(10),' / ')}")
        print()

    print(f"共 {len(groups)} 组重复；若每组只留最长的一份，可省约 {total_saved} 字")


if __name__ == "__main__":
    main()
