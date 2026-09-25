# -*- coding: utf-8 -*-
import pathlib, hashlib, json, sys
B = pathlib.Path(r"C:\OneDrive\MikaMisono")
a = B/"qq-bot"/"persona"/"bot-personality.md"
b = B/"persona-merge"/"qq-bot-personality.merged.md"
c = B/"agent"/"SKILL.md"
d = B/"persona-merge"/"agent-SKILL.merged.md"
for p in (a,b,c,d):
    t = p.read_text(encoding="utf-8")
    h = hashlib.md5(t.encode("utf-8")).hexdigest()[:12]
    print(f"{len(t):>7} chars  md5={h}  sensei={t.count('sensei'):<3} {p.relative_to(B)}")
print("QQ 真源==镜像 :", a.read_text(encoding="utf-8")==b.read_text(encoding="utf-8"))
print("DSH 真源==镜像:", c.read_text(encoding="utf-8")==d.read_text(encoding="utf-8"))
print()
# 全部预设对话文件里的 sensei / 破绽
for f in sorted((B/"persona-merge").glob("*")):
    if f.suffix in (".md",".json") and "begin_dialogs" in f.name or f.name.startswith("预设对话"):
        t = f.read_text(encoding="utf-8")
        print(f"{len(t):>7}  sensei={t.count('sensei')}  {f.name}")
print()
# 线上 persona
cfg = pathlib.Path(r"C:\Users\MisonoMika\.astrbot\data\cmd_config.json")
j = json.loads(cfg.read_text(encoding="utf-8-sig"))
name = j.get("provider_settings",{}).get("default_personality")
print("live persona:", name)
print("  default_provider_id:", j.get("provider_settings",{}).get("default_provider_id"))
print("  max_context_length:", j.get("provider_settings",{}).get("max_context_length"))
print("  buffer_intermediate:", j.get("provider_settings",{}).get("buffer_intermediate_messages"))
# 找 persona 文件
import glob
hits = glob.glob(r"C:\Users\MisonoMika\.astrbot\data\**\*未小花*.json", recursive=True)
for h in hits:
    try:
        pj = json.loads(pathlib.Path(h).read_text(encoding="utf-8-sig"))
    except Exception as e:
        print("  skip", h, e); continue
    if isinstance(pj, dict) and pj.get("name")==name:
        sp = pj.get("prompt","")
        bd = pj.get("begin_dialogs") or []
        print(f"  live system_prompt = {len(sp)} chars  sensei={sp.count('sensei')}  begin_dialogs={len(bd)}  skills={pj.get('skills')}")
        print("  真源==线上 :", sp == a.read_text(encoding="utf-8"))
