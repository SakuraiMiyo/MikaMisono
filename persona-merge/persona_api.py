#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""persona_api.py —— 通过 AstrBot 面板 API 读写人格（不直接动 SQLite）

## 为什么不用直连 DB

`data_v4.db` 是 WAL 模式且 AstrBot 正在跑，直接写容易踩到并发。
面板 API 走的是同一套 service 层，而且 `update_persona` 只更新**传了的字段**
（`sqlite.py:1120` `if system_prompt is not None`），所以只传 `begin_dialogs` 是安全的。

## 认证

`dashboard.jwt_secret` 签 HS256，payload `{"username": ..., "exp": ...}`。
（`.kb_session_token` 那个是知识库文件服务的专用 token，走不了这一套，会 401。）

用法：
    <python> persona_api.py backup          # 备份线上人格到 _live-persona-backup/
    <python> persona_api.py show            # 看当前 begin_dialogs
    <python> persona_api.py put             # 写入 预设对话.begin_dialogs.json
    <python> persona_api.py clear           # 清空 begin_dialogs（回滚用）
    <python> persona_api.py skills          # 看当前 skills 白名单
    <python> persona_api.py skills a b c    # 设为白名单；不带名字 = 恢复成 null（用全部）

⚠️ skills 的语义（`persona_mgr.py:428` + `astr_main_agent.py:580`）：
    null  = 使用**全部** workspace skills
    []    = 会被 `... or None` 折成 null，**所以设空列表等于没设**（这是个坑）
    [..]  = 白名单，只注入名单里的
  想让无关技能别污染 system_prompt，必须给一个**非空**白名单。
"""
from __future__ import annotations

import datetime
import json
import pathlib
import sys

import httpx
import jwt

HOME = pathlib.Path.home()
CONFIG = HOME / ".astrbot" / "data" / "cmd_config.json"
BASE = "http://127.0.0.1:6185/api/v1"
HERE = pathlib.Path(__file__).resolve().parent
BAK = HERE / "_live-persona-backup"

# ── 提示词真源与镜像（2026-09-26 钉死）───────────────────────────────
# 真源 = QQ 链路自己的原件；merged 只是给 build_master_prompt.py 读的镜像。
# 推人格时读真源、顺手写一遍镜像，两份就不会再分叉。
SOURCE = HERE.parent / "qq-bot" / "persona" / "bot-personality.md"
MIRROR = HERE / "qq-bot-personality.merged.md"

DIALOGS = HERE / "预设对话.begin_dialogs.json"


def _live_persona_name() -> str:
    """线上真正生效的人格名 —— 就是配置里的 provider_settings.default_personality。

    ⚠️ 2026-09-26 的教训：硬编码成 "未小花！"，而配置里默认的是 "未小花0924"，
    结果一整天改的那份**根本没上线**。这里改成现读配置。
    """
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
        name = cfg.get("provider_settings", {}).get("default_personality")
        if name:
            return name
    except Exception:
        pass
    return "未小花！"


PERSONA = _live_persona_name()


def client() -> httpx.Client:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
    d = cfg["dashboard"]
    tok = jwt.encode(
        {"username": d["username"],
         "exp": datetime.datetime.now(datetime.timezone.utc)
         + datetime.timedelta(hours=2)},
        d["jwt_secret"], algorithm="HS256")
    return httpx.Client(base_url=BASE, timeout=30,
                        headers={"Authorization": f"Bearer {tok}"})


def get(c: httpx.Client) -> dict:
    r = c.get("/personas/by-id", params={"persona_id": PERSONA})
    r.raise_for_status()
    return r.json()["data"]


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    c = client()

    if cmd == "backup":
        BAK.mkdir(parents=True, exist_ok=True)
        d = get(c)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        (BAK / f"persona-{PERSONA}-{stamp}.json").write_text(
            json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        (BAK / f"system_prompt-{stamp}.md").write_text(
            d.get("system_prompt") or "", encoding="utf-8")
        print(f"✓ 已备份人格「{PERSONA}」")
        print(f"  system_prompt {len(d.get('system_prompt') or '')} 字")
        print(f"  begin_dialogs {len(d.get('begin_dialogs') or [])} 条")
        print(f"  → {BAK}")

    elif cmd == "show":
        d = get(c)
        b = d.get("begin_dialogs") or []
        print(f"人格「{PERSONA}」  system_prompt {len(d.get('system_prompt') or '')} 字")
        print(f"begin_dialogs {len(b)} 条")
        for i, x in enumerate(b):
            print(f"  {i:>3} {'老师' if i % 2 == 0 else '未花'} | {x}")

    elif cmd == "put":
        b = json.loads(DIALOGS.read_text(encoding="utf-8"))["begin_dialogs"]
        assert len(b) % 2 == 0, f"条数必须为偶数，现在是 {len(b)}"
        r = c.put("/personas/by-id", json={"persona_id": PERSONA,
                                           "begin_dialogs": b})
        print("PUT ->", r.status_code)
        if r.status_code != 200:
            print(r.text[:500]); return
        d = get(c)
        got = d.get("begin_dialogs") or []
        print(f"✓ 写入完成，回读 {len(got)} 条")
        print(f"  system_prompt 仍为 {len(d.get('system_prompt') or '')} 字（未受影响）")
        print("  前 4 条：")
        for i, x in enumerate(got[:4]):
            print(f"    {i} {'老师' if i % 2 == 0 else '未花'} | {x}")

    elif cmd == "prompt":
        # 把**真源**（qq-bot/persona/bot-personality.md）作为 system_prompt 推上线。
        # ⚠️ 只传 system_prompt 一个字段——update_persona 只更新**传了的字段**
        #    （sqlite.py:1120 `if system_prompt is not None`），begin_dialogs / skills 不受影响。
        if not SOURCE.exists():
            print(f"✗ 找不到真源 {SOURCE}")
            return
        text = SOURCE.read_text(encoding="utf-8")
        # 顺手把镜像写一遍，保证 build_master_prompt.py 读到的是同一份
        if not MIRROR.exists() or MIRROR.read_text(encoding="utf-8") != text:
            MIRROR.write_text(text, encoding="utf-8")
            print(f"  （已同步镜像 {MIRROR.name}）")
        before = get(c)
        b_len = len(before.get("system_prompt") or "")
        r = c.put("/personas/by-id", json={"persona_id": PERSONA,
                                           "system_prompt": text})
        print("PUT ->", r.status_code)
        if r.status_code != 200:
            print(r.text[:500]); return
        d = get(c)
        got = d.get("system_prompt") or ""
        print(f"✓ system_prompt {b_len:,} → {len(got):,} 字")
        assert got == text, f"回读不一致（{len(got)} vs {len(text)}）"
        print(f"  begin_dialogs 仍为 {len(d.get('begin_dialogs') or [])} 条（未受影响）")
        print(f"  skills 仍为 {(d.get('skills') or [])!r}（未受影响）")

    elif cmd == "clear":
        r = c.put("/personas/by-id", json={"persona_id": PERSONA,
                                           "begin_dialogs": []})
        print("PUT ->", r.status_code)
        print("✓ 已清空（回滚）" if r.status_code == 200 else r.text[:300])

    elif cmd == "skills":
        names = sys.argv[2:]
        if not names:
            d = get(c)
            print(f"人格「{PERSONA}」 skills = {d.get('skills')!r}")
            print("（None = 使用全部 workspace skills；空列表会被折成 None，等于没设）")
            return
        r = c.put("/personas/by-id", json={"persona_id": PERSONA, "skills": names})
        print("PUT ->", r.status_code)
        if r.status_code != 200:
            print(r.text[:500]); return
        d = get(c)
        got = d.get("skills")
        print(f"✓ skills = {got!r}")
        assert got == names, f"回读不一致：期望 {names!r}，得到 {got!r}"
        print(f"  system_prompt 仍为 {len(d.get('system_prompt') or '')} 字（未受影响）")
        print(f"  begin_dialogs 仍为 {len(d.get('begin_dialogs') or [])} 条（未受影响）")

    elif cmd == "check":
        live = _live_persona_name()
        d = get(c)
        sp = d.get("system_prompt") or ""
        src = SOURCE.read_text(encoding="utf-8") if SOURCE.exists() else ""
        mir = MIRROR.read_text(encoding="utf-8") if MIRROR.exists() else ""
        print(f"配置默认人格（= 线上生效）：{live!r}")
        print(f"  真源 {SOURCE.name:<28} {len(src):>7,} 字")
        print(f"  镜像 {MIRROR.name:<28} {len(mir):>7,} 字")
        print(f"  线上 system_prompt{'':<20} {len(sp):>7,} 字")
        print(f"  线上 begin_dialogs{'':<21} {len(d.get('begin_dialogs') or []):>7} 条")
        print(f"  线上 skills：{d.get('skills')!r}")
        print()
        print(f"  真源 == 镜像        ：{src == mir}")
        print(f"  真源 == 线上 prompt ：{src == sp}")
        if src != sp:
            print("  ⚠️ 线上不是最新——跑一次 `persona_api.py prompt` 推上去")

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
