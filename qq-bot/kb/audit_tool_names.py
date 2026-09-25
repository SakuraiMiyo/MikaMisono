# -*- coding: utf-8 -*-
"""audit_tool_names.py —— 权威核验：白名单里每个名字是否真实存在

## 为什么必须核

`astr_main_agent.py:635`：

```python
tool = tmgr.get_func(tool_name)
if tool and tool.active:
    persona_toolset.add_tool(tool)
```

**名字写错 → `get_func` 返回 None → 那个工具静默消失**，没有警告、没有日志。
白名单是"少挂"型错误，测试的时候最容易看不出来——
她只是偶尔做不了某件事，谁也不会想到是名字拼错。

## 名字从哪来（四类，来源各不相同）

| 类别 | 真名怎么定的 | 去哪找 |
|---|---|---|
| 内置 | `name: str = "astrbot_xxx"` | `core/tools/**/*.py` |
| 插件类 | `@filter.llm_tool(name="x")` 或 `name` 属性 | `data/plugins/<plugin>/**/*.py` |
| 插件（_conf_schema 注册） | `llm_tool(name=)` 形式 | 同上 |
| MCP | 服务端 tools 列表 | `data/mcp_server.json` + 服务端 |

用法：<python> audit_tool_names.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

APP = pathlib.Path(r"C:\SoftWare\Astrbot\backend\app")
PLUGINS = pathlib.Path.home() / ".astrbot" / "data" / "plugins"
SKILLS = pathlib.Path.home() / ".astrbot" / "data" / "skills"

# ── 1. 内置 ────────────────────────────────────────────────────────
builtin: dict[str, str] = {}
for p in (APP / "astrbot" / "core" / "tools").rglob("*.py"):
    t = p.read_text(encoding="utf-8", errors="ignore")
    for m in re.finditer(r'name:\s*str\s*=\s*"([a-zA-Z0-9_\-]+)"', t):
        builtin[m.group(1)] = p.name

# ── 2. 插件（含 llm_tool 装饰器与属性两种写法）──────────────────────
plugin: dict[str, str] = {}
PATTERNS = [
    re.compile(r'@filter\.llm_tool\(\s*name\s*=\s*"([^"]+)"'),
    re.compile(r"@filter\.llm_tool\(\s*name\s*=\s*'([^']+)'"),
    re.compile(r'name:\s*str\s*=\s*"([a-zA-Z0-9_\-]+)"'),
    re.compile(r'\.llm_tool\(\s*name\s*=\s*"([^"]+)"'),
]
for p in PLUGINS.rglob("*.py"):
    if "site-packages" in p.parts or "node_modules" in p.parts:
        continue
    t = p.read_text(encoding="utf-8", errors="ignore")
    for rx in PATTERNS:
        for m in rx.finditer(t):
            nm = m.group(1)
            if 2 < len(nm) < 64:
                plugin.setdefault(nm, p.parts[-3] if len(p.parts) > 3 else p.name)

# 插件目录名（`_filter_skills_for_current_config` 用的是 root_dir_name）
plugin_dirs = sorted(d.name for d in PLUGINS.iterdir() if d.is_dir())

# ── 3. MCP 服务端已声明的名字（从日志里那一行拿不到，这里只列服务）──
mcp_cfg = pathlib.Path.home() / ".astrbot" / "data" / "mcp_server.json"
servers = []
try:
    servers = list(json.loads(mcp_cfg.read_text(encoding="utf-8-sig"))["mcpServers"])
except Exception:
    pass

# ── 待核验的名单 ───────────────────────────────────────────────────
sys.path.insert(0, r"C:\OneDrive\MikaMisono\persona-merge")
import importlib.util
spec = importlib.util.spec_from_file_location(
    "atl", r"C:\OneDrive\MikaMisono\persona-merge\apply_tool_whitelist.py")
mod = importlib.util.module_from_spec(spec)
try:
    # 只取 WHITELIST 常量，不跑 main
    src = pathlib.Path(r"C:\OneDrive\MikaMisono\persona-merge\apply_tool_whitelist.py").read_text(encoding="utf-8")
    m = re.search(r"^WHITELIST = \[(.*?)^\]", src, re.S | re.M)
    names = re.findall(r'"([^"]+)"', m.group(1))
except Exception as e:
    print("读不到 WHITELIST：", e)
    sys.exit(1)

print(f"内置 {len(builtin)} 个 · 插件类 {len(plugin)} 个 · 插件目录 {len(plugin_dirs)} 个")
print(f"MCP 服务：{servers}")
print(f"\n待核验白名单 {len(names)} 个：\n")

unknown = []
for n in names:
    where = []
    if n in builtin:
        where.append(f"内置/{builtin[n]}")
    if n in plugin:
        where.append(f"插件/{plugin[n]}")
    if not where:
        # MCP 或其它
        where.append("MCP 或未在源码里静态注册")
        unknown.append(n)
    mark = "✓" if (n in builtin or n in plugin) else "?"
    print(f"  {mark} {n:34} {' · '.join(where)}")

print(f"\n静态核不到的（{len(unknown)} 个，多半是 MCP 工具，需要连上服务端才能确认）：")
for n in unknown:
    print(f"   ? {n}")

print("\n── 有几个高危工具确实存在（确认它们**在**全量集合里）──")
DANGER = ["astrbot_execute_shell", "astrbot_shell_session", "astrbot_grep_tool",
          "astrbot_cua_mouse_click", "astrbot_cua_keyboard_type",
          "astrbot_cua_screenshot", "astrbot_execute_browser",
          "astrbot_file_edit_tool", "astrbot_execute_python"]
for d in DANGER:
    print(f"   {'在' if d in builtin else '不在':4} {d}")
