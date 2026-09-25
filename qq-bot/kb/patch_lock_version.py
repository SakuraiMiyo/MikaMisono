#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_lock_version.py —— 版本锁定：封死 WebUI 的核心更新入口

## 为什么要改（2026-09-26 老师拍板）

**AstrBot 固定在 v4.27.3，不升级。** 本项目有 10 个源码补丁 + 一堆
流程假设都建立在这个版本上——升级一次，补丁全部静默消失
（思考泄漏、半括号消息、资料腔一起复发）。

WebUI 的「更新核心」走 `POST /updates/core` → `UpdateService.update_project`。
上游自带一道门：`is_desktop_managed_backend()`（环境变量
`ASTRBOT_DESKTOP_MANAGED=1`）时拒绝执行。但这道门依赖启动方式——
用 `start_backend_desktop_env.ps1` 手动拉起的后端**没设这个变量**，门就是开的。

## 改成什么

`update_service.py :: update_project` 开头加一个**无条件的硬拒绝**，
不管谁、什么环境、点没点，一律返回"版本已锁定"。

不动的东西（有意保留）：
- `update_dashboard`（ensure_dashboard）：是把面板资源**同步到当前版本**的
  修复功能，不是升级；
- `POST /pip/install`：装插件依赖用的，装不坏 `backend\app` 里的核心。

## 还剩一条路（补丁管不到的）

`astrbot-desktop-tauri.exe` 自身的更新弹窗（逻辑编译在 exe 里）。
**在桌面应用里看到"新版本"提示时不要点更新**——点了整个安装目录会被换掉。

用法：<python> patch_lock_version.py [--dry] [--revert]
"""
from __future__ import annotations

import datetime
import pathlib
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

APP = pathlib.Path(r"C:\SoftWare\Astrbot\backend\app\astrbot")
SVC = APP / "dashboard" / "services" / "update_service.py"
PY = sys.executable or r"C:\SoftWare\Astrbot\backend\python\python.exe"
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
DRY = "--dry" in sys.argv
REVERT = "--revert" in sys.argv

OLD = '''    async def update_project(self, data: object) -> UpdateServiceResult:
        if is_desktop_managed_backend():
            raise UpdateServiceError(
                DESKTOP_MANAGED_RESTART_MESSAGE,
                code="desktop_managed",
            )
'''

NEW = '''    async def update_project(self, data: object) -> UpdateServiceResult:
        # ── 2026-09-26 版本锁定 ────────────────────────────────────────────
        # 本部署固定在 v4.27.3：项目里有 10 个源码补丁建立在这个版本上，
        # 升级会让它们全部静默失效。无论是否桌面托管，一律拒绝核心更新。
        raise UpdateServiceError(
            "版本已锁定在 v4.27.3（本项目依赖源码补丁，升级即失效）。"
            "如确需升级，先读 README 第九节。",
            code="version_locked",
        )

        if is_desktop_managed_backend():
            raise UpdateServiceError(
                DESKTOP_MANAGED_RESTART_MESSAGE,
                code="desktop_managed",
            )
'''

MARKER = "版本已锁定在 v4.27.3"


def main() -> None:
    if REVERT:
        baks = sorted(SVC.parent.glob(SVC.name + ".bak_lock_*"))
        if not baks:
            print(f"  ? {SVC.name} 没有备份")
            return
        shutil.copy2(baks[-1], SVC)
        print(f"  ✓ 已还原 {SVC.name} ← {baks[-1].name}")
        return

    t = SVC.read_text(encoding="utf-8")
    if MARKER in t:
        print(f"  · {SVC.name}：已经打过这个补丁")
        return
    n = t.count(OLD)
    if n != 1:
        print(f"  ⚠ {SVC.name}：锚点命中 {n} 次（应为 1），跳过")
        print("    （AstrBot 升级后源码变了？对照补丁说明手改，别硬替换）")
        return
    if DRY:
        print(f"  ✓ {SVC.name}（dry-run，锚点唯一）")
        return

    bak = SVC.with_name(SVC.name + f".bak_lock_{STAMP}")
    shutil.copy2(SVC, bak)
    SVC.write_text(t.replace(OLD, NEW, 1), encoding="utf-8")

    r = subprocess.run(
        [PY, "-c", f"import py_compile; py_compile.compile(r'{SVC}', doraise=True)"],
        capture_output=True, text=True)
    if r.returncode != 0:
        shutil.copy2(bak, SVC)  # 语法坏了就回滚
        print(f"  ✗ py_compile 失败，已回滚：{(r.stderr or '').strip()[:200]}")
        return
    print(f"  ✓ {SVC.name}（备份 {bak.name}，py_compile 通过）")
    print("\n改完要**重启 AstrBot 后端**才生效。")
    print("还原：python patch_lock_version.py --revert")


if __name__ == "__main__":
    main()
