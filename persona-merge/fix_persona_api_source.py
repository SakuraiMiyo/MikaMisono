#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_persona_api_source.py —— 把 persona_api.py 的真源改成「本地原件」，并加镜像同步

## 为什么

之前 `persona_api.py` 推的是 `persona-merge/qq-bot-personality.merged.md`，
而提示词里自称"本真源"的是 `qq-bot/persona/bot-personality.md`——
**两份各改各的，越走越远**（原件落后了一整天）。

现在两份已经对齐（内容完全一致），这个补丁把规则钉死：

    `qq-bot/persona/bot-personality.md`  = 真源（改这里）
    `persona-merge/qq-bot-personality.merged.md` = 它的镜像（`prompt` 时自动同步）

推人格时读真源 → 顺手把镜像写一遍 → 再 PUT。这样两份永远不会分叉。

用法：<python> fix_persona_api_source.py [--dry]
"""
from __future__ import annotations

import pathlib
import sys

P = pathlib.Path(__file__).parent / "persona_api.py"
DRY = "--dry" in sys.argv
t = P.read_text(encoding="utf-8")
orig = t

OLD_CONST = '''BAK = HERE / "_live-persona-backup"
PERSONA = "未小花！"                       # cmd_config: provider_settings.default_personality
DIALOGS = HERE / "预设对话.begin_dialogs.json"
'''
NEW_CONST = '''BAK = HERE / "_live-persona-backup"

# ── 提示词真源与镜像（2026-09-26 钉死）───────────────────────────────
# 真源 = QQ 链路自己的原件；merged 只是给 build_master_prompt.py 读的镜像。
# 推人格时读真源、顺手写一遍镜像，两份就不会再分叉。
SOURCE = HERE.parent / "qq-bot" / "persona" / "bot-personality.md"
MIRROR = HERE / "qq-bot-personality.merged.md"

DIALOGS = HERE / "预设对话.begin_dialogs.json"


def _live_persona_name() -> str:
    """线上真正生效的人格名 —— 就是配置里的 provider_settings.default_personality。

    ⚠️ 2026-09-26 的教训：硬编码成 "未小花！"，而配置里默认的是 "未小花0924"，
    结果一整天改的那份**根本没上线**。这里改成现读配置。
    """
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
        name = cfg.get("provider_settings", {}).get("default_personality")
        if name:
            return name
    except Exception:
        pass
    return "未小花！"


PERSONA = _live_persona_name()
'''
assert t.count(OLD_CONST) == 1, "锚点常量没找到"
t = t.replace(OLD_CONST, NEW_CONST)

OLD_PROMPT = '''    elif cmd == "prompt":
        # 把 qq-bot-personality.merged.md 作为 system_prompt 推上线。
        # ⚠️ 只传 system_prompt 一个字段——update_persona 只更新**传了的字段**
        #    （sqlite.py:1120 `if system_prompt is not None`），begin_dialogs / skills 不受影响。
        src = HERE / "qq-bot-personality.merged.md"
        text = src.read_text(encoding="utf-8")
'''
NEW_PROMPT = '''    elif cmd == "prompt":
        # 把**真源**（qq-bot/persona/bot-personality.md）作为 system_prompt 推上线。
        # ⚠️ 只传 system_prompt 一个字段——update_persona 只更新**传了的字段**
        #    （sqlite.py:1120 `if system_prompt is not None`），begin_dialogs / skills 不受影响。
        if not SOURCE.exists():
            print(f"✗ 找不到真源 {SOURCE}")
            return
        text = SOURCE.read_text(encoding="utf-8")
        # 顺手把镜像写一遍，保证 build_master_prompt.py 读到的是同一份
        if not MIRROR.exists() or MIRROR.read_text(encoding="utf-8") != text:
            MIRROR.write_text(text, encoding="utf-8")
            print(f"  （已同步镜像 {MIRROR.name}）")
'''
assert t.count(OLD_PROMPT) == 1, "锚点 prompt 段没找到"
t = t.replace(OLD_PROMPT, NEW_PROMPT)

# 加一个 check 子命令
OLD_TAIL = '''    else:
        print(__doc__)
'''
NEW_TAIL = '''    elif cmd == "check":
        live = _live_persona_name()
        d = get(c)
        sp = d.get("system_prompt") or ""
        src = SOURCE.read_text(encoding="utf-8") if SOURCE.exists() else ""
        mir = MIRROR.read_text(encoding="utf-8") if MIRROR.exists() else ""
        print(f"配置默认人格（= 线上生效）：{live!r}")
        print(f"  真源 {SOURCE.name:<28} {len(src):>7,} 字")
        print(f"  镜像 {MIRROR.name:<28} {len(mir):>7,} 字")
        print(f"  线上 system_prompt{'':<20} {len(sp):>7,} 字")
        print(f"  线上 begin_dialogs{'':<21} {len(d.get('begin_dialogs') or []):>7} 条")
        print(f"  线上 skills：{d.get('skills')!r}")
        print()
        print(f"  真源 == 镜像        ：{src == mir}")
        print(f"  真源 == 线上 prompt ：{src == sp}")
        if src != sp:
            print("  ⚠️ 线上不是最新——跑一次 `persona_api.py prompt` 推上去")

    else:
        print(__doc__)
'''
assert t.count(OLD_TAIL) == 1
t = t.replace(OLD_TAIL, NEW_TAIL)

if DRY:
    print("（dry-run，未写盘）")
else:
    P.write_text(t, encoding="utf-8")
    print(f"✓ {P.name}：{len(orig):,} → {len(t):,} 字")
