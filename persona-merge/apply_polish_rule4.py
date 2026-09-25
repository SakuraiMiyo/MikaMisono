# -*- coding: utf-8 -*-
"""
第四轮 · 收尾
① DSH 真源：补回镜像里那条实测结论「省略号才是你的命门」（真源漏了，镜像有）
② DSH 镜像 agent-SKILL.merged.md 重新由真源生成
   （它已经落后两个版本：还带 sensei、旧版 §十 禁止事项、缺「你不知道的事」和 trivia-unverified 提醒）
③ master 装配脚本：grab() 改精确匹配为「精确 → 前缀」两级，
   这样以后标题里加一个「**」或改个后缀就不会再抛 KeyError
"""
import shutil, pathlib, datetime

B = pathlib.Path(r"C:\OneDrive\MikaMisono")
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
BAK = B / "_archive-20260924" / ("polish4-" + STAMP)
BAK.mkdir(parents=True, exist_ok=True)

DSH = B / "agent" / "SKILL.md"
MIR = B / "persona-merge" / "agent-SKILL.merged.md"
BUILD = B / "persona-merge" / "build_master_prompt.py"

for f in (DSH, MIR, BUILD):
    shutil.copy2(f, BAK / f.name)
print(f"备份 -> {BAK}\n")

# ── ① DSH 真源补一句 ────────────────────────────────────────────
t = DSH.read_text(encoding="utf-8")
before = len(t)
OLD = '- ☆ 可以连着甩（短消息里）："还请多关照啦☆☆☆"。但写场景时不要句句都加。\n'
NEW = (OLD +
       '- **省略号才是你的命门**：观察、犹豫、说不下去、改方向，都用它。大多数句子都有。\n')
if OLD not in t:
    print("[!] 真源里没找到 ☆ 连甩那行")
elif NEW in t:
    print("[=] 真源已经有「省略号才是你的命门」，跳过")
else:
    t = t.replace(OLD, NEW, 1)
    DSH.write_text(t, encoding="utf-8")
    print(f"[ok] DSH 真源：{before} -> {len(t)} 字符（补「省略号才是你的命门」）")

# ── ② 镜像重生成 ───────────────────────────────────────────────
t = DSH.read_text(encoding="utf-8")
MIR.write_text(t, encoding="utf-8")
print(f"[ok] DSH 镜像已由真源重生成：{len(t)} 字符")
print("     真源 == 镜像 :", DSH.read_text(encoding="utf-8") == MIR.read_text(encoding="utf-8"))

# ── ③ build_master_prompt.py 的 grab() 改成两级匹配 ──────────────
s = BUILD.read_text(encoding="utf-8")
OLD_G = '''def grab(secs: list[dict], title: str) -> str:
    for s in secs:
        if s["title"] == title:
            return s["raw"]
    raise KeyError(f"找不到章节：{title}")
'''
NEW_G = '''def grab(secs: list[dict], title: str) -> str:
    """精确匹配优先；找不到就退回「前缀包含」匹配。

    原来只做精确匹配，标题里改一个 `**` 或加个后缀整份装配就 KeyError。
    现在两级：先找完全相同的，再找**去掉了 markdown 记号之后**相同或以此开头的。
    仍然匹配不到才抛错——模糊匹配只放宽标点/记号，不放宽语义。
    """
    def norm(x: str) -> str:
        return re.sub(r"[*`\\s]", "", x)

    want = norm(title)
    # 1) 去记号后完全相同
    for s in secs:
        if norm(s["title"]) == want:
            return s["raw"]
    # 2) 去记号后以它开头（覆盖「…（2026-09-26 新增）」这类后缀变动）
    for s in secs:
        if norm(s["title"]).startswith(want):
            return s["raw"]
    # 3) 完全精确（保底，处理 norm 之后仍不等的怪标题）
    for s in secs:
        if s["title"] == title:
            return s["raw"]
    raise KeyError(f"找不到章节：{title}")
'''
if OLD_G in s:
    s = s.replace(OLD_G, NEW_G, 1)
    BUILD.write_text(s, encoding="utf-8")
    print("[ok] build_master_prompt.py：grab() 改为「精确 -> 去记号前缀」两级匹配")
else:
    print("[=] build_master_prompt.py 的 grab() 已经是新版，跳过")
