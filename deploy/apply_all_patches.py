#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""apply_all_patches.py —— 一键把全部源码补丁打到 AstrBot v4.27.3 上

## 什么时候用

新机器部署 / AstrBot 重装后。前置：AstrBot Desktop v4.27.3 已安装在
`C:\\SoftWare\\Astrbot`（推荐从旧机整目录拷贝——版本、webui、python 运行时一起到位；
至少要保证 11 个补丁的锚点源码是 v4.27.3 原版）。

## 用法

    & 'C:\\SoftWare\\Astrbot\\backend\\python\\python.exe' deploy\\apply_all_patches.py

跑完自动执行 verify_live_patches.py。**之后必须重启后端**。
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = pathlib.Path(__file__).resolve().parent.parent / "qq-bot" / "kb"
PY = sys.executable or r"C:\SoftWare\Astrbot\backend\python\python.exe"

# 顺序无关（各自幂等），但按依赖习惯排：上游行为补丁 → 泄漏治理 → 分段 → 锁 → 注入
PATCHES = [
    "patch_kb_context_format.py",       # #1/#2/#5 知识库注入抬头 + 片段格式
    "patch_kb_log_spam.py",             # #6/#7 日志节流
    "patch_kb_tool_always.py",          # #3 知识库工具常挂
    "patch_persona_tool_whitelist.py",  # #4 白名单权限守卫
    "patch_intermediate_text_block.py", # #8 中间步骤正文封锁
    "patch_bracket_segmentation.py",    # #9 括号原子分段
    "patch_lock_version.py",            # #10 版本锁定
    "patch_context_timeline.py",        # #11 此刻状态+时间线注入
]


def main() -> None:
    failed = []
    for name in PATCHES:
        script = HERE / name
        if not script.exists():
            print(f"✗ 找不到 {name}")
            failed.append(name)
            continue
        print(f"── {name}")
        r = subprocess.run([PY, str(script)], capture_output=True, text=True)
        out = (r.stdout or "").strip()
        for line in out.splitlines():
            print(f"   {line}")
        if r.returncode != 0:
            print(f"   ✗ 退出码 {r.returncode}: {(r.stderr or '')[:200]}")
            failed.append(name)

    print()
    if failed:
        print(f"⚠ {len(failed)} 个补丁脚本异常：{failed}")
        print("  （「已经打过」是正常输出；异常才需要看）")
    else:
        print("全部补丁脚本执行完毕（幂等，重跑安全）。")

    print("\n── 核验 ──")
    subprocess.run([PY, str(HERE / "verify_live_patches.py")])
    print("\n如果核验里有「晚于启动 → 还没加载」，**重启后端**即可。")


if __name__ == "__main__":
    main()
