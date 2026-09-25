#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_intermediate_text_block.py —— 工具循环的中间步骤不再产出正文

## 为什么要改（2026-09-23 事故）

deepseek-flash 在 agent 工具循环里会把自言自语写进 completion text（正文通道），
和真正的 reasoning_content 是两回事（推理通道本来就分离干净）。
非流式路径下 `run_agent` 会把**每一步**的正文逐条发到聊天平台：

    [18:35] Let me wait ~ 20s and check.
    [18:35] Backend up on the 5080. Let me check my swimsuit reference ...
    [18:38] Let me poll again.
    [18:38] All five are out. Let me downscale for sending.

共 9 条英文思考碎片直接进了 QQ。更糟的是同一句「Let me poll again.」
在会话历史里**同时**存成 think 块和 text 块——模型把思考流复述进了正文。

**提示词层压不住**（人格禁令、EXTRA_PROMPT 都写过"中间别说话"，模型无视），
只能机械拦截：**凡是带工具调用的中间步骤，不 yield 正文链**；
只有最终一步（不再调用工具）的正文才允许产出。

`send_message_to_user` 走工具直发通道，不受此补丁影响——
「做一步说一步」的进度播报从那儿走，两边不打架。

## 改哪里

`tool_loop_agent_runner.py`：把主循环里 result_chain / completion_text 的
yield 包进 `if not llm_resp.tools_call_name:`。
（skills_like 回查路径本来就只在无工具调用时 yield，不用动。）

## 边界

- 只保护**非流式**路径。流式 delta（streaming_delta）在 chunk 层无法预知
  该步会不会带工具调用，补不了——**`streaming_response` 必须保持关闭**，
  开了泄漏就会复发。
- 中止（abort）路径不发送中间文本，行为不变；用户主动停止本就不该再收消息。

用法：<python> patch_intermediate_text_block.py [--dry] [--revert]
"""
from __future__ import annotations

import datetime
import pathlib
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

APP = pathlib.Path(r"C:\SoftWare\Astrbot\backend\app\astrbot")
RUNNER = APP / "core" / "agent" / "runners" / "tool_loop_agent_runner.py"
PY = sys.executable or r"C:\SoftWare\Astrbot\backend\python\python.exe"
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
DRY = "--dry" in sys.argv
REVERT = "--revert" in sys.argv

OLD = '''        if llm_resp.result_chain:
            yield AgentResponse(
                type="llm_result",
                data=AgentResponseData(chain=llm_resp.result_chain),
            )
        elif llm_resp.completion_text:
            yield AgentResponse(
                type="llm_result",
                data=AgentResponseData(
                    chain=MessageChain().message(llm_resp.completion_text),
                ),
            )
'''

NEW = '''        # ── 2026-09-24 改动 ────────────────────────────────────────────────
        # 带工具调用的中间步骤不产出正文：deepseek 等模型会在工具循环中
        # 把自言自语写进 completion text，这些字会被下游逐条发到聊天平台。
        # 只有不含工具调用的最终步骤才允许产出正文链。
        if not llm_resp.tools_call_name:
            if llm_resp.result_chain:
                yield AgentResponse(
                    type="llm_result",
                    data=AgentResponseData(chain=llm_resp.result_chain),
                )
            elif llm_resp.completion_text:
                yield AgentResponse(
                    type="llm_result",
                    data=AgentResponseData(
                        chain=MessageChain().message(llm_resp.completion_text),
                    ),
                )
'''

MARKER = "带工具调用的中间步骤不产出正文"


def main() -> None:
    if REVERT:
        baks = sorted(RUNNER.parent.glob(RUNNER.name + ".bak_itm_*"))
        if not baks:
            print(f"  ? {RUNNER.name} 没有备份")
            return
        shutil.copy2(baks[-1], RUNNER)
        print(f"  ✓ 已还原 {RUNNER.name} ← {baks[-1].name}")
        return

    t = RUNNER.read_text(encoding="utf-8")
    if MARKER in t:
        print(f"  · {RUNNER.name}：已经打过这个补丁")
        return
    n = t.count(OLD)
    if n != 1:
        print(f"  ⚠ {RUNNER.name}：锚点命中 {n} 次（应为 1），跳过")
        print("    （AstrBot 升级后源码变了？对照补丁说明手改，别硬替换）")
        return
    if DRY:
        print(f"  ✓ {RUNNER.name}（dry-run，锚点唯一）")
        return

    bak = RUNNER.with_name(RUNNER.name + f".bak_itm_{STAMP}")
    shutil.copy2(RUNNER, bak)
    RUNNER.write_text(t.replace(OLD, NEW, 1), encoding="utf-8")

    r = subprocess.run(
        [PY, "-c", f"import py_compile; py_compile.compile(r'{RUNNER}', doraise=True)"],
        capture_output=True, text=True)
    if r.returncode != 0:
        shutil.copy2(bak, RUNNER)  # 语法坏了就回滚
        print(f"  ✗ py_compile 失败，已回滚：{(r.stderr or '').strip()[:200]}")
        return
    print(f"  ✓ {RUNNER.name}（备份 {bak.name}，py_compile 通过）")
    print("\n改完要**重启 AstrBot 后端**才生效。")
    print("还原：python patch_intermediate_text_block.py --revert")


if __name__ == "__main__":
    main()
