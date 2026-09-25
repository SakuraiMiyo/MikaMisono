#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""discover_mika.py —— 全站发现：把「未花出场过的剧情」一篇不落找出来

## 思路

1. 从前端 bundle（`playerUtils-*.js`）里抽出官方剧情目录里**所有 story_id**。
2. 逐个试探三种 URL 模板，确定它属于 main / other / event 哪种、是否可取。
3. 用 `students.json` 拿到全部学生 id → `/story/favor/{id}/index.json` 拿到全部羁绊 groupId。
4. 下载每一篇，用 `ba_speaker.parse_speaker` 精确数出未花的台词数量。
5. 产出 `mika-story-index.json`（未花出场清单）与 `_all-story-index.json`（全站清单）。

## 用法

    <python> discover_mika.py            # 只做发现与索引（不落盘原文）
    <python> discover_mika.py --fetch    # 顺带把所有未花相关原文下到 raw/
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import pathlib
import re
import sys

import httpx

import ba_speaker as bs

ROOT = pathlib.Path(r"C:\OneDrive\MikaMisono\assets\story-cn")
RAW = ROOT / "raw"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
HOST = "https://preview.blue-archive.io"

# 本地已有的分类 → raw 子目录名
CAT_DIR = {"Vol.3": "Vol.3", "原版羁绊": "原版羁绊", "泳装羁绊": "泳装羁绊",
           "活动": "活动", "其他": "其他"}


def jsnum(s: str) -> int:
    if "e" in s:
        a, b = s.split("e")
        return int(a) * 10 ** int(b)
    return int(s)


def get_catalog_ids(c: httpx.Client) -> list[int]:
    html = c.get(HOST).text
    entry = re.search(r'src="(/assets/index-[A-Za-z0-9_\-]+\.js)"', html).group(1)
    idx = c.get(HOST + entry).text
    m = re.search(r"assets/(playerUtils-[A-Za-z0-9_\-]+\.js)", idx) or \
        re.search(r'"(\./playerUtils-[A-Za-z0-9_\-]+\.js)"', idx)
    js = c.get(f"{HOST}/assets/{m.group(1).lstrip('./')}").text
    return sorted({jsnum(x) for x in re.findall(r"story_id:(\d+(?:e\d+)?)", js)})


def get_favor_groups(c: httpx.Client) -> dict[int, dict]:
    """返回 {groupId: {student_id, student_cn}}"""
    students = c.get(f"{HOST}/config/json/students.json").json()
    out: dict[int, dict] = {}

    def probe(st: dict):
        sid = st["id"]
        try:
            r = c.get(f"{HOST}/story/favor/{sid}/index.json", timeout=30)
            if r.status_code != 200:
                return []
            j = r.json()
        except Exception:
            return []
        return [(a["groupId"], sid,
                 (st.get("name") or {}).get("cn", ""),
                 (st.get("familyName") or {}).get("cn", ""),
                 (a.get("title") or {}).get("TextCn", ""),
                 (a.get("title") or {}).get("TextJp", ""))
                for a in j.get("abstracts", [])]

    with cf.ThreadPoolExecutor(8) as ex:
        for res in ex.map(probe, students):
            for gid, sid, name, fam, tcn, tjp in res:
                out[gid] = {"student_id": sid, "student_cn": fam + name,
                            "title_cn": tcn, "title_jp": tjp}
    return out


def probe_url(c: httpx.Client, kind: str, sid: int):
    if kind in ("main", "other"):
        url = f"{HOST}/story/{kind}/{sid}.json"
    else:
        url = f"{HOST}/story/{kind}/{sid // 10 if False else int(str(sid)[:5])}/{sid}.json"
    try:
        r = c.get(url, timeout=40)
        if r.status_code != 200:
            return None
        j = r.json()
        if not isinstance(j, dict) or "content" not in j:
            return None
        return j
    except Exception:
        return None


def analyze(j: dict) -> dict:
    content = j.get("content", [])
    speakers: dict[str, int] = {}
    mika = 0
    mika_cjk = 0
    mika_variants: set[str] = set()
    for u in content:
        kr, cn, _ = bs.parse_speaker(u.get("ScriptKr") or "")
        tcn = (u.get("TextCn") or "").strip()
        if kr is None and bs.SENSEI_PREFIX.match(tcn):
            kr, cn = "선생", "老师"
        elif kr is None and bs.NARR_PREFIX.match(tcn):
            kr, cn = None, "旁白"
        elif kr is None and tcn:
            cn = "未知"
        if cn:
            speakers[cn] = speakers.get(cn, 0) + 1
        if bs.is_mika(kr):
            mika += 1
            mika_cjk += bs.cjk_len(tcn)
            mika_variants.add(kr)
    title = ""
    for u in content:
        t = (u.get("TextCn") or "").strip()
        if t:
            title = t.replace("\n", " ")[:48]
            break
    return {"units": len(content), "mika": mika, "mika_cjk": mika_cjk,
            "mika_variants": sorted(mika_variants),
            "speakers": dict(sorted(speakers.items(), key=lambda kv: -kv[1])[:14]),
            "title": title}


def save_raw(j: dict, cat: str, name: str) -> None:
    d = RAW / CAT_DIR.get(cat, "其他")
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.json").write_text(
        json.dumps(j, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> None:
    do_fetch = "--fetch" in sys.argv
    with httpx.Client(headers=UA, timeout=45, follow_redirects=True) as c:
        print("① 抽目录 story_id …")
        cat_ids = get_catalog_ids(c)
        print(f"   {len(cat_ids)} 个")

        print("② 试探 main / other / event …")
        tasks = [(k, i) for i in cat_ids for k in ("main", "other", "event")]
        found: list[tuple[str, int, dict]] = []

        def probe(pair):
            k, i = pair
            j = probe_url(c, k, i)
            return (k, i, j)

        with cf.ThreadPoolExecutor(8) as ex:
            for k, i, j in ex.map(probe, tasks):
                if j:
                    found.append((k, i, j))
        # main/other 优先（同一 id 命中的话）
        best: dict[int, tuple[str, int, dict]] = {}
        for k, i, j in found:
            if i not in best or {"main": 0, "other": 1, "event": 2}[k] < \
                    {"main": 0, "other": 1, "event": 2}[best[i][0]]:
                best[i] = (k, i, j)
        print(f"   可取 {len(best)} 篇")

        print("③ 扫羁绊（students.json → favor index）…")
        fav = get_favor_groups(c)
        print(f"   {len(fav)} 篇羁绊")

        # 组装清单
        index: list[dict] = []
        for i, (k, _, j) in sorted(best.items()):
            cat = "Vol.3" if k == "main" and 31000 <= i < 34000 else \
                  ("活动" if k == "other" else ("其他" if k == "other" else "其他"))
            rec = {"kind": k, "id": i, "cat": cat, **analyze(j)}
            index.append(rec)
            if do_fetch and rec["mika"] >= 0 and (k == "main" and 31000 <= i < 34000 or rec["mika"]):
                save_raw(j, cat, str(i))

        print("④ 扫羁绊内容 …")
        fav_ids = list(fav)
        fav_tasks = [(gid, int(str(gid)[:5]) if len(str(gid)) > 5 else gid)
                     for gid in fav_ids]

        def pf(t):
            gid, d = t
            return gid, probe_url(c, "favor", gid)

        fav_index: list[dict] = []
        with cf.ThreadPoolExecutor(8) as ex:
            for gid, j in ex.map(pf, fav_tasks):
                if not j:
                    continue
                info = fav.get(gid, {})
                cat = "泳装羁绊" if info.get("title_jp", "") and \
                    "水着" in info.get("title_jp", "") else "原版羁绊"
                # 用学生名判分类更稳：与羁绊标题无关，直接留原始信息
                rec = {"kind": "favor", "id": gid, "cat": "羁绊",
                       "student": info.get("student_cn", ""),
                       "student_id": info.get("student_id"),
                       **analyze(j)}
                fav_index.append(rec)
                if do_fetch and rec["mika"]:
                    name = f"{gid}_{info.get('title_cn','')}".replace("/", "_")
                    save_raw(j, "羁绊", name)

        all_index = {"main_other": index, "favor": fav_index}
        (ROOT / "_all-story-index.json").write_text(
            json.dumps(all_index, ensure_ascii=False, indent=1), encoding="utf-8")

        mika_main = [r for r in index if r["mika"] > 0]
        mika_fav = [r for r in fav_index if r["mika"] > 0]
        (ROOT / "mika-story-index.json").write_text(
            json.dumps({"main_other": mika_main, "favor": mika_fav,
                        "favor_meta": {str(k): v for k, v in fav.items()
                                       if fav_index and any(f["id"] == k and f["mika"] > 0
                                                            for f in fav_index)}},
                       ensure_ascii=False, indent=1), encoding="utf-8")

        print("\n" + "=" * 72)
        print(f"未花出场的主线/任务剧情：{len(mika_main)} 篇，"
              f"合计 {sum(r['mika'] for r in mika_main)} 句 / "
              f"{sum(r['mika_cjk'] for r in mika_main)} 汉字")
        for r in mika_main:
            print(f"   {r['kind']:<6}{r['id']:>7}  {r['mika']:>3}句/{r['mika_cjk']:>5}字  "
                  f"{r['title']}   {','.join(r['mika_variants'])}")
        print(f"\n未花出场的羁绊：{len(mika_fav)} 篇，"
              f"合计 {sum(r['mika'] for r in mika_fav)} 句 / "
              f"{sum(r['mika_cjk'] for r in mika_fav)} 汉字")
        for r in mika_fav:
            print(f"   {r['id']}  {r['student']:<10} {r['mika']:>3}句/"
                  f"{r['mika_cjk']:>5}字  {r['title']}")
        print(f"\n全部羁绊篇数（全站）：{len(fav_index)}")


if __name__ == "__main__":
    main()
