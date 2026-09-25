#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""list_device_lines.py —— 列出「机器/电脑/设备」和「她本人」出现在同一句里的行

`scan_memory_ai.py` 只抓最露骨的写法（住在机器里、被搬进平板）。
但真正的传染源更宽：凡是**把"机器"和"她"绑在一起**的句子，
模型读了都会得出「她住在机器上」这个结论。

例：
    老师给我换了台新机器，我反应更快了        ← 换了的是"她"，不是电脑
    机器换了，住的地方也换了，可我还是那个未花  ← 机器=她的载体
    不管家里换成哪台机器，冷冰冰的都不是未花    ← 尚可，但"家里换机器"仍像换她

判据（2026-09-24 收紧版）：
    ✅ 电脑是**老师用的东西 / 家里的电器 / 她干活的工具**
    ❌ 电脑不是**她的住处 / 她的身体 / 她被搬来搬去的对象**

用法：<python> list_device_lines.py [--write 输出文件]
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

AGENT = pathlib.Path(__file__).parent.parent.parent / "agent"
ROOTS = [AGENT / "memory" / "diary", AGENT / "memory" / "cards",
         AGENT / "memory" / "summaries"]

DEVICE = re.compile(r"机器|电脑|服务器|NAS|nas|平板|设备|主机|台式|笔记本|显卡|显存")
SELF = re.compile(r"我|未花|自己|身上")


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
    hits: list[tuple[str, str]] = []
    for root in ROOTS:
        for p in sorted(root.rglob("*")):
            if p.suffix not in (".md", ".json") or p.name.endswith(".bak_20260918"):
                continue
            for ln in lines_of(p):
                if DEVICE.search(ln) and SELF.search(ln) and len(ln.strip()) > 8:
                    hits.append((str(p.relative_to(AGENT)), ln.strip()))

    print(f"命中 {len(hits)} 行\n")
    for f, ln in hits:
        print(f"[{f}]\n    {ln[:220]}\n")

    if "--write" in sys.argv:
        i = sys.argv.index("--write")
        out = pathlib.Path(sys.argv[i + 1])
        out.write_text("\n".join(f"[{f}] {ln}" for f, ln in hits), encoding="utf-8")
        print(f"→ 写入 {out}")


if __name__ == "__main__":
    main()
