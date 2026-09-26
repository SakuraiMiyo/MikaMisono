#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_segment_leak_filter.py —— 分段发送前的「思考泄漏段」过滤（补丁 #12）

## 为什么要有（2026-09-26 16:50 事故）

#8 补丁封的是「带工具调用的中间步骤」的正文——但这天 deepseek-flash 在
**最终正文里自带思考尾巴**：

    TTS request: 唔，这两个名字听着又耳熟又陌生哦
    TTS request: 找我呀，我最擅长这个" — and ask what topic.

模型写台词时把英文内部计划渗进了输出 token（"# 头脑风暴" 这类输入会显著
加剧）。TTS 失败后 "sending text instead"，英文段原样进群。群友引用实锤。

**这是最终输出内容污染，任何「步骤级」补丁都拦不住**——只能在内容层处理：
分段后、TTS/发送前，对每个 Plain 段做泄漏检测，命中即丢段。

## 判据（宁可错杀段、不可漏英文进群；且她本来的规矩就是正文无英文）

1. 思考短语正则命中（The user / I should / Let me / mode indicator / as Mika would ...）
2. 连续 ≥3 个非技术英文单词的游程（技术词白名单外）——
   「试试 Redis 嘛」安全（1 词）；「— and ask what topic.」命中（4 连）；
   「Surface Pro 9」安全（2 词）。

丢段只丢坏段（同一条回复的其余正常分段照发），并打 warning 日志留痕。

用法：<python> patch_segment_leak_filter.py [--dry] [--revert]
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

# ① 模块级：检测函数（插在 split_text_respecting_brackets 定义之后）
OLD_1 = '''    tail = text[cursor:]
    if tail.strip():
        segments.extend(base_split(tail))
    return segments
'''

NEW_1 = OLD_1 + '''

_THINK_LEAK_TECH = {
    "redis", "python", "java", "javascript", "api", "http", "https", "json",
    "comfyui", "lora", "nas", "tts", "gsv", "gpt", "ai", "id", "ip", "md",
    "bot", "qq", "gif", "png", "jpg", "ua", "ik", "uv", "ui", "cpu", "gpu",
    "ssd", "sql", "git", "github", "stackoverflow", "app", "web", "linux",
    "windows", "docker", "qqbot", "onebot", "ws", "url", "ok",
}
_THINK_LEAK_PHRASES = re.compile(
    r"(the user|i should|i'll respond|i will respond|let me |wait, |hmm, |"
    r"this seems|i need to|mode indicator|as mika would|brainstorm)",
    re.IGNORECASE,
)
_THINK_LEAK_WORD = re.compile(r"[A-Za-z]+")


def has_thinking_leak(text: str) -> bool:
    """判断一段文本是否疑似思考流泄漏（英文计划/分析渗进正文）。"""
    if not text:
        return False
    if _THINK_LEAK_PHRASES.search(text):
        return True
    run = best = 0
    for token in re.split(r"\\s+", text):
        words = _THINK_LEAK_WORD.findall(token)
        if words and all(w.lower() not in _THINK_LEAK_TECH for w in words):
            run += len(words)
            best = max(best, run)
        else:
            run = 0
    return best >= 3
'''

# ② 分段循环之后、TTS 之前：统一过滤 result.chain 里的泄漏段
OLD_2 = '''            # TTS
            tts_provider = (
                await self.ctx.plugin_manager.context.get_using_tts_provider_async(
'''

NEW_2 = '''            # ── 2026-09-26 补丁 #12：思考泄漏段过滤 ──────────────────────
            # #8 封的是中间步骤；这里是最终正文自带英文思考尾巴的情况
            # （TTS 失败 fallback 会把它发进群）。宁丢一段，不放英文。
            _kept_chain = []
            for _comp in result.chain:
                if (
                    isinstance(_comp, Plain)
                    and has_thinking_leak(_comp.text)
                ):
                    logger.warning(
                        "[leak-filter] dropped thinking-leak segment: "
                        f"{_comp.text[:80]!r}"
                    )
                    continue
                _kept_chain.append(_comp)
            result.chain = _kept_chain

            # TTS
            tts_provider = (
                await self.ctx.plugin_manager.context.get_using_tts_provider_async(
'''

MARKER_HELPER = "def has_thinking_leak"
MARKER_INJECT = "补丁 #12：思考泄漏段过滤"


def main() -> None:
    if REVERT:
        baks = sorted(STAGE.parent.glob(STAGE.name + ".bak_leak_*"))
        if not baks:
            print(f"  ? {STAGE.name} 没有备份")
            return
        shutil.copy2(baks[-1], STAGE)
        print(f"  ✓ 已还原 {STAGE.name} ← {baks[-1].name}")
        return

    t = STAGE.read_text(encoding="utf-8")
    if MARKER_HELPER in t and MARKER_INJECT in t:
        print(f"  · {STAGE.name}：已经打过这个补丁")
        return
    if t.count(OLD_1) != 1 or t.count(OLD_2) != 1:
        print(f"  ⚠ 锚点命中不为 1（{t.count(OLD_1)}/{t.count(OLD_2)}），跳过")
        print("    （AstrBot 升级后源码变了？对照补丁说明手改，别硬替换）")
        return
    if DRY:
        print("  ✓（dry-run，锚点均唯一）")
        return

    bak = STAGE.with_name(STAGE.name + f".bak_leak_{STAMP}")
    shutil.copy2(STAGE, bak)
    t = t.replace(OLD_1, NEW_1, 1)
    t = t.replace(OLD_2, NEW_2, 1)
    STAGE.write_text(t, encoding="utf-8")

    r = subprocess.run(
        [PY, "-c", f"import py_compile; py_compile.compile(r'{STAGE}', doraise=True)"],
        capture_output=True, text=True)
    if r.returncode != 0:
        shutil.copy2(bak, STAGE)
        print(f"  ✗ py_compile 失败，已回滚：{(r.stderr or '').strip()[:200]}")
        return
    print(f"  ✓ {STAGE.name}（备份 {bak.name}，py_compile 通过）")
    print("\n改完要**重启 AstrBot 后端**才生效。")
    print("还原：python patch_segment_leak_filter.py --revert")


if __name__ == "__main__":
    main()
