# -*- coding: utf-8 -*-
"""unify_seia.py —— 把「圣亚」「圣亜」统一成官方简中的「圣娅」

## 为什么要统一

QQ 提示词的称呼表已经写明「⚠️ 是「圣**娅**」不是「圣亚」」，
`knowledge/dialogue-corpus.md` 也标了官方简中口径。
但项目里三种写法混着：`圣亚` / `圣娅` / `圣亜`（日文异体字）。
结果同一个角色在不同记忆文件里叫不同名字，检索时会分裂成三簇。

## 映射规则

   圣亜ちゃん  →  小圣娅          （日文爱称转中文爱称；称呼表里就是「小圣娅」）
   圣亜        →  圣娅
   圣亚        →  圣娅

⚠️ **不碰 `圣娅`**（已经是目标写法）。
⚠️ 有「ちゃん」的地方必须**先**处理，否则会被 `圣亜→圣娅` 抢先，
   留下一个不中不日的「圣娅ちゃん」。

## 用法

    <python> unify_seia.py            # 预演
    <python> unify_seia.py --apply    # 真的改（改前自动备份）
"""
from __future__ import annotations

import argparse
import datetime
import pathlib
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")

B = pathlib.Path(r"C:\OneDrive\MikaMisono")
BAK = B / "_archive-20260924"

# 只扫"活"的提示词与记忆文件；归档、对话备份、node_modules 不动
ROOTS = [B / "agent", B / "qq-bot", B / "persona-merge", B / "misono-mika-csp"]
SKIP_PARTS = {"node_modules", "_conversation-backup", "_live-persona-backup",
              "_archive-20260924", ".git", "__pycache__", "index"}
# ⚠️ 这几个文件**必须跳过**：
#   · unify_seia.py 本身——它的替换规则里就含那两个字，不排除就会改自己
#   · apply_*.py / _apply_*.py / apply_chinese_names.py——**历史补丁脚本**。
#     它们记的是"当时做了什么"，把里面的字改掉，记录就失真了。
#     它们是日志，不是活配置。
SKIP_FILES = {"unify_seia.py", "apply_chinese_names.py"}
EXTS = {".md", ".json", ".mjs", ".py", ".txt"}

# ⚠️ 顺序很重要：带「ちゃん」的必须先处理，否则会被「圣亜→圣娅」抢先，
#    留下一个不中不日的「圣娅ちゃん」。
RULES = [
    ("圣亜ちゃん", "小圣娅"),
    ("圣亚ちゃん", "小圣娅"),
    ("圣亜", "圣娅"),
    ("圣亚", "圣娅"),
]


def _skip(p: pathlib.Path) -> bool:
    if any(x in p.parts for x in SKIP_PARTS):
        return True
    if p.name in SKIP_FILES:
        return True
    # 历史补丁脚本一律不改
    if p.suffix == ".py" and (p.name.startswith("apply_") or p.name.startswith("_apply_")):
        return True
    return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    hits = []
    for root in ROOTS:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file() or p.suffix not in EXTS:
                continue
            if _skip(p):
                continue
            try:
                t = p.read_text(encoding="utf-8")
            except Exception:
                continue
            if RULES[2][0] in t or RULES[3][0] in t:
                hits.append((p, t))

    print(f"命中 {len(hits)} 个文件\n")

    n_all = 0
    for p, t in hits:
        detail = []
        new = t
        for old, rep in RULES:
            n = new.count(old)
            if n:
                new = new.replace(old, rep)
                detail.append(f"{old}->{rep} ×{n}")
                n_all += n
        if new != t:
            rel = p.relative_to(B)
            print(f"  {rel}")
            print(f"      {' · '.join(detail)}")

    print(f"\n共 {n_all} 处替换")
    if not a.apply:
        print("\n（预演。加 --apply 才写。）")
        return

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = BAK / f"seia-unify-{stamp}"
    dst.mkdir(parents=True, exist_ok=True)
    for p, _ in hits:
        rel = p.relative_to(B)
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, out)
    print(f"\n✓ 已备份 {len(hits)} 个文件 -> {dst}")

    for p, t in hits:
        new = t
        for old, rep in RULES:
            new = new.replace(old, rep)
        if new != t:
            p.write_text(new, encoding="utf-8")
    print(f"✓ 已写入")

    # 回读校验
    left = 0
    for p, _ in hits:
        t = p.read_text(encoding="utf-8")
        left += t.count("圣亜") + t.count("圣亚")
    print(f"✓ 回读：剩余 圣亜/圣亚 {left} 处")


if __name__ == "__main__":
    main()
