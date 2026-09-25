#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_bracket_segmentation.py —— 分段回复的括号原子化

## 为什么要改（2026-09-24 发现）

分段回复（platform_settings.segmented_reply，regex 模式）按 `[。？！~…]+` 断句，
不认识括号。她在括号内心活动里写句号时：

    （心里其实有点慌。）

会被拆成两条消息发出去：

    （心里其实有点慌。
    ）

第二条以半个括号开头，整段括号不闭合。附带的次生问题：
半截括号 `（心里其实有点慌。` 不成对，会被 TTS 的旁白识别（split_stage_directions）
漏掉、当成台词念出来。

## 改成什么

`result_decorate/stage.py` 三处：

1. 模块级新增 `_BRACKET_GROUP_RE` + `split_text_respecting_brackets()`：
   完整闭合的 `（…）`（含紧随的 ~/… 语气记号）先摘出来作为**独立分段**，
   括号内的句读不参与断句；括号外的文本仍按用户配置的基础规则断句。
2. 类里新增 `_base_split_text()`：把原 words/regex 两条分支收拢成一个方法，
   供上面调用。
3. 分段主逻辑改为调用 `split_text_respecting_brackets(comp.text, self._base_split_text)`。

效果（实测用例）：
    嗯，看完了。（心里其实有点慌。）接下来我去抓图。
→  三条：`嗯，看完了。` / `（心里其实有点慌。）` / `接下来我去抓图。`
    （笑）~ 就这样啦☆
→  两条：`（笑）~` / `就这样啦☆`
未闭合的括号救不了（那是畸形输出），退回普通断句。

用法：<python> patch_bracket_segmentation.py [--dry] [--revert]
"""
from __future__ import annotations

import datetime
import pathlib
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

APP = pathlib.Path(r"C:\SoftWare\Astrbot\backend\app\astrbot")
STAGE = APP / "core" / "pipeline" / "result_decorate" / "stage.py"
PY = sys.executable or r"C:\SoftWare\Astrbot\backend\python\python.exe"
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
DRY = "--dry" in sys.argv
REVERT = "--revert" in sys.argv

# ── ① split_stage_directions 尾部后面追加括号工具 ─────────────────────
OLD_1 = '''    if pos < len(text):
        segments.append((False, text[pos:]))
    return [(is_stage, content) for is_stage, content in segments if content.strip()]
'''

NEW_1 = OLD_1 + '''

_BRACKET_GROUP_RE = re.compile(r"（[^（）]*）[~～…]*", re.UNICODE)


def split_text_respecting_brackets(text: str, base_split) -> list[str]:
    """括号组原子化分段：完整闭合的 （…）（含紧随的 ~/… 语气记号）视作独立分段。

    括号内出现的句读符号不参与断句，避免把（内心活动。）拆成半括号消息；
    括号外的文本仍按调用方传入的基础规则断句。
    """
    segments: list[str] = []
    cursor = 0
    for match in _BRACKET_GROUP_RE.finditer(text):
        head = text[cursor : match.start()]
        if head.strip():
            segments.extend(base_split(head))
        segments.append(match.group(0))
        cursor = match.end()
    tail = text[cursor:]
    if tail.strip():
        segments.extend(base_split(tail))
    return segments
'''

# ── ② 类里加 _base_split_text，收拢 words/regex 两条分支 ────────────────
OLD_2 = '''    def _split_text_by_words(self, text: str) -> list[str]:
        """使用分段词列表分段文本"""
'''

NEW_2 = '''    def _base_split_text(self, text: str) -> list[str]:
        """按用户配置的基础规则（words/regex）断句，不含括号感知。"""
        if self.split_mode == "words":
            return self._split_text_by_words(text)
        try:  # regex 模式
            return re.findall(self.regex, text, re.DOTALL | re.MULTILINE)
        except re.error:
            logger.error(
                "Invalid segmented-reply regular expression; "
                "using the default segmentation method: "
                f"{traceback.format_exc()}",
            )
            return re.findall(
                r".*?[。？！~…]+|.+$",
                text,
                re.DOTALL | re.MULTILINE,
            )

    def _split_text_by_words(self, text: str) -> list[str]:
        """使用分段词列表分段文本"""
'''

# ── ③ 分段主逻辑改为括号感知调用 ───────────────────────────────────────
OLD_3 = '''                            # 根据 split_mode 选择分段方式
                            if self.split_mode == "words":
                                split_response = self._split_text_by_words(comp.text)
                            else:  # regex 模式
                                try:
                                    split_response = re.findall(
                                        self.regex,
                                        comp.text,
                                        re.DOTALL | re.MULTILINE,
                                    )
                                except re.error:
                                    logger.error(
                                        "Invalid segmented-reply regular expression; "
                                        "using the default segmentation method: "
                                        f"{traceback.format_exc()}",
                                    )
                                    split_response = re.findall(
                                        r".*?[。？！~…]+|.+$",
                                        comp.text,
                                        re.DOTALL | re.MULTILINE,
                                    )
'''

NEW_3 = '''                            # 括号感知分段：完整闭合的 （…） 独立成段，括号内不断句
                            split_response = split_text_respecting_brackets(
                                comp.text, self._base_split_text
                            )
'''

HUNKS = [
    (OLD_1, NEW_1, "split_text_respecting_brackets"),
    (OLD_2, NEW_2, "_base_split_text"),
    (OLD_3, NEW_3, "括号感知分段"),
]


def main() -> None:
    if REVERT:
        baks = sorted(STAGE.parent.glob(STAGE.name + ".bak_brk_*"))
        if not baks:
            print(f"  ? {STAGE.name} 没有备份")
            return
        shutil.copy2(baks[-1], STAGE)
        print(f"  ✓ 已还原 {STAGE.name} ← {baks[-1].name}")
        return

    t = STAGE.read_text(encoding="utf-8")
    if all(marker in t for _, _, marker in HUNKS):
        print(f"  · {STAGE.name}：已经打过这个补丁")
        return

    # 先把三块的锚点都数一遍，任何一块不唯一就整体跳过（避免打到一半）
    counts = [t.count(old) for old, _, _ in HUNKS]
    for (old, _, marker), n in zip(HUNKS, counts):
        print(f"  · 锚点[{marker[:12]}…] 命中 {n} 次")
    if any(n != 1 for n in counts):
        print("  ⚠ 有锚点不是恰好 1 次，整体跳过")
        print("    （AstrBot 升级后源码变了？对照补丁说明手改，别硬替换）")
        return
    if DRY:
        print(f"  ✓ {STAGE.name}（dry-run，锚点全部唯一）")
        return

    bak = STAGE.with_name(STAGE.name + f".bak_brk_{STAMP}")
    shutil.copy2(STAGE, bak)
    for old, new, _ in HUNKS:
        t = t.replace(old, new, 1)
    STAGE.write_text(t, encoding="utf-8")

    r = subprocess.run(
        [PY, "-c", f"import py_compile; py_compile.compile(r'{STAGE}', doraise=True)"],
        capture_output=True, text=True)
    if r.returncode != 0:
        shutil.copy2(bak, STAGE)  # 语法坏了就回滚
        print(f"  ✗ py_compile 失败，已回滚：{(r.stderr or '').strip()[:200]}")
        return
    print(f"  ✓ {STAGE.name}（备份 {bak.name}，py_compile 通过）")
    print("\n改完要**重启 AstrBot 后端**才生效。")
    print("还原：python patch_bracket_segmentation.py --revert")


if __name__ == "__main__":
    main()
