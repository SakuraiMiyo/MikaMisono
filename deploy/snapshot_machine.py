#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""snapshot_machine.py —— 把「机器本地态」 harvest 进仓库 deploy/snapshot/

## 为什么需要

仓库里是真源（提示词/语料/脚本），但一台能跑的她还需要四类**机器本地态**：

1. `~\\.astrbot\\data\\skills\\` 的技能实体（mika-* 等，线上孤本）
2. `~\\.astrbot\\data\\workspaces\\_*/EXTRA_PROMPT.md`（会话级加固规则）
3. `~\\.astrbot\\data\\cmd_config.json`（provider/platform/segmented_reply/KB 等全部运行配置）
4. 线上人格（system_prompt + begin_dialogs + skills + tools —— 校验真源==线上之后可从真源重建，
   但 begin_dialogs 等字段真源里没有，快照最稳）+ 已安装插件清单

这些不在 git 里，换机就丢。本脚本把它们收进 `deploy/snapshot/`（提交到仓库），
密钥单独拆到 `deploy/secrets.local.json`（**已 gitignore**，换机时手动拷）。

## 用法（在本机跑）

    & 'C:\\SoftWare\\Astrbot\\backend\\python\\python.exe' deploy\\snapshot_machine.py

跑完 review 一下 diff 再提交。secrets.local.json 不入库——换机后从旧机拷或手填。
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")

try:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "persona-merge"))
    from persona_api import BASE, client  # noqa: E402
except Exception as exc:  # noqa: BLE001
    print(f"✗ 无法导入 persona_api（要在仓库里跑）: {exc}")
    sys.exit(1)

REPO = pathlib.Path(__file__).resolve().parent.parent
SNAP = REPO / "deploy" / "snapshot"
DATA = pathlib.Path.home() / ".astrbot" / "data"

# cmd_config.json 里属于密钥的字段（拆到 secrets.local.json，不入库）
SECRET_PATHS = [
    ("provider_sources", None),  # 整段含 key（各 provider 的 api key）
    ("dashboard", "jwt_secret"),
    ("dashboard", "pbkdf2_password"),
    ("dashboard", "password"),
]

SKILL_WHITELIST_PREFIX = ("mika-", "comfyui-node", "skill-thesis")


def main() -> None:
    SNAP.mkdir(parents=True, exist_ok=True)
    (SNAP / "skills").mkdir(exist_ok=True)
    (SNAP / "extraprompt").mkdir(exist_ok=True)

    # ── 1. 技能实体 ────────────────────────────────────────────────────
    n = 0
    for skill_dir in (DATA / "skills").iterdir():
        if not skill_dir.is_dir():
            continue
        if not skill_dir.name.startswith(SKILL_WHITELIST_PREFIX):
            continue
        dest = SNAP / "skills" / skill_dir.name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(skill_dir, dest)
        n += 1
    print(f"✓ 技能快照 {n} 个 → deploy/snapshot/skills/")

    # ── 2. EXTRA_PROMPT ───────────────────────────────────────────────
    n = 0
    ws_root = DATA / "workspaces"
    for ws in ws_root.iterdir():
        ep = ws / "EXTRA_PROMPT.md"
        if ws.is_dir() and ep.exists():
            shutil.copy2(ep, SNAP / "extraprompt" / f"{ws.name}.md")
            n += 1
    print(f"✓ EXTRA_PROMPT 快照 {n} 份 → deploy/snapshot/extraprompt/")

    # ── 3. cmd_config.json（密钥拆分）─────────────────────────────────
    raw = (DATA / "cmd_config.json").read_bytes()
    cfg = json.loads(raw.decode("utf-8-sig"))
    secrets: dict = {}
    for seg, key in SECRET_PATHS:
        if seg not in cfg:
            continue
        if key is None:
            secrets[seg] = cfg[seg]
            cfg[seg] = {}  # 占位：类型保留，内容清空
        elif isinstance(cfg.get(seg), dict):
            secrets.setdefault(seg, {})
            secrets[seg][key] = cfg[seg].get(key)
            cfg[seg].pop(key, None)  # 从快照里删掉（只复制不删除等于白拆）
    (SNAP / "cmd_config.json").write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    sl = REPO / "deploy" / "secrets.local.json"
    sl.write_text(json.dumps(secrets, ensure_ascii=False, indent=2), encoding="utf-8")
    print("✓ cmd_config 快照（密钥已拆出）→ deploy/snapshot/cmd_config.json")
    print(f"✓ 密钥（不入库）→ deploy/secrets.local.json  ← 换机时手动拷这个")

    # ── 4. 线上人格 + 插件清单（走面板 API）────────────────────────────
    try:
        with client() as c:
            r = c.get(f"{BASE}/personas")
            personas = r.json().get("data", {})
            items = personas.get("list", personas) if isinstance(personas, dict) else personas
            if isinstance(items, dict):
                items = list(items.values())
            (SNAP / "personas.json").write_text(
                json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"✓ 线上人格快照 {len(items)} 个 → deploy/snapshot/personas.json")

            r2 = c.get(f"{BASE}/plugins")
            pdata = r2.json().get("data", {})
            plist = pdata.get("list", pdata) if isinstance(pdata, dict) else pdata
            slim = [
                {"name": p.get("name"), "enabled": p.get("enabled"),
                 "version": p.get("version"), "repo": p.get("repo")}
                for p in plist if isinstance(p, dict)
            ]
            (SNAP / "plugins_installed.json").write_text(
                json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"✓ 插件清单快照 {len(slim)} 条 → deploy/snapshot/plugins_installed.json")
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ 面板 API 不可达（后端没跑？）——人格/插件快照跳过：{exc}")

    print("\n完成。review 后提交：git add deploy && git commit && git push")


if __name__ == "__main__":
    main()
