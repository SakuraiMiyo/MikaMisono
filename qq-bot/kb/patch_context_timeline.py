#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_context_timeline.py —— 每轮把「此刻的心情 + 当前有效的事实」注入 system_prompt

## 为什么要有这个（2026-09-26 老师拍板，借鉴 Zep/Graphiti 时间线与情绪状态引擎思想）

private_companion 插件自带「动态情绪 + 关系分」，但它**处于停用状态**，且不打算启用
（启用会带来主动消息编排等一整套行为改变，干扰现有体系）。于是她的上下文里
没有任何关于「此刻心情」和「哪些事实现在还有效」的输入：

- 时间问题：检索命中 Old 事实会被当现状说出来（例：家里电脑 9/8 已换新成 285K+5080，
  旧日记里的 14600KF+5060Ti 若被检索到就是错的）。
- 情绪问题：情绪只活在单轮里，昨天的低落今天无痕。

## 改成什么

`astr_main_agent.py` 在 Persona Instructions 注入后追加「此时此刻」块：

1. 读 `C:\OneDrive\MikaMisono\agent\memory\emotion_state.json` → 心情/精力/对老师温度/情境
2. 读同目录 `timeline.json` → 只渲染**当前有效**的事实（valid_from<=今天<valid_to 或永续），
   按 entity 分组；过期事实被滤掉——这是时间线的全部意义。
3. 文件缺失/损坏/字段不对 → 逐段降级为空，绝不影响请求。

每轮现读磁盘（与人格「每轮现读」同一哲学）：她更新完情绪文件，下一轮立即生效。

## 谁维护

- emotion_state.json：她写完日记后顺手更新（file_read/file_write 工具都在白名单里）。
- timeline.json：老师/工程师手工维护，事实必须带 source，改动走 git。她只读不写。

## 边界

- 注入文案写明「心情影响语气，不影响事实与规矩」。
- 渲染体积可控：当前有效事实 ~20 条 ≈ 600 字 + 心情 ≈ 150 字。

用法：<python> patch_context_timeline.py [--dry] [--revert]
"""
from __future__ import annotations

import datetime
import pathlib
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

APP = pathlib.Path(r"C:\SoftWare\Astrbot\backend\app\astrbot")
MAIN = APP / "core" / "astr_main_agent.py"
PY = sys.executable or r"C:\SoftWare\Astrbot\backend\python\python.exe"
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
DRY = "--dry" in sys.argv
REVERT = "--revert" in sys.argv

OLD = '''    if persona:
        # Inject persona system prompt
        if prompt := persona["prompt"]:
            req.system_prompt += f"\\n# Persona Instructions\\n\\n{prompt}\\n"
        if begin_dialogs := copy.deepcopy(persona.get("_begin_dialogs_processed")):
            req.contexts[:0] = begin_dialogs
'''

NEW = '''    if persona:
        # Inject persona system prompt
        if prompt := persona["prompt"]:
            req.system_prompt += f"\\n# Persona Instructions\\n\\n{prompt}\\n"
        if begin_dialogs := copy.deepcopy(persona.get("_begin_dialogs_processed")):
            req.contexts[:0] = begin_dialogs
        # ── 2026-09-26 改动：注入「此时此刻」（心情 + 当前有效事实）──────────
        # 文件由项目侧维护（C:\\OneDrive\\MikaMisono\\agent\\memory\\），每轮现读；
        # 缺失或损坏时静默跳过，注入是增强不是依赖。
        try:
            state_block = _render_state_and_timeline_block()
            if state_block:
                req.system_prompt += state_block
        except Exception:
            logger.debug("state/timeline block injection failed", exc_info=True)
'''

HELPER_ANCHOR = "async def _apply_workspace_extra_prompt("

HELPER = '''def _render_state_and_timeline_block() -> str:
    """渲染「此时此刻」注入块：emotion_state.json + timeline.json（每轮现读）。

    文件缺失 / JSON 损坏 / 字段不对，逐段降级为空串——注入是增强，不是依赖。
    """
    import datetime as _dt
    import json as _json
    from pathlib import Path as _Path

    base = _Path(r"C:\\OneDrive\\MikaMisono\\agent\\memory")
    parts: list[str] = []

    emo_path = base / "emotion_state.json"
    try:
        emo = _json.loads(emo_path.read_text(encoding="utf-8"))
        mood = emo.get("mood") or {}
        tt = emo.get("toward_teacher") or {}
        valence = mood.get("valence", 0)
        mood_word = (
            "有点低落" if valence <= -2 else
            "平静里带一点闷" if valence < 0 else
            "平稳" if valence == 0 else
            "不错" if valence <= 2 else
            "很好"
        )
        tags = "、".join(str(t) for t in (emo.get("context_tags") or [])[:4])
        parts.append(
            "# 你此刻的状态（实时更新；影响语气，不影响事实与规矩）\\n"
            f"- 心情：{mood_word}（{mood.get('label', '')}）——{mood.get('because', '')}\\n"
            f"- 精力：{emo.get('energy', 70)}/100\\n"
            f"- 对老师：温度 {tt.get('warmth', 5)}/5——{tt.get('note', '')}\\n"
            + (f"- 情境：{tags}\\n" if tags else "")
        )
    except Exception:
        pass

    tl_path = base / "timeline.json"
    try:
        tl = _json.loads(tl_path.read_text(encoding="utf-8"))
        today = _dt.date.today()
        groups: dict[str, list[str]] = {}
        for fact in tl.get("facts", []):
            vf = str(fact.get("valid_from") or "0001-01-01")[:10]
            vt = fact.get("valid_to")
            try:
                if _dt.date.fromisoformat(vf) > today:
                    continue
            except ValueError:
                pass
            if vt:
                try:
                    if _dt.date.fromisoformat(str(vt)[:10]) < today:
                        continue
                except ValueError:
                    pass
            line = f"{fact.get('attribute', '')}：{fact.get('value', '')}"
            groups.setdefault(str(fact.get("entity") or "其他"), []).append(line)
        if groups:
            rendered = "\\n".join(
                f"- {entity}：" + "；".join(lines)
                for entity, lines in sorted(groups.items())
            )
            parts.append(
                "# 你生活里现在仍然有效的事实（核对过的时间线，过期的已滤掉）\\n"
                "拿这些当「现状」说话；记忆与它冲突时，以这里为准。\\n"
                f"{rendered}\\n"
            )
    except Exception:
        pass

    if not parts:
        return ""
    return "\\n" + "\\n".join(parts) + "\\n"


'''

MARKER_HELPER = "def _render_state_and_timeline_block"


def main() -> None:
    if REVERT:
        baks = sorted(MAIN.parent.glob(MAIN.name + ".bak_ctl_*"))
        if not baks:
            print(f"  ? {MAIN.name} 没有备份")
            return
        shutil.copy2(baks[-1], MAIN)
        print(f"  ✓ 已还原 {MAIN.name} ← {baks[-1].name}")
        return

    t = MAIN.read_text(encoding="utf-8")
    if MARKER_HELPER in t:
        print(f"  · {MAIN.name}：已经打过这个补丁")
        return
    if t.count(OLD) != 1:
        print(f"  ⚠ 注入点锚点命中 {t.count(OLD)} 次（应为 1），跳过")
        print("    （AstrBot 升级后源码变了？对照补丁说明手改，别硬替换）")
        return
    if t.count(HELPER_ANCHOR) != 1:
        print(f"  ⚠ helper 锚点命中 {t.count(HELPER_ANCHOR)} 次（应为 1），跳过")
        return
    if DRY:
        print("  ✓（dry-run，两个锚点均唯一）")
        return

    bak = MAIN.with_name(MAIN.name + f".bak_ctl_{STAMP}")
    shutil.copy2(MAIN, bak)
    t = t.replace(OLD, NEW, 1)
    t = t.replace(HELPER_ANCHOR, HELPER + HELPER_ANCHOR, 1)
    MAIN.write_text(t, encoding="utf-8")

    r = subprocess.run(
        [PY, "-c", f"import py_compile; py_compile.compile(r'{MAIN}', doraise=True)"],
        capture_output=True, text=True)
    if r.returncode != 0:
        shutil.copy2(bak, MAIN)
        print(f"  ✗ py_compile 失败，已回滚：{(r.stderr or '').strip()[:200]}")
        return
    print(f"  ✓ {MAIN.name}（备份 {bak.name}，py_compile 通过）")
    print("\n改完要**重启 AstrBot 后端**才生效。")
    print("还原：python patch_context_timeline.py --revert")


if __name__ == "__main__":
    main()
