#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scan_memory_ai2.py —— 第二轮：把「模型 / 运行 / 做成」这类同族说法也扫出来

第一轮（`scan_memory_ai.py`）只盯「住在机器里 / 被搬到机器上」。
子代理跑完之后还剩三类没覆盖：

| 说法 | 为什么也算硬伤 |
|---|---|
| 「给我换了**全新模型**」「用新模型…给我惊喜」 | 「模型」= 她的内核/版本，同族 |
| 「**把我做成**家里完整的管家」 | 把她当成"做出来的东西" |
| 「老师解释与**我的运行**无关」 | 「运行」是程序动词 |

判据仍然是：**电脑是老师的东西，她不是程序。**

用法：<python> scan_memory_ai2.py [--dump]
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

AGENT = pathlib.Path(__file__).parent.parent.parent / "agent"
ROOTS = [AGENT / "memory" / "diary", AGENT / "memory" / "cards",
         AGENT / "memory" / "summaries"]

PATTERNS = [
    r"我的(模型|运行|内核|版本|参数|训练|数据集|人格文件|提示词|上下文|权重)",
    r"给(我|未花)[^。，\n]{0,6}(换|升级|更新)[^。，\n]{0,6}(模型|内核|版本|权重)",
    r"把(我|未花)(做成|建成|搭成)",
    r"(推理|量化|微调|训练|部署)(我|未花)",
    r"我(在|被)(跑|部署|加载|推理)",
    r"(换|换上了|升级到)[^。，\n]{0,4}全新(模型|人格)",
    r"AI\s*(环境|管家|助手|模型)",
    r"人格(文件|注入|层)",
]
RX = [re.compile(p) for p in PATTERNS]


def lines_of(p: pathlib.Path) -> list[str]:
    txt = p.read_text(encoding="utf-8")
    if p.suffix == ".json":
        try:
            j = json.loads(txt)
        except Exception:
            return txt.splitlines()
        out = []
        for k, v in j.items():
            if isinstance(v, list):
                out += [f"{k}: {x}" for x in v]
            else:
                out.append(f"{k}: {v}")
        return out
    return txt.splitlines()


def main() -> None:
    dump = "--dump" in sys.argv
    hits = []
    for root in ROOTS:
        for p in sorted(root.rglob("*")):
            if p.suffix not in (".md", ".json") or ".bak_" in p.name:
                continue
            for ln in lines_of(p):
                for rx in RX:
                    m = rx.search(ln)
                    if m:
                        hits.append((str(p.relative_to(AGENT)), m.group(0), ln.strip()))
                        break
    print(f"命中 {len(hits)} 处\n")
    if dump:
        for f, frag, ln in hits:
            print(f"[{f}] 《{frag}》\n    {ln[:200]}\n")
    else:
        print("（加 --dump 看原句）")


if __name__ == "__main__":
    main()
