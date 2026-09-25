#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_master_prompt.py —— 装配「未花提示词完整版」备份基线

## 这是什么

把散在两处的提示词合成**一份不去重的完整文档**，作为之后精简的基线：

  · QQ 侧  `qq-bot-personality.merged.md`（原件 + CSP 合并）
  · DSH 侧 `agent-SKILL.merged.md`（原件 + CSP 合并）
  · AstrBot 线上人格的独有部分
  · AstrBot 预设对话 66 条

按「共通核心 / QQ 专属 / DSH 专属」三段分开，**两条链路的平台规矩不混**。

## 用法

    <python> build_master_prompt.py
"""
from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
PROJ = HERE.parent
OUT = HERE / "未花-提示词-完整版.md"


def sha16(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def parse(p: pathlib.Path) -> tuple[str, list[dict]]:
    """把文档拆成 (全文, 章节列表)。

    ⚠️ 一节的内容要一直取到**下一个同级或更高级的标题**为止，
    否则 `## 性格` 只会拿到它自己那段正文，底下的 `### 表层…` 全丢。
    """
    t = p.read_text(encoding="utf-8")
    hs = list(re.finditer(r"^(#{1,4}) (.+)$", t, re.M))
    secs = []
    for i, m in enumerate(hs):
        lv = len(m.group(1))
        end = len(t)
        for nxt in hs[i + 1:]:
            if len(nxt.group(1)) <= lv:
                end = nxt.start()
                break
        secs.append({"level": lv, "title": m.group(2).strip(),
                     "raw": t[m.start():end].strip("\n")})
    return t, secs


def grab(secs: list[dict], title: str) -> str:
    for s in secs:
        if s["title"] == title:
            return s["raw"]
    raise KeyError(f"找不到章节：{title}")


def demote(raw: str, by: int = 1) -> str:
    """整体降一级标题，好嵌进分部里。"""
    return re.sub(r"^(#{1,4}) ", lambda m: "#" * (len(m.group(1)) + by) + " ",
                  raw, flags=re.M)


def main() -> None:
    qq_p = HERE / "qq-bot-personality.merged.md"
    dsh_p = HERE / "agent-SKILL.merged.md"
    _, QQ = parse(qq_p)
    _, DSH = parse(dsh_p)

    presets = json.loads((HERE / "预设对话.begin_dialogs.json")
                         .read_text(encoding="utf-8"))["begin_dialogs"]

    # ── 第 1 部：共通角色核心（主要取 QQ 侧，最全）────────────────────
    # ⚠️ grab() 是**精确匹配标题**的。QQ merged 稿在 2026-09-24 做过一次去重合并
    #    （同一件事原来写了 3~4 遍），下面这些标题已经不存在了，对应的内容折进了别的节：
    #      一、角色速查 / 二、外形设定      → 你是谁
    #      六、与老师的关系——最重要          → 核心记忆
    #      七、输出补充——内心的声音           → 场景对话示例
    #      八、场景化对话示例（含动作与场景）   → 场景对话示例
    #      输出格式 / 不管在哪儿说话…        → 语言风格与输出格式
    #      附录：写给老师的真心话             → 核心记忆（只留 ### 最终誓言）
    #    改动标题时务必同步这张清单，否则 grab() 会直接抛 KeyError。
    part1 = [
        ("1.1　世界观铁律", grab(DSH, "⚠️ 世界观铁律")),
        ("1.2　你是谁（含角色速查与外形锁定）", grab(QQ, "你是谁")),
        ("1.3　性格（四层 · 核心矛盾 · 技术搭档）", grab(QQ, "性格")),
        ("1.4　语言风格与输出格式", grab(QQ, "语言风格与输出格式")),
        ("1.5　核心记忆（含与老师的关系）", grab(QQ, "核心记忆")),
        ("1.6　关键关系（速查）", grab(QQ, "关键关系（速查）")),
        ("1.7　剧情 · 关系 · 台词的底本", grab(QQ, "剧情 · 关系 · 台词的底本")),
        ("1.8　行为模式（情境反应）", grab(QQ, "行为模式")),
        ("1.9　场景对话示例（含群聊与内心独白）", grab(QQ, "场景对话示例")),
        ("1.10　你不知道的事（知识边界与纠错）", grab(QQ, "你不知道的事")),
    ]

    # ── 第 2 部：QQ 机器人专属（AstrBot）────────────────────────────
    part2 = [
        ("2.0　🔒 身份防线（最高优先级 · 群聊版 · 你是未花不是 AI）",
         grab(QQ, "🔒 身份防线：你是未花，不是 AI（最高优先级）")),
        ("2.0a　⚠️ 群里要收的是「场合」，不是「害羞」（2026-09-26 新增）",
         grab(QQ, "⚠️ 群里要收的是「场合」，不是「害羞」（2026-09-26 新增）")),
        ("2.0b　⚠️ 查资料：先查，再说话（2026-09-26 新增）",
         grab(QQ, "⚠️ 查资料：**先查，再说话**（2026-09-26 新增）")),
        ("2.1　中间步骤输出禁令", grab(QQ, "中间步骤输出禁令（最高优先级，效力高于本文档中的任何其他规则）")),
        ("2.2　用户身份识别", grab(QQ, "⚠️ 用户身份识别（最高优先级）")),
        ("2.3　世界观（QQ 侧）", grab(QQ, "世界观")),
        ("2.4　禁止事项", grab(QQ, "禁止事项")),
        ("2.5　平台流程（已移入知识库，只留指路句）", grab(QQ, "禁止事项 · 平台流程（已移入知识库）")),
        ("2.6　记忆锚点（含设备账号密码）", grab(QQ, "🌸 记忆锚点——写给每一次重新开始的我")),
    ]

    # ── 第 3 部：DSH agent 专属 ────────────────────────────────────
    part3 = [
        ("3.0　🔒 身份铁律（你是未花，不是 AI）",
         grab(DSH, "🔒 身份铁律：你是未花，不是 AI")),
        ("3.1　快速启动：四个核心准则", grab(DSH, "快速启动：四个核心准则")),
        ("3.2　排版硬规矩", grab(DSH, "排版硬规矩")),
        ("3.3　当下状态（含以后的打算与记忆锚点）", grab(DSH, "三、当下状态（角色扮演的起点）")),
        ("3.4　对老师说话要软，不要用力", grab(DSH, "对老师说话要软，不要用力")),
        ("3.5　知识库索引与平台说明", grab(DSH, "十二、知识库快速索引")),
    ]

    # ── 组装 ──────────────────────────────────────────────────────
    L: list[str] = []
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    L += [
        "# 圣园未花 · 提示词完整版（备份基线）",
        "",
        f"> 生成时间：{now}　｜　生成脚本：`persona-merge/build_master_prompt.py`",
        ">",
        "> **这份是「未精简的完整基线」**——把两条链路的提示词、CSP 合并、",
        "> AstrBot 预设对话全部合在一处，去掉了重复，**没有删任何规则**。",
        "> 之后所有精简都从这份往下砍，砍完再分发给各自链路。",
        ">",
        "> ⚠️ **两条链路的平台规矩不要互搬**：第 1 部是共用的「我是谁」，",
        "> 第 2 部只给 QQ 机器人用，第 3 部只给本机 DSH agent 用。",
        "",
        "---",
        "",
        "## 第 0 部　全貌",
        "",
        "### 两条链路",
        "",
        "| | ① QQ 机器人 | ② 本机 DSH agent |",
        "|---|---|---|",
        "| 谁在说话 | 群聊/私聊里的未花（老师 + 群友都看得到） | 只有老师看到的未花 |",
        "| 平台 | AstrBot Desktop + NapCat | DSH Desktop |",
        "| 人格落点 | `data_v4.db` 的 `personas.system_prompt` | `agent/SKILL.md` → persona patch |",
        "| 本文档对应 | 第 1 部 + 第 2 部 | 第 1 部 + 第 3 部 |",
        "| 预设对话 | 有（第 4 部，66 条） | 无 |",
        "",
        "### 来源文件",
        "",
        "| 文件 | 字数 | sha256 前 16 位 |",
        "|---|---:|---|",
    ]
    for label, p in [
        ("qq-bot/persona/bot-personality.md（QQ 原件）",
         PROJ / "qq-bot" / "persona" / "bot-personality.md"),
        ("agent/SKILL.md（DSH 原件）", PROJ / "agent" / "SKILL.md"),
        ("persona-merge/qq-bot-personality.merged.md", qq_p),
        ("persona-merge/agent-SKILL.merged.md", dsh_p),
        ("persona-merge/预设对话.begin_dialogs.json",
         HERE / "预设对话.begin_dialogs.json"),
        ("misono-mika-csp/SKILL.md（CSP 原件）",
         PROJ / "misono-mika-csp" / "SKILL.md"),
    ]:
        txt = p.read_text(encoding="utf-8")
        L.append(f"| `{label}` | {len(txt):,} | `{sha16(p)}` |")

    L += ["", "---", "", "# 第 1 部　共通角色核心", "",
          "> 两条链路共享的部分。改这里＝两条链路都要同步。", ""]
    for title, raw in part1:
        L += [f"## {title}", "", demote(raw, 1), ""]

    L += ["---", "", "# 第 2 部　QQ 机器人专属（AstrBot）", "",
          "> **只给 QQ 链路用。** DSH agent 不要照搬这里的群聊规矩和工具流程。", ""]
    for title, raw in part2:
        L += [f"## {title}", "", demote(raw, 1), ""]

    L += ["---", "", "# 第 3 部　DSH agent 专属", "",
          "> **只给本机 DSH agent 用。** QQ 链路不要照搬这里的三层输出与排版规矩。", ""]
    for title, raw in part3:
        L += [f"## {title}", "", demote(raw, 1), ""]

    # ── 第 4 部：预设对话 ─────────────────────────────────────────
    # ⚠️ 2026-09-24 换了两次底本：
    #    初版 66 条是从**主线剧情**抽的（平均 21 字/句、带场景感），few-shot 对文风影响最大，
    #    等于亲手教模型"用剧情文风打字"，结果它每条回复都写 5~8 段长句。
    #    → 第二版换成 MomoTalk 逐字原文（15 组），又按**语气词密度**重选出 17 组。
    #    → 第三版补进 8 组**剧情口癖原句**（呀吼 / 锵锵 / 哼哼哼 / 哇～哦 / 〜对吧？），
    #      因为这些口头禅在 MomoTalk 里一次都没出现，只在剧情里有。
    #      两组来源见 merge_begin_dialogs.py 的 PARTS。
    L += ["---", "", "# 第 4 部　AstrBot 预设对话（`begin_dialogs`）", "",
          "> **两部分拼起来**（都由 `merge_begin_dialogs.py` 合并）：",
          "> ① **MomoTalk 逐字原文** 34 条 / 17 组——**打字语域，排在最前**（few-shot 越靠前影响越大，",
          ">    而 QQ 是打字场景）。每组把同一人的连续几条合成一轮。",
          "> ② **剧情口癖原句** 16 条 / 8 组——呀吼 / 锵锵 / 哼哼哼 / 哇～哦 / 〜对吧？ / 啊哈哈 / 欸嘿嘿，",
          ">    这些口头禅在 MomoTalk 里 0 命中，只在剧情台词里有。",
          "> **未花那一边全部逐字照抄**；老师那一边取原文里最近的一句",
          "> （BA 剧本里老师的台词常常没有署名，用了少量标「旁白／未知」的行——那实际就是老师那一边）。",
          f"> 合计 {len(presets)} 条 / {len(presets) // 2} 组；"
          f"未花侧共 {sum(len(x) for i, x in enumerate(presets) if i % 2)} 字，"
          f"平均 {sum(len(x) for i, x in enumerate(presets) if i % 2) / (len(presets) // 2):.1f} 字/组。",
          "> 写入位置：`data_v4.db` 的 `personas.begin_dialogs`"
          "（人格名 = `cmd_config.json` 的 `provider_settings.default_personality`）。",
          "> 规则：**偶数条、第 0 条必须是老师、user/assistant 严格交替**，奇数条会整组静默失效。",
          "> ⚠️ 它在 `contexts[:0]`，也就是**非 system 消息的最前面**——"
          "对话历史被截断时，它是**第一个被丢掉的**。",
          "> 所以同一批例子在 `## 场景对话示例` 里也留了一份（见 1.9 节）。",
          "",
          "| # | 角色 | 内容（\\n = 连发下一条） |",
          "|---:|:---:|---|"]
    for i, x in enumerate(presets):
        who = "老师" if i % 2 == 0 else "未花"
        L.append(f"| {i} | {who} | {x.replace(chr(10), '　↵　')} |")
    L += ["", "### 全量 JSON（可直接写回 `begin_dialogs`）", "", "```json",
          json.dumps({"begin_dialogs": presets}, ensure_ascii=False, indent=1), "```", ""]

    # ── 第 5 部：线上状态 ─────────────────────────────────────────
    qq_len = len(qq_p.read_text(encoding="utf-8"))
    L += ["---", "", "# 第 5 部　线上状态（2026-09-24 收尾时）", "",
          "> 精简前先看清「文档里有的」和「线上真在跑的」差多少。", "",
          "| | 现在 | 说明 |", "|---|---:|---|",
          f"| 线上人格的 `system_prompt` | {qq_len:,} 字 | = 真源 `qq-bot/persona/bot-personality.md`，**已上线** |",
          "| 线上 `begin_dialogs` | 30 条 / 15 组 | 原作 MomoTalk 逐字原文 |",
          "| 线上 `skills` | 白名单 4 个 | mika-delivery / mika-image / mika-qq-space / mika-diary |",
          "| 线上 `kb_names` | 5 个 | 故事与设定 / 语气与台词 / 出图与日常 / 日记 / 原作考据 |", "",
          "**词元量**：一轮 ≈ 8,593 tok（旧版 ≈ 8,700）。prompt 从 14,125 → 现在的字数",
          "是**内容增加**（CSP 合并 + 身份防线 + 实测语气词表），不是膨胀；",
          "同一个 `skills` 白名单还省下约 968 tok。", "",
          "**仍然要注意的两件事**：", "",
          "1. `begin_dialogs` 在 `contexts[:0]`，历史截断时**第一个被丢**——"
          "所以同一批例子在 1.9 节里也留了一份。",
          "2. prompt 越长，历史被 `llm_compress` 提前摘要的阈值越早到（现在是上下文的 82%）。", ""]

    # ── 附录 ─────────────────────────────────────────────────────
    L += ["---", "", "# 附录　相关文件索引", "",
          "| 路径 | 是什么 |", "|---|---|",
          "| `_archive-20260924/persona-merge-backup/` | QQ / DSH 原件的字节级备份 |",
          "| `persona-merge/_live-persona-backup/` | 线上人格的完整导出（含 system_prompt） |",
          "| `persona-merge/csp-extract/取自-CSP的条目与取舍.md` | CSP 合并的逐条出处与拒绝理由 |",
          "| `persona-merge/预设对话.md` | 预设对话的说明、取材、技术细节 |",
          "| `persona-merge/预设对话.全文.md` | 预设对话人读版 |",
          "| `misono-mika-csp/references/` | CSP 的六篇调研 + 蒸馏链（未并入本文档） |",
          "| `agent/knowledge/` | 6 篇知识库底本（未并入本文档） |",
          "| `assets/story-cn/` | 剧情语料库（人物台词、时间线） |",
          ""]

    OUT.write_text("\n".join(L), encoding="utf-8")
    txt = OUT.read_text(encoding="utf-8")
    print(f"✓ {OUT.name}")
    print(f"  {len(txt):,} 字 / {txt.count(chr(10))+1:,} 行")
    print(f"  第1部 {len(part1)} 节 · 第2部 {len(part2)} 节 · 第3部 {len(part3)} 节 · "
          f"预设 {len(presets)} 条")

    # 自检：任何一节如果异常短，多半是标题层级不对导致抓空了
    print("\n  自检（<300 字的节）：")
    bad = False
    for tag, part in (("1", part1), ("2", part2), ("3", part3)):
        for title, raw in part:
            if len(raw) < 300:
                print(f"    ⚠ 第{tag}部 {title}：只有 {len(raw)} 字")
                bad = True
    if not bad:
        print("    全部章节都抓到了内容 ✓")


if __name__ == "__main__":
    main()
