#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_kb_tool_always.py —— 让「查资料」有且只有一条路：走知识库

## 起因（老师的原话）

> 「他查资料也不应该这样查呀，应该是从我的给他做的知识库去查呀。
>  你这样如果说我问他对群友有什么印象的话他答不上来，那我的知识库不白做了吗。
>  你让他查资料的时候直接通过知识库去查。」

## 现在的代码为什么没做到

`astr_main_agent.py` 的 `_apply_kb()` 是个 **if / else**：

```python
if not config.kb_agentic_mode:
    <自动检索，把结果塞进 system_prompt>     # ← 现在走这条
else:
    <把 KnowledgeBaseQueryTool 挂到工具集>   # ← 这条永远不走
```

也就是说：**自动检索开着的时候，她手里根本没有"查知识库"这个工具。**
于是有人问「你对群友有什么印象」，她只有 shell / grep / 读文件可用——
实测跑了 6 次工具、59,937 字输出全进历史（占那轮 98%），
而**答案其实就在知识库里**（`未花·日记` 那一库的 2026-09-09、2026-07-02 都提到了群友）。

## 这个补丁做什么

把 if/else 改成「**自动检索照旧 + 无论哪种模式都把知识库查询工具挂上**」。
这样：

- 每轮照旧白拿一段背景资料（不用她动手）
- 但她想主动查的时候，手里有 `astr_kb_search` 这条路

用法：<python> patch_kb_tool_always.py [--dry] [--revert]
"""
from __future__ import annotations

import datetime
import pathlib
import shutil
import sys

TARGET = pathlib.Path(
    r"C:\SoftWare\Astrbot\backend\app\astrbot\core\astr_main_agent.py")
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
DRY = "--dry" in sys.argv
REVERT = "--revert" in sys.argv

OLD = '''            req.system_prompt = (req.system_prompt or "") + kb_block
        except Exception as exc:  # noqa: BLE001
            logger.error("Error occurred while retrieving knowledge base: %s", exc)
    else:
        if req.func_tool is None:
            req.func_tool = ToolSet()
        req.func_tool.add_tool(
            plugin_context.get_llm_tool_manager().get_builtin_tool(
                KnowledgeBaseQueryTool
            )
        )
'''

NEW = '''            req.system_prompt = (req.system_prompt or "") + kb_block
        except Exception as exc:  # noqa: BLE001
            logger.error("Error occurred while retrieving knowledge base: %s", exc)

    # ── 2026-09-26 改动：两种模式不再互斥 ─────────────────────────────────────
    # 原实现是 if / else：kb_agentic_mode=False 时**只**自动注入，不给她查询工具。
    # 实测后果：有人问「你对群友有什么印象」，她手里只有 shell/grep/读文件，
    # 于是 grep 日记目录、跑 PowerShell、读记忆卡——6 次工具、59,937 字输出全进历史
    # （占那一轮历史的 98%），而答案本来就在知识库里（未花·日记 那一库）。
    # 改成：自动注入照旧，**并且**无论哪种模式都把知识库查询工具挂给她。
    # 让「查资料」有且只有一条路——走老师建的那几个知识库（日记也在里面）。
    if req.func_tool is None:
        req.func_tool = ToolSet()
    req.func_tool.add_tool(
        plugin_context.get_llm_tool_manager().get_builtin_tool(
            KnowledgeBaseQueryTool
        )
    )
'''


def main() -> None:
    baks = sorted(TARGET.parent.glob(TARGET.name + ".bak_kbtool_*"))
    if REVERT:
        if not baks:
            print("没有备份，无法还原")
            return
        shutil.copy2(baks[-1], TARGET)
        print(f"✓ 已还原 ← {baks[-1].name}")
        return

    t = TARGET.read_text(encoding="utf-8")
    if "2026-09-26 改动：两种模式不再互斥" in t:
        print("· 已经打过这个补丁，跳过")
        return
    n = t.count(OLD)
    if n != 1:
        print(f"⚠ 锚点命中 {n} 次（应为 1），中止")
        raise SystemExit(1)

    t = t.replace(OLD, NEW, 1)
    if DRY:
        print("（dry-run，未写盘）")
        return
    bak = TARGET.with_name(TARGET.name + f".bak_kbtool_{STAMP}")
    shutil.copy2(TARGET, bak)
    TARGET.write_text(t, encoding="utf-8")
    print(f"✓ 已打补丁（备份 {bak.name}）")
    print("  改完要**重启 AstrBot 后端**才生效。")
    print("  还原：python patch_kb_tool_always.py --revert")


if __name__ == "__main__":
    main()
