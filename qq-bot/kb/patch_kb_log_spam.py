#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_kb_log_spam.py —— 给「embedding 服务挂掉 → 日志刷爆」加限流

## 事故（2026-09-26 00:36）

本机 ollama（`127.0.0.1:11434`，跑 `bge-m3` 做 embedding）没在运行，
AstrBot 的知识库稠密检索全军覆没，日志变成这样：

    [Ollama Embedding] Network error: Cannot connect to host 127.0.0.1:11434
    知识库 542230be-… 稠密检索失败: ClientConnectorError: …
    <一整页 traceback>
    …× 5 个知识库 × 每轮压缩 + 回答 2 次调用 = 一轮 10 段

`retrieval/manager.py` 里那句是 `logger.error(..., exc_info=True)`，
所以每段都带完整 traceback——桌面疯狂弹窗，而且真正有用的行全被埋掉。

## 改什么

1. `retrieval/manager.py`
   `_dense_retrieve` 的 except：去掉 `exc_info=True`，改成**限流**——
   同一个「知识库 + 异常类型」5 分钟内只报一条，并在消息里直接点明
   「本机 ollama 没在跑？跑一句 `ollama list` 就会把它拉起来」。

2. `provider/sources/ollama_embedding_source.py`
   网络错误那条同样限流（原来每轮 10 行）。

**行为不变**：仍然是「跳过出故障的库，继续走稀疏检索」，只是不再刷屏。

用法：<python> patch_kb_log_spam.py [--dry] [--revert]
"""
from __future__ import annotations

import datetime
import pathlib
import shutil
import sys

APP = pathlib.Path(r"C:\SoftWare\Astrbot\backend\app\astrbot")
MGR = APP / "core" / "knowledge_base" / "retrieval" / "manager.py"
OLL = APP / "core" / "provider" / "sources" / "ollama_embedding_source.py"
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
DRY = "--dry" in sys.argv
REVERT = "--revert" in sys.argv

HELPER = '''

# ── 2026-09-26 新增：稠密检索失败的日志限流 ─────────────────────────────
# 背景：embedding 走本机 ollama(127.0.0.1:11434)。ollama 一挂，
# **每个知识库、每一轮**都会失败一次（5 个库 × 每轮 2 次调用 ≈ 一轮 10 段），
# 而原来这里带 `exc_info=True`，于是每段都是一整页 traceback——
# 日志被刷爆、桌面疯狂弹窗，真正有用的行全被埋掉。
# 现在：同一个「库 + 异常类型」5 分钟内只报一条，且不打 traceback。
_DENSE_ERR_LAST: dict[str, float] = {}
_DENSE_ERR_INTERVAL_S = 300.0


def _log_dense_error(kb_id: str, exc: BaseException) -> None:
    """限流地记一条稠密检索失败，并点明最可能的原因。"""
    sig = f"{kb_id}|{type(exc).__name__}"
    now = time.monotonic()
    if now - _DENSE_ERR_LAST.get(sig, -1e9) < _DENSE_ERR_INTERVAL_S:
        return
    _DENSE_ERR_LAST[sig] = now
    hint = ""
    low = str(exc).lower()
    if "11434" in low or "ollama" in low or "connect" in low:
        hint = "（本机 ollama 没在跑？随便跑一句 `ollama list` 就会把它拉起来）"
    logger.error(
        f"知识库 {kb_id} 稠密检索失败{hint}: {type(exc).__name__}: {exc}"
        f"；该库本轮只走稀疏检索，同一错误 {int(_DENSE_ERR_INTERVAL_S)} 秒内不再重复打印"
    )

'''

OLL_HELPER = '''

# ── 2026-09-26 新增：embedding 网络错误的日志限流 ───────────────────────
# 知识库一多，这个错误每轮会重复十次；限流成 5 分钟一条，保留信息但不再刷屏。
_OLL_ERR_LAST: dict[str, float] = {}
_OLL_ERR_INTERVAL_S = 300.0


def _log_ollama_net_error(exc: BaseException) -> None:
    import time as _t

    sig = type(exc).__name__
    now = _t.monotonic()
    if now - _OLL_ERR_LAST.get(sig, -1e9) < _OLL_ERR_INTERVAL_S:
        return
    _OLL_ERR_LAST[sig] = now
    logger.error(
        f"[Ollama Embedding] Network error: {exc}"
        f"（{int(_OLL_ERR_INTERVAL_S)} 秒内同类错误不再重复打印）"
    )

'''


def patch(path: pathlib.Path, edits: list[tuple[str, str]], tag: str) -> None:
    t = path.read_text(encoding="utf-8")
    orig = t
    for old, new in edits:
        n = t.count(old)
        if n != 1:
            print(f"  ⚠ {path.name}：锚点命中 {n} 次，跳过该处")
            continue
        t = t.replace(old, new)
    if t == orig:
        print(f"  · {path.name}：无需改动（可能已经打过补丁）")
        return
    if DRY:
        print(f"  ✓ {path.name}（dry-run）")
        return
    bak = path.with_name(path.name + f".bak_{tag}_{STAMP}")
    if not bak.exists():
        shutil.copy2(path, bak)
    path.write_text(t, encoding="utf-8")
    print(f"  ✓ {path.name}（备份 {bak.name}）")


def main() -> None:
    if REVERT:
        for p in (MGR, OLL):
            baks = sorted(p.parent.glob(p.name + ".bak_kbspam_*"))
            if not baks:
                print(f"  ? {p.name} 没有备份，跳过")
                continue
            shutil.copy2(baks[-1], p)
            print(f"  ✓ 已还原 {p.name} ← {baks[-1].name}")
        return

    print("1) retrieval/manager.py")
    patch(MGR, [
        ("\n@dataclass\nclass RetrievalResult:",
         HELPER + "\n@dataclass\nclass RetrievalResult:"),
        ("""            except Exception as e:
                logger.error(
                    f"知识库 {kb_id} 稠密检索失败: {type(e).__name__}: {e}",
                    exc_info=True,
                )
                # skip the faulty KB and continue""",
         """            except Exception as e:
                _log_dense_error(kb_id, e)
                # skip the faulty KB and continue"""),
    ], "kbspam")

    print("2) provider/sources/ollama_embedding_source.py")
    patch(OLL, [
        ('\n@register_provider_adapter(\n    "ollama_embedding",',
         OLL_HELPER + '\n@register_provider_adapter(\n    "ollama_embedding",'),
        ("""        except aiohttp.ClientError as e:
            logger.error(f"[Ollama Embedding] Network error: {e}")
            raise""",
         """        except aiohttp.ClientError as e:
            _log_ollama_net_error(e)
            raise"""),
    ], "kbspam")

    print("\n改完要**重启 AstrBot 后端**才生效。")
    print("还原：python patch_kb_log_spam.py --revert")


if __name__ == "__main__":
    main()
