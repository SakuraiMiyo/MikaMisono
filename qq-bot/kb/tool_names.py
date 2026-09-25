#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tool_names.py —— 找出每个工具类**对 LLM 暴露的名字**（白名单要用这个）

`persona.tools` 是**按工具名**匹配的，不是类名。
所以要把 `KnowledgeBaseQueryTool` / `GrepTool` / `FileReadTool` … 的 `name` 属性挖出来。
"""
from __future__ import annotations

import pathlib
import re

APP = pathlib.Path(r"C:\SoftWare\Astrbot\backend\app\astrbot")
PLUGINS = pathlib.Path.home() / ".astrbot" / "data" / "plugins"

WANT = [
    "KnowledgeBaseQueryTool", "GrepTool", "FileReadTool", "FileWriteTool",
    "FileEditTool", "ExecuteShellTool", "LocalExecuteShellTool", "ShellSessionTool",
    "LocalPythonTool", "PythonTool", "GetGroupMessageHistoryTool",
    "SendMessageToUserTool", "BrowserExecTool", "CuaScreenshotTool",
    "FutureTaskTool", "AnnotateExecutionTool", "HandoffTool",
    "MikaVoiceTool",
]

CLS = re.compile(r"^class\s+(\w+)\s*[\(:]", re.M)
NAME = re.compile(r"^\s{4,8}name\s*(?::\s*[^=]+)?=\s*['\"]([^'\"]+)['\"]", re.M)


def main() -> None:
    seen: dict[str, str] = {}
    for root in (APP, PLUGINS):
        if not root.exists():
            continue
        for p in root.rglob("*.py"):
            if "node_modules" in str(p):
                continue
            try:
                t = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            marks = [(m.start(), m.group(1)) for m in CLS.finditer(t)]
            for i, (pos, cname) in enumerate(marks):
                end = marks[i + 1][0] if i + 1 < len(marks) else len(t)
                body = t[pos:end]
                if cname in WANT and cname not in seen:
                    nm = NAME.search(body)
                    seen[cname] = nm.group(1) if nm else "（没找到 name 属性）"

    print("类名 → LLM 工具名：")
    for k in WANT:
        print(f"  {k:<30} {seen.get(k, '（这个项目里没有）')}")

    # 顺便把已知的 AstrBot 内置工具名全捞一遍（保险）
    print("\n所有带 name= 的工具类（前 60）：")
    out = []
    for root in (APP,):
        for p in root.rglob("*.py"):
            t = p.read_text(encoding="utf-8", errors="ignore")
            marks = [(m.start(), m.group(1)) for m in CLS.finditer(t)]
            for i, (pos, cname) in enumerate(marks):
                if not cname.endswith("Tool"):
                    continue
                end = marks[i + 1][0] if i + 1 < len(marks) else len(t)
                nm = NAME.search(t[pos:end])
                if nm:
                    out.append((cname, nm.group(1)))
    for c, n in sorted(set(out))[:60]:
        print(f"  {c:<34} {n}")


if __name__ == "__main__":
    main()
