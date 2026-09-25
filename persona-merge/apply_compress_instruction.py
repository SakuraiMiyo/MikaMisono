# -*- coding: utf-8 -*-
"""
第八轮 · 上下文压缩指令（`llm_compress_instruction`）

## 为什么改

`context_limit_reached_strategy = "llm_compress"`。历史超限时，AstrBot 把旧历史
交给 `llm_compress_provider`（同样是 deepseek-flash）压成一段摘要，
再把摘要当成一条 `user` 消息插回上下文
（`compressor.py:294`：`Our previous history conversation summary: …`，
紧跟一条 `assistant` 的 "Acknowledged…"）。

原来用的就是**内置那条英文通用指令**（"produce a concise summary of key takeaways
and/or project progress"）——它是给写代码的 agent 用的。照这条压出来，旧历史里
**她的语气、情绪、当时具体说的话全没了**，只剩光秃秃的事件条目。
于是每压缩一次，她就"忘掉一次自己怎么说话"。

改成保留语域：摘要仍然是**第三人称**（防止把摘要误当成她自己的话），
但要求留住她的口味、符号、当时的情绪走向，以及"答应过的事"。

## 用法

    <python> apply_compress_instruction.py            # 只看现在是什么
    <python> apply_compress_instruction.py --apply    # 写入（改完要重启后端）
"""
from __future__ import annotations

import datetime
import json
import pathlib
import shutil
import sys

HOME = pathlib.Path.home()
CFG = HOME / ".astrbot" / "data" / "cmd_config.json"
BAK = pathlib.Path(r"C:\OneDrive\MikaMisono\_archive-20260924")

NEW = """根据我们之前的完整对话历史，写一份简明的摘要。
这份摘要的唯一用途是：让我在后面的对话里，能接着把这段关系继续下去。

1. 按时间顺序覆盖所有核心话题和每个话题的结论；最新的重点要单独点出来。
2. 用到了工具就写清楚用了什么、结果是什么，别把工具输出原文抄进来。
3. 读过或写过的文件、日记、图片，列出路径或名字和它大概是什么。
4. 当时答应过、还没做完的事，一条都不能漏。
5. **留住语气**：写她说过的话时，保留她当时的用词和语气词（哦、啦、呀、嘛、诶、欸）、
   句末的 ☆ ♪ 〜 和省略号。可以短引号引用关键的那一两句原文。
   情绪怎么起、怎么落，写一句；她是高兴、心虚、气鼓鼓还是难过，要看得出来。
   —— 不要写成中立的会议记录。这份摘要里的人是未花，不是"助手"。
6. 人称用第三人称（"她说""她答应"），不要写成她自己在说话。
7. 用中文写。
"""


def main() -> None:
    apply = "--apply" in sys.argv
    raw = CFG.read_bytes()
    has_bom = raw[:3] == b"\xef\xbb\xbf"
    j = json.loads(raw.decode("utf-8-sig"))
    ps = j["provider_settings"]
    cur = ps.get("llm_compress_instruction", "")

    print(f"配置：{CFG}   BOM={has_bom}   {len(raw):,} 字节")
    print(f"压缩 provider：{ps.get('llm_compress_provider_id')!r}")
    print(f"保留最近比例：{ps.get('llm_compress_keep_recent_ratio')}")
    print(f"\n现在的指令（{len(cur)} 字）：\n{'-'*60}\n{cur}\n{'-'*60}")
    print(f"新的指令（{len(NEW)} 字）：\n{'-'*60}\n{NEW}{'-'*60}")

    if not apply:
        print("（这是预览。加 --apply 才写。）")
        return

    BAK.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = BAK / f"cmd_config-{stamp}.json"
    shutil.copy2(CFG, dst)
    print(f"\n✓ 已备份 -> {dst}")

    ps["llm_compress_instruction"] = NEW
    out = json.dumps(j, ensure_ascii=False, indent=2)
    data = (b"\xef\xbb\xbf" if has_bom else b"") + out.encode("utf-8")
    CFG.write_bytes(data)

    # 回读校验
    chk = json.loads(CFG.read_bytes().decode("utf-8-sig"))
    got = chk["provider_settings"]["llm_compress_instruction"]
    print(f"✓ 已写入并回读一致：{got == NEW}")
    print("  ⚠️ 配置是启动时读的 —— 要让后端重启一次才生效。")


if __name__ == "__main__":
    main()
