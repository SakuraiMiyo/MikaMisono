#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""enum_tools.py —— 列出这台机器上 AstrBot 实际注册了哪些 LLM 工具

用来给「人格工具白名单」打草稿：她其实只需要
**知识库查询 / 出图 / 说说 / 点餐 / 日记 / QQ 操作**这几样，
不该有 shell、文件读写、grep。

工具来自两处：
  · AstrBot 内置：`backend/app/astrbot/core/tools/**`、`builtin_stars/**`
  · 插件：`~/.astrbot/data/plugins/**`
"""
from __future__ import annotations

import os
import pathlib
import re

APP = pathlib.Path(r"C:\SoftWare\Astrbot\backend\app\astrbot")
PLUGINS = pathlib.Path(os.path.expanduser("~")) / ".astrbot" / "data" / "plugins"

# AstrBot 里工具声明的几种写法
PATS = [
    ("filter.llm_tool(name=)", re.compile(r'@filter\.llm_tool\(\s*name\s*=\s*["\']([\w.\-]+)')),
    ("filter.llm_tool(\"..\")", re.compile(r'@filter\.llm_tool\(\s*["\']([\w.\-]+)')),
    ("llm_tool(name=)", re.compile(r'@llm_tool\(\s*name\s*=\s*["\']([\w.\-]+)')),
    ("register_llm_tool", re.compile(r'register_llm_tool\(\s*(?:name\s*=\s*)?["\']([\w.\-]+)')),
    ("func_tool.call", re.compile(r'@llm_tool\b\s*\n\s*(?:async\s+)?def\s+(\w+)')),
    ("class XxxTool", re.compile(r'class\s+(\w*Tool)\s*[\(:]')),
]


def scan(root: pathlib.Path) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    if not root.exists():
        return out
    for p in root.rglob("*.py"):
        if "node_modules" in str(p):
            continue
        t = p.read_text(encoding="utf-8", errors="ignore")
        for label, rx in PATS:
            for m in rx.findall(t):
                out.setdefault(label, set()).add(m)
    return out


for label, root in (("内置", APP), ("插件", PLUGINS)):
    res = scan(root)
    print(f"===== {label}（{root.name}）=====")
    for k in sorted(res):
        print(f"  [{k}]  {len(res[k])} 个")
        for n in sorted(res[k]):
            print(f"      {n}")
    print()

print("===== 插件目录 =====")
if PLUGINS.exists():
    for d in sorted(PLUGINS.iterdir()):
        print("  ", d.name)
