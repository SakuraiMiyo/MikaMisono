# -*- coding: utf-8 -*-
"""
patch_persona_tool_whitelist.py —— 修 AstrBot 的一个安全问题：
**人格的 `tools` 白名单会绕掉逐工具权限校验**

## 问题

`astr_main_agent.py` 有两条挂工具的路：

```python
if (persona and persona.get("tools") is None) or not persona:
    persona_toolset = tmgr.get_full_tool_set()      # ← 全量：走权限包装
    ...
else:
    persona_toolset = ToolSet()
    for tool_name in persona["tools"]:
        tool = tmgr.get_func(tool_name)             # ← 白名单：直接拿，没包装
        if tool and tool.active:
            persona_toolset.add_tool(tool)
```

而 `get_full_tool_set()` 对**非内置工具**（插件、MCP）套了 `_PermissionGuardedTool`：

```python
for tool in self.func_list:
    tool_set.add_tool(_PermissionGuardedTool(tool, self))
```

`_PermissionGuardedTool.__init__` 里有一句关键的注释：

> The ``handler`` field is intentionally kept ``None`` so that
> ``FunctionToolExecutor._execute_local`` falls through to the
> ``is_override_call`` branch and invokes our ``call()`` instead of
> calling the raw handler directly. This ensures the permission
> check runs for *every* invocation path.

**所以两条路的权限语义是不一样的**：一旦给某个人格配上 `tools` 白名单，
她那白名单里的插件/MCP 工具就**不再经过 `_check_tool_permission`**——
面板里逐工具设的权限对她失效。

白名单本来是"收紧"，结果顺带开了个口子。这是**先用白名单之前必须修掉**的东西。

## 修法

只动白名单那一路：拿到工具后，非内置的补上同样的包装。
判内置用现成的 `tmgr.is_builtin_tool(name)`。

## 用法

    <python> patch_persona_tool_whitelist.py            # 只看
    <python> patch_persona_tool_whitelist.py --apply    # 写入（备份 + 语法自检）
"""
from __future__ import annotations

import argparse
import datetime
import pathlib
import py_compile
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")

TARGET = pathlib.Path(
    r"C:\SoftWare\Astrbot\backend\app\astrbot\core\astr_main_agent.py"
)
BAK = pathlib.Path(r"C:\OneDrive\MikaMisono\_archive-20260924")

OLD = """    else:
        persona_toolset = ToolSet()
        if persona["tools"]:
            for tool_name in persona["tools"]:
                tool = tmgr.get_func(tool_name)
                if tool and tool.active:
                    persona_toolset.add_tool(tool)
"""

NEW = """    else:
        persona_toolset = ToolSet()
        if persona["tools"]:
            # ── 2026-09-26 修复：白名单也要套权限守卫 ───────────────────────
            # 原实现直接 `add_tool(tool)`，而这些工具**没有**经过
            # `get_full_tool_set()` 里那层 `_PermissionGuardedTool`，
            # 于是面板上逐工具设的权限对白名单里的人格形同虚设——
            # 配白名单本意是"收紧"，却顺手把权限校验绕掉了。
            # 这里对**非内置**工具补上同一个包装，让两条路的权限语义一致。
            from astrbot.core.provider.func_tool_manager import (
                _PermissionGuardedTool,
            )

            for tool_name in persona["tools"]:
                tool = tmgr.get_func(tool_name)
                if not tool or not tool.active:
                    continue
                if not tmgr.is_builtin_tool(tool_name):
                    tool = _PermissionGuardedTool(tool, tmgr)
                persona_toolset.add_tool(tool)
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    t = TARGET.read_text(encoding="utf-8")
    print(f"目标：{TARGET}")
    print(f"  {len(t):,} 字符")

    if NEW in t:
        print("\n[=] 已经修过了，跳过。")
        return
    if OLD not in t:
        print("\n[!] 没找到要改的那段。文件可能已经变过——先人工看一眼。")
        sys.exit(2)

    print(f"\n[ok] 找到了要改的段落（{len(OLD)} 字符）")

    if not a.apply:
        print("\n（预览。加 --apply 才写。）")
        print("\n将要变成：\n" + "-" * 60)
        print(NEW)
        return

    BAK.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = BAK / f"astr_main_agent-before-toolguard-{stamp}.py"
    shutil.copy2(TARGET, dst)
    print(f"\n✓ 已备份 -> {dst}")

    TARGET.write_text(t.replace(OLD, NEW, 1), encoding="utf-8")
    print("✓ 已写入")

    try:
        py_compile.compile(str(TARGET), doraise=True)
        print("✓ 语法自检通过")
    except py_compile.PyCompileError as e:
        shutil.copy2(dst, TARGET)
        print(f"✗ 语法错误，已回滚：{e}")
        sys.exit(1)

    print("\n⚠️ 代码改动要**重启后端**才生效。")


if __name__ == "__main__":
    main()
