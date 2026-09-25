#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""map_speakers.py —— 用剧情站的 students.json 自动补全「韩文说话人 → 中文」映射

`ba_speaker.SPEAKER_CN` 是手写的，只覆盖了主要角色。本脚本把语料里
**还没翻译的韩文说话人**列出来，并从 `students.json` 里找官方中文名对照，
生成一段可直接粘进 `SPEAKER_CN` 的代码。

用法：<python> map_speakers.py
"""
from __future__ import annotations

import collections
import json
import pathlib
import re

import httpx

import ba_speaker as bs

ROOT = pathlib.Path(r"C:\OneDrive\MikaMisono\assets\story-cn")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}

# 一眼能看懂的角色类名（非学生姓名），直接手写
ROLE_CN = {
    "학생": "学生", "학생 A": "学生 A", "학생 B": "学生 B",
    "학생 C": "学生 C", "학생 D": "学生 D", "학생 간부": "学生干部",
    "전원": "全员", "일동": "全体",
    "불량배": "不良少年", "깡패": "混混",
    "시스터후드": "修女会", "시스터후드 간부": "修女会干部",
    "시스터후드 행정관": "修女会行政官", "시스터후드 분석관": "修女会分析官",
    "응급의학부원": "急救医学部成员",
    "선도부 의무관": "风纪委员会医务官", "유폐실 담당관": "禁闭室负责人",
    "경비원": "保安", "안내 방송": "广播", "아나운서": "播音员",
    "학생 기자": "学生记者",
    "티파티 감찰관": "茶会监察官", "티파티 호위부대장": "茶会护卫队长",
    "트리니티 학생": "三一学生", "게헨나 학생": "格黑娜学生",
    "트리니티 기숙사 사감 학생": "三一宿舍舍监学生",
    "아리우스 학생들": "阿里乌斯学生们",
    "온천 부원": "温泉部成员",
    "음험해보이는 학생": "看起来阴险的学生",
    "검은 양복": "黑西装", "검은 양복2": "黑西装２",
    "지하생활자": "地下生活者",
}


def suffix_rule(kr: str) -> str | None:
    """给「XXX A」「XXX 1」这类加后缀的杂兵名统一加后缀。"""
    m = re.match(r"^(.*?)\s*([A-Z0-9])$", kr)
    if not m:
        return None
    base = m.group(1)
    if base in bs.SPEAKER_CN:
        return f"{bs.SPEAKER_CN[base]} {m.group(2)}"
    if base in ROLE_CN:
        return f"{ROLE_CN[base]} {m.group(2)}"
    return None


def main() -> None:
    turns = json.loads((ROOT / "corpus" / "mika-turns.json").read_text(encoding="utf-8"))
    # 注意：要看**翻译后**的 speaker 还有没有韩文，而不是 speaker_kr
    #（speaker_kr 本来就该是韩文原值，按它筛会把已经翻译好的也算进来）
    speakers = collections.Counter(
        t["speaker_kr"] for t in turns if t["speaker_kr"] and
        re.search(r"[가-힣]", t["speaker"] or ""))
    todo = sorted(speakers, key=lambda k: -speakers[k])
    print(f"语料里还有 {len(todo)} 个未翻译的韩文说话人\n")

    c = httpx.Client(headers=UA, timeout=60, follow_redirects=True)
    students = c.get("https://preview.blue-archive.io/config/json/students.json").json()
    kr2cn: dict[str, str] = {}
    for st in students:
        name = (st.get("name") or {})
        fam = (st.get("familyName") or {})
        if name.get("kr"):
            # 只取「名」，和 SPEAKER_CN 里既有写法保持一致（花子 / 日富美 / 梓…）
            kr2cn[name["kr"]] = (name.get("cn")
                                 or fam.get("cn", "") + name.get("cn", ""))

    # 确定能认出来的非学生角色（数秘术成员 / AI 助手 / 无名杂兵前缀）
    EXTRA = {
        "골콩트": "戈尔孔达",
        "아로나": "阿罗娜",
        "복면호시노": "面具星野", "복면노노미": "面具野宫",
        "복면세리카": "面具芹香", "복면시로코": "面具白子",
        "통신아코": "通讯亚子", "통신아야네": "通讯绫音",
        "통신복면아야네": "通讯面具绫音",
    }

    resolved: dict[str, str] = {}
    unknown: list[tuple[str, int]] = []
    for kr in todo:
        if kr in ROLE_CN:
            resolved[kr] = ROLE_CN[kr]
        elif kr in kr2cn:
            resolved[kr] = kr2cn[kr]
        elif kr in EXTRA:
            resolved[kr] = EXTRA[kr]
        else:
            s = suffix_rule(kr)
            if s:
                resolved[kr] = s
            else:
                unknown.append((kr, speakers[kr]))

    print("── 可自动解析，直接生成代码 ──")
    for k, v in resolved.items():
        print(f'    "{k}": "{v}",   # {speakers[k]} 次')

    if unknown:
        print("\n── 需要人工确认（students.json 里没有或名字对不上）──")
        for k, n in unknown:
            # 模糊找同名片段
            cand = [f"{v}({kk})" for kk, v in kr2cn.items()
                    if k[:2] in kk or kk[:2] in k]
            print(f"    {k:<22} {n:>4} 次   候选: {', '.join(cand[:5]) or '无'}")

    out = ROOT / "_speaker-map-draft.py"
    out.write_text(
        "# 由 map_speakers.py 生成 —— 确认后并入 ba_speaker.SPEAKER_CN\n"
        "AUTO = {\n" +
        "".join(f'    "{k}": "{v}",\n' for k, v in resolved.items()) +
        "}\n", encoding="utf-8")
    print(f"\n→ 草稿写入 {out.name}")


if __name__ == "__main__":
    main()
