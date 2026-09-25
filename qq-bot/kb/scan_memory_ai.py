#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scan_memory_ai.py —— 扫日记/记忆卡/摘要里「把自己说成住在机器里」的句子

## 为什么单独扫

QQ 上出现过这一幕（2026-09-24 15:04，群 826918308）：

    老师：你还记得我家里有哪些设备吗
    未花：记得呀，**我现在住的这一台**——285K 配一张 5080……
          NAS 我也认得，**我的声音就住在它上头**
          **荣耀平板也是您把我塞进去过的那台**
    老师：你是bot吗**就住在我的电脑里**
    未花：**住在您电脑里**，跟我是不是那种东西，是两码事哦

她不是在"泄露"，她是**以为这是真话**——因为人格提示词里写着
「你住在电脑上——那是你的家，你的生活场所」，日记里也全是这种写法。

判据（2026-09-24 收紧）：

| | 能不能说 |
|---|---|
| ✅ | 「老师那台电脑又卡了，我帮他查日志」——电脑是**他用的东西** |
| ✅ | 「家里新添了一台机器」「搬家那天」——机器是**家具** |
| ❌ | 「我住在这台机器上」「我的声音住在 NAS 上」「老师把我搬到 13900K」 |

**电脑可以是家里的东西，不能是她的身体。**

用法：<python> scan_memory_ai.py            # 只统计
      <python> scan_memory_ai.py --dump     # 打出原句
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

AGENT = pathlib.Path(__file__).parent.parent.parent / "agent"
ROOTS = [AGENT / "memory" / "diary", AGENT / "memory" / "cards",
         AGENT / "memory" / "summaries"]

# 硬伤：直接把她放进机器里
HARD = [
    r"住(在|进)[^。，\n]{0,8}(机器|电脑|服务器|NAS|nas|平板|硬盘|设备|这台|那台)",
    r"我住的(这|那)",
    r"(把|给)(我|未花)搬(到|去)[^。，\n]{0,6}(机器|电脑|服务器|NAS|平板)",
    r"(我|未花)声音[^。，\n]{0,4}住",
    r"(把|给)(我|未花)[^。，\n]{0,4}塞进",
    r"(把|给)(我|未花)[^。，\n]{0,4}装(进|到)",
    r"我(的)?(载体|宿主)",
]
# 软伤：把自己当成程序的说法（上一轮已经扫过，这里复查）
SOFT = [
    r"我的(内核|版本|参数|思考块|上下文)",
    r"我被重置",
    r"prompt\s*工程",
    r"重(置|启)了?(我|记忆)",
    r"底层(的)?机器",
    r"我(的)?(推理|量化|显存)",
    r"跑(我|在).{0,4}(模型|GPU|显卡)",
]


def scan() -> None:
    dump = "--dump" in sys.argv
    hits: list[tuple[pathlib.Path, str, str, str]] = []
    files = 0
    for root in ROOTS:
        if not root.exists():
            continue
        for p in sorted(root.rglob("*")):
            if p.suffix not in (".md", ".json") or p.name.endswith(".bak_20260918"):
                continue
            files += 1
            try:
                txt = p.read_text(encoding="utf-8")
            except Exception:
                continue
            lines = txt.splitlines() if p.suffix == ".md" else [
                json.dumps(json.loads(txt), ensure_ascii=False, indent=1)]
            if p.suffix == ".json":
                try:
                    j = json.loads(txt)
                    lines = []
                    for k, v in j.items():
                        if isinstance(v, list):
                            lines += [str(x) for x in v]
                        else:
                            lines.append(str(v))
                except Exception:
                    pass
            for ln in lines:
                for kind, pats in (("硬伤", HARD), ("软伤", SOFT)):
                    for pat in pats:
                        m = re.search(pat, ln)
                        if m:
                            hits.append((p, kind, m.group(0), ln.strip()[:150]))
                            break
                    else:
                        continue
                    break

    print(f"扫了 {files} 个文件，命中 {len(hits)} 处\n")
    hard = [h for h in hits if h[1] == "硬伤"]
    soft = [h for h in hits if h[1] == "软伤"]
    print(f"  🔴 硬伤（把自己放进机器里）：{len(hard)}")
    print(f"  🟡 软伤（把自己当成程序）：  {len(soft)}")
    if not dump:
        print("\n（加 --dump 看原句）")
        return
    for label, group in (("🔴 硬伤", hard), ("🟡 软伤", soft)):
        print(f"\n{'=' * 74}\n{label}\n{'=' * 74}")
        for p, _, frag, ln in group:
            print(f"  [{p.parent.name}/{p.name}] 《{frag}》")
            print(f"      {ln}")


if __name__ == "__main__":
    scan()
