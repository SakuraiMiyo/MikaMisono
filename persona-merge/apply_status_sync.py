#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""apply_status_sync.py —— 把文档里「线上人格是 未小花！」这句过期的话改对

2026-09-26 发现配置里 `default_personality = '未小花0924'`，
所以线上生效的一直是它，不是 `未小花！`。两份现在已同步成同一份内容，
但**文档里还到处写着「未小花！」**，下次照着文档操作又会踩同一个坑。

改这几处：
  · `persona-merge/README.md`        状态表（还写着"没上线"）
  · `persona-merge/预设对话.md`       尾部说明
  · `persona-merge/build_master_prompt.py`  第 4/5 部里硬编码的人格名
  · `docs/未花系统总览.md`            人格条数

用法：<python> apply_status_sync.py [--dry]
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent
DRY = "--dry" in sys.argv

EDITS: list[tuple[str, str, str]] = [
    ("persona-merge/README.md",
     "> **AstrBot 的预设对话已经上线**（人格 `未小花！`）；**人格本身还是旧版，没上线**。",
     "> **已经全部上线。** 线上生效的人格是 `未小花0924`（= `cmd_config.json` 的\n"
     "> `provider_settings.default_personality`），内容与真源 `qq-bot/persona/bot-personality.md` 完全一致。\n"
     ">\n"
     "> ⚠️ **2026-09-26 的教训**：之前一直以为线上是 `未小花！`，改了一整天都写在它身上，\n"
     "> 而配置指定的其实是 `未小花0924`——**改动根本没生效**。\n"
     "> 现在 `persona_api.py` 会**现读配置**确定线上人格名，推人格前还会回读校验；\n"
     "> `persona_api.py check` 一条命令就能看出「真源 / 镜像 / 线上」三者是否一致。"),
    ("persona-merge/README.md",
     "| AstrBot 预设对话（66 条，☆32 ♪2） | ✅ 已写进 `未小花！` 的 `begin_dialogs` |",
     "| AstrBot 预设对话（**50 条 / 25 组**） | ✅ 已写进线上人格的 `begin_dialogs`（MomoTalk 34 + 剧情口癖 16） |"),
    ("persona-merge/预设对话.md",
     "> 数据：`预设对话.begin_dialogs.json`，**已写入线上人格 `未小花！`**（3,363 字节）。",
     "> 数据：`预设对话.begin_dialogs.json`，**已写入线上人格**（3,363 字节）。\n"
     "> ⚠️ 线上人格名以 `cmd_config.json` 的 `provider_settings.default_personality` 为准\n"
     "> （现在 = `未小花0924`）。`persona_api.py check` 可以一条命令核对。"),
    ("persona-merge/build_master_prompt.py",
     '          "> 写入位置：`data_v4.db` 的 `personas.begin_dialogs`（人格 `未小花！`）。",',
     '          "> 写入位置：`data_v4.db` 的 `personas.begin_dialogs`"\n'
     '          "（人格名 = `cmd_config.json` 的 `provider_settings.default_personality`）。",'),
    ("persona-merge/build_master_prompt.py",
     '          f"| 线上 `未小花！` 的 `system_prompt` | {qq_len:,} 字 | = `qq-bot-personality.merged.md`，**已上线** |",',
     '          f"| 线上人格的 `system_prompt` | {qq_len:,} 字 | = 真源 `qq-bot/persona/bot-personality.md`，**已上线** |",'),
    ("docs/未花系统总览.md",
     "│    │     ├── 人格：SQLite  data_v4.db → personas 表（3 条：未花/未花2/未小花！）│",
     "│    │     ├── 人格：SQLite  data_v4.db → personas 表（生效的那条由配置指定）      │"),
]

for rel, old, new in EDITS:
    p = ROOT / rel
    if not p.exists():
        print(f"  ? 找不到 {rel}")
        continue
    t = p.read_text(encoding="utf-8")
    n = t.count(old)
    if n == 0:
        print(f"  ⚠ {rel}：锚点没命中，跳过")
        continue
    t = t.replace(old, new)
    if not DRY:
        p.write_text(t, encoding="utf-8")
    print(f"  ✓ {rel}（{n} 处）")

print("\n（dry-run，未写盘）" if DRY else "\n完成")
