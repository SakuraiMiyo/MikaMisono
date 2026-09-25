#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""restore_machine.py —— 在新机器上把仓库快照恢复成可运行状态

## 前置（哪些不能自动化，见 docs/部署手册.md 第 0 节）

- AstrBot Desktop v4.27.3 已装在 C:\\SoftWare\\Astrbot（推荐旧机整目录拷贝）
- 本仓库 clone 在 C:\\OneDrive\\MikaMisono（路径 relocating 见手册第 0.3 节）
- deploy/secrets.local.json 已从旧机拷来（或手填）
- 后端正在运行（start_backend_desktop_env.ps1），面板 API 可达

## 用法

    & 'C:\\SoftWare\\Astrbot\\backend\\python\\python.exe' deploy\\restore_machine.py

步骤全部幂等。跑完按手册第 5 节做外部依赖核验。
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
    print(f"✗ 无法导入 persona_api: {exc}")
    sys.exit(1)

REPO = pathlib.Path(__file__).resolve().parent.parent
SNAP = REPO / "deploy" / "snapshot"
SECRETS = REPO / "deploy" / "secrets.local.json"
DATA = pathlib.Path.home() / ".astrbot" / "data"

ok = True


def step(name):
    print(f"\n── {name}")


def warn(msg):
    global ok
    ok = False
    print(f"  ✗ {msg}")


def good(msg):
    print(f"  ✓ {msg}")


def main() -> None:
    # ── 1. 技能 ────────────────────────────────────────────────────────
    step("恢复技能实体 → ~/.astrbot/data/skills/")
    src = SNAP / "skills"
    if not src.is_dir():
        warn("快照缺 skills/（先在旧机跑 snapshot_machine.py）")
    else:
        n = 0
        for d in src.iterdir():
            if d.is_dir():
                dest = DATA / "skills" / d.name
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(d, dest)
                n += 1
        good(f"恢复 {n} 个技能")

    # ── 2. EXTRA_PROMPT ───────────────────────────────────────────────
    step("恢复会话工作区 EXTRA_PROMPT")
    ep_dir = SNAP / "extraprompt"
    if not ep_dir.is_dir() or not any(ep_dir.iterdir()):
        warn("快照缺 extraprompt/（可跳过，但活跃会话少了加固规则）")
    else:
        n = 0
        for f in ep_dir.glob("*.md"):
            ws = DATA / "workspaces" / f.stem
            ws.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, ws / "EXTRA_PROMPT.md")
            n += 1
        good(f"恢复 {n} 份 EXTRA_PROMPT")

    # ── 3. cmd_config.json（快照 + 密钥合并，保 BOM）────────────────────
    step("恢复 cmd_config.json（快照 + secrets.local 合并）")
    cfg_path = SNAP / "cmd_config.json"
    if not cfg_path.exists():
        warn("快照缺 cmd_config.json")
    elif not SECRETS.exists():
        warn("缺 deploy/secrets.local.json —— 从旧机拷来或手填后重跑")
    else:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        secrets = json.loads(SECRETS.read_text(encoding="utf-8"))
        for seg, content in secrets.items():
            if isinstance(content, dict) and isinstance(cfg.get(seg), dict):
                cfg[seg].update(content)
            else:
                cfg[seg] = content
        # BOM 必须保留（AstrBot 读写都带 BOM；不带会有隐患）
        (DATA / "cmd_config.json").write_bytes(
            b"\xef\xbb\xbf" + json.dumps(cfg, ensure_ascii=False, indent=2).encode("utf-8"))
        good("cmd_config.json 已写入（BOM 保留）")
        # 立即自检：不带 utf-8-sig 能否读——能读说明 BOM 丢了
        try:
            json.loads((DATA / "cmd_config.json").read_text(encoding="utf-8"))
            warn("BOM 校验：utf-8 直读成功 = BOM 丢失了，检查写入逻辑")
        except Exception:
            good("BOM 校验通过（必须 utf-8-sig 才能读）")

    # ── 4. 提醒：重启后端 ──────────────────────────────────────────────
    step("重启后端（流水线配置是启动时读的）")
    print("  手动：AstrBot Desktop 界面重启，或")
    print("  powershell -File C:\\SoftWare\\Astrbot\\backend\\start_backend_desktop_env.ps1")
    input("  重启完成后按回车继续…")

    # ── 5. 人格恢复（走面板 API；真源推送 + 快照字段回填）───────────────
    step("恢复线上人格")
    pj = SNAP / "personas.json"
    if not pj.exists():
        warn("快照缺 personas.json（旧机没跑 API 快照）——"
             "至少跑 persona_api.py prompt 推真源")
    else:
        try:
            items = json.loads(pj.read_text(encoding="utf-8"))
            live_name = None
            with client() as c:
                for item in items:
                    pid = item.get("persona_id") or item.get("name")
                    if not pid:
                        continue
                    body = {
                        "persona_id": pid,
                        "system_prompt": item.get("system_prompt"),
                        "begin_dialogs": item.get("begin_dialogs"),
                        "skills": item.get("skills"),
                        "tools": item.get("tools"),
                    }
                    body = {k: v for k, v in body.items() if v is not None}
                    r = c.put(f"{BASE}/personas/by-id", json=body)
                    if r.status_code < 300:
                        print(f"  ✓ 人格 {pid} 已恢复")
                    else:
                        warn(f"人格 {pid} 恢复失败：{r.status_code} {r.text[:120]}")
                cfgj = json.loads(
                    (pathlib.Path.home() / ".astrbot" / "data" / "cmd_config.json")
                    .read_text(encoding="utf-8-sig"))
                live_name = cfgj.get("provider_settings", {}).get("default_personality")
            print(f"  默认人格：{live_name}（真源推送：persona-merge/persona_api.py prompt）")
        except Exception as exc:  # noqa: BLE001
            warn(f"人格恢复异常：{exc}")

    # ── 6. 补丁 ────────────────────────────────────────────────────────
    step("打全部源码补丁（幂等）")
    subprocess.run([sys.executable, str(REPO / "deploy" / "apply_all_patches.py")])

    # ── 7. 后置核验清单 ────────────────────────────────────────────────
    step("剩余人工项（详见 docs/部署手册.md 第 5 节）")
    print("  □ Ollama 运行中 + ollama pull bge-m3 → mika_kb.py --sync --status")
    print("  □ NapCat/QQ 客户端连接（适配器「已连接」日志）")
    print("  □ ComfyUI @127.0.0.1:8188（Manager 离线模式！见 mika-image skill）")
    print("  □ GPT-SoVITS @192.168.2.20:9880（NAS）")
    print("  □ 计划任务 MikaDiaryKBSync（每 30 分钟 --sync-diary）")
    print("  □ persona_api.py check 三方一致 / check_timeline.py 全绿")

    print("\n" + ("恢复完成 ✓（还有上面的人工项）" if ok else "有 ✗ 项，往上翻。"))


if __name__ == "__main__":
    main()
