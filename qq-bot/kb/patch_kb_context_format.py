#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_kb_context_format.py —— 把知识库那段"资料壳"换成"回忆"的口吻

## 为什么要改

她每轮读到的检索结果长这样（`kb_mgr.py:342 _format_context` 拼的）：

    以下是相关的知识库内容,请参考这些信息回答用户的问题:

    【知识 1】
    来源: 未花·日记 / 2026-09-03.md
    内容: [日记 2026-09-03] ……
    相关度: 0.90

**三个标签全是给程序看的**，但模型读到的就是它们。而 `astr_main_agent.py` 那段
注入头又连说三遍「这是第三人称写的资料／不要模仿它的行文」——
**等于反复告诉她"这是资料"**。资料当然要用资料腔念。

于是就有了「我先查再答」那种腔调。

## 改成什么

1. `kb_mgr.py::_format_context` —— 去掉 `【知识 N】` / `来源:` / `相关度:`，
   换成一句"这是你自己记得的东西"。来源和分数改走 `logger.debug`（开 DEBUG 还能看）。
2. `astr_main_agent.py::_apply_kb` 的注入头 —— 从"资料，别模仿"改成
   "**你自己记得的事**，用你自己的口气讲"。

用法：<python> patch_kb_context_format.py [--dry] [--revert]
"""
from __future__ import annotations

import datetime
import pathlib
import shutil
import sys

APP = pathlib.Path(r"C:\SoftWare\Astrbot\backend\app\astrbot")
KB_MGR = APP / "core" / "knowledge_base" / "kb_mgr.py"
MAIN = APP / "core" / "astr_main_agent.py"
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
DRY = "--dry" in sys.argv
REVERT = "--revert" in sys.argv

OLD_FMT = '''        lines = ["以下是相关的知识库内容,请参考这些信息回答用户的问题:\\n"]

        for i, result in enumerate(results, 1):
            lines.append(f"【知识 {i}】")
            lines.append(f"来源: {result.kb_name} / {result.doc_name}")
            lines.append(f"内容: {result.content}")
            lines.append(f"相关度: {result.score:.2f}")
            lines.append("")

        return "\\n".join(lines)
'''

NEW_FMT = '''        # ── 2026-09-26 改动 ────────────────────────────────────────────────
        # 原来每段都带 `【知识 N】` / `来源: 库 / 文档.md` / `相关度: 0.90` 三个标签。
        # 那是**给程序看的**，可是模型读到的就是它——实测她因此学会了"资料综述腔"：
        # 把检索结果当成一份档案来念，而不是当成自己想起来的几件事
        # （原话：「先查再答。中间正文保持空。」）。
        # 现在只给内容，用"你自己记得的事"起头。来源/分数改走 debug 日志。
        lines = ["下面几段是你自己记得的东西——是你自己的回忆，不是资料。别照着念，用你说话的口气讲：\\n"]

        for result in results:
            lines.append(result.content)
            lines.append("")

        logger.debug(
            "KB 命中 %d 段：%s",
            len(results),
            " | ".join(f"{r.kb_name}/{r.doc_name}({r.score:.2f})" for r in results),
        )

        return "\\n".join(lines)
'''

OLD_HEAD = '''            kb_block = (
                "\\n\\n# 背景资料（仅供核对事实，不要模仿其行文）\\n\\n"
                "下面是从知识库检索到的内容。它是**第三人称写的资料**，不是你的语气。\\n"
                "只用来确认事实（名字、日期、数字、剧情顺序）；\\n"
                "**绝对不要模仿它的措辞、句式与排版**——不要因此把回复写成条目、报告或综述。\\n"
                "确认完，用你自己的嘴重说一遍。\\n\\n"
                f"{kb_result}\\n"
            )
'''

NEW_HEAD = '''            # ── 2026-09-26 改动 ────────────────────────────────────────────
            # 旧文案连说三遍"这是第三人称写的资料／不要模仿它的行文"，
            # 等于反复告诉她"这是资料"——她当然就用念资料的口气回。
            # 现在改成"这是你自己记得的事"：日记本来就是她写的，
            # 知识库那几篇才是参考资料，分开说。
            kb_block = (
                "\\n\\n# 你自己记得的事\\n\\n"
                "下面几段是刚想起来的——**是你自己的记忆，不是一份资料**。\\n"
                "有你自己写的日记，也有你记下的设定和别人整理的研究；\\n"
                "**用你自己的口气讲出来**，不要照着念，更不要因此把回复写成条目或报告。\\n"
                "名字、日期、数字、剧情顺序要准；说法要是你的说法。\\n\\n"
                f"{kb_result}\\n"
            )
'''


def patch(path: pathlib.Path, old: str, new: str, marker: str, tag: str) -> None:
    t = path.read_text(encoding="utf-8")
    if marker in t:
        print(f"  · {path.name}：已经打过这个补丁")
        return
    n = t.count(old)
    if n != 1:
        print(f"  ⚠ {path.name}：锚点命中 {n} 次（应为 1），跳过")
        return
    t = t.replace(old, new, 1)
    if DRY:
        print(f"  ✓ {path.name}（dry-run）")
        return
    bak = path.with_name(path.name + f".bak_kbctx_{tag}_{STAMP}")
    if not bak.exists():
        shutil.copy2(path, bak)
    path.write_text(t, encoding="utf-8")
    print(f"  ✓ {path.name}（备份 {bak.name}）")


def main() -> None:
    if REVERT:
        for p in (KB_MGR, MAIN):
            baks = sorted(p.parent.glob(p.name + ".bak_kbctx_*"))
            if not baks:
                print(f"  ? {p.name} 没有备份")
                continue
            shutil.copy2(baks[-1], p)
            print(f"  ✓ 已还原 {p.name} ← {baks[-1].name}")
        return

    print("1) kb_mgr.py :: _format_context")
    patch(KB_MGR, OLD_FMT, NEW_FMT, "你自己记得的东西——是你自己的回忆", "fmt")
    print("2) astr_main_agent.py :: _apply_kb 的注入头")
    patch(MAIN, OLD_HEAD, NEW_HEAD, "你自己记得的事\\n\\n" if False else "# 你自己记得的事", "head")

    print("\n改完要**重启 AstrBot 后端**才生效。")
    print("还原：python patch_kb_context_format.py --revert")


if __name__ == "__main__":
    main()
