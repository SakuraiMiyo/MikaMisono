# -*- coding: utf-8 -*-
"""
verify_live_patches.py —— 不重启、不打扰她，从面板 API 侧核对"补丁真的进去了"

## 为什么不用"发条消息试试"
发消息会真的进群里/私聊里，她会回，老师会看到。做验证不该有副作用。

## 怎么验
`launch_backend` 把后端跑在 `C:\\SoftWare\\Astrbot\\backend\\app` 下，
所以 `app` 目录里的那几份源码**就是**运行中的代码（`launch_backend.py:289` 把 APP_DIR
插进 sys.path 首位）。这里做三件事：

1. **静态核对**：源码里那几处补丁标记文本在不在、`py_compile` 过不过。
2. **运行态核对**：进程的启动时间 vs 补丁文件的修改时间——
   启动晚于修改 = 这份代码已经被 import 进去了（Python 在 import 时就定死了，
   不存在"读的是旧版"这种情况）。
3. **配置核对**：`cmd_config.json` 里的 `llm_compress_instruction` 是不是新版。
   （流水线配置是**初始化时**读的，所以起步时间必须晚于配置改动时间。）

用法：<python> verify_live_patches.py
"""
from __future__ import annotations

import datetime
import json
import pathlib
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

APP = pathlib.Path(r"C:\SoftWare\Astrbot\backend\app")
MAIN_AGENT = APP / "astrbot" / "core" / "astr_main_agent.py"
KB_MGR = APP / "astrbot" / "core" / "knowledge_base" / "kb_mgr.py"
RETRIEVAL = APP / "astrbot" / "core" / "knowledge_base" / "retrieval" / "manager.py"
OLLAMA = APP / "astrbot" / "core" / "provider" / "sources" / "ollama_embedding_source.py"
RUNNER = APP / "astrbot" / "core" / "agent" / "runners" / "tool_loop_agent_runner.py"
STAGE = APP / "astrbot" / "core" / "pipeline" / "result_decorate" / "stage.py"
UPDATE_SVC = APP / "astrbot" / "dashboard" / "services" / "update_service.py"
CFG = pathlib.Path.home() / ".astrbot" / "data" / "cmd_config.json"
PY = r"C:\SoftWare\Astrbot\backend\python\python.exe"

ok = True


def line(t=""):
    print(t)


line("=" * 66)
line("① 运行中的进程")
line("=" * 66)

ps = subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     "$ErrorActionPreference='SilentlyContinue';"
     "Get-CimInstance Win32_Process -Filter \"Name like '%python%'\" |"
     " Where-Object { $_.CommandLine -like '*launch_backend*' } |"
     " ForEach-Object { \"$($_.ProcessId)|$($_.CreationDate.ToString('o'))\" }"],
    capture_output=True, text=True)
start = None
for ln in (ps.stdout or "").splitlines():
    if "|" in ln:
        pid, iso = ln.split("|", 1)
        start = datetime.datetime.fromisoformat(iso.strip()).replace(tzinfo=None)
        line(f"  后端 PID {pid.strip()}　启动于 {start:%Y-%m-%d %H:%M:%S}")
if start is None:
    line("  ✗ 没找到后端进程")
    ok = False
line()

line("=" * 66)
line("② 源码补丁（静态核对）")
line("=" * 66)

PATCHES = [
    (MAIN_AGENT, "知识库注入抬头改成「你自己记得的事」", "# 你自己记得的事"),
    (MAIN_AGENT, "注入抬头补的正面形状", "像跟老师聊起一件旧事那样"),
    (MAIN_AGENT, "知识库工具常挂（两种模式不互斥）", "两种模式不再互斥"),
    (KB_MGR, "知识库片段抬头改成「你自己记得的东西」", "下面几段是你自己记得的东西"),
    (RETRIEVAL, "dense 错误日志节流", "_log_dense_error"),
    (OLLAMA, "Ollama 网络错误日志节流", "_log_ollama_net_error"),
    (RUNNER, "中间步骤正文封锁（治思考泄漏）", "带工具调用的中间步骤不产出正文"),
    (STAGE, "分段回复括号原子化", "split_text_respecting_brackets"),
    (UPDATE_SVC, "版本锁定（封死核心更新入口）", "版本已锁定在 v4.27.3"),
    (MAIN_AGENT, "此刻状态+时间线注入（emotion/timeline）", "_render_state_and_timeline_block"),
]

for p, label, marker in PATCHES:
    if not p.exists():
        line(f"  ✗ 找不到 {p.name}")
        ok = False
        continue
    t = p.read_text(encoding="utf-8", errors="replace")
    hit = marker in t
    mtime = datetime.datetime.fromtimestamp(p.stat().st_mtime)
    fresh = start is None or mtime < start
    flag = "✓" if hit else "✗"
    if not hit:
        ok = False
    line(f"  {flag} {label}")
    line(f"      {p.name}　改了 {mtime:%m-%d %H:%M:%S}　"
         f"{'在启动之前 → 已加载' if fresh else '⚠️ 晚于启动 → 还没加载，需重启'}　"
         f"标记{'命中' if hit else '缺失'}")

# 语法自检
line()
for p in (MAIN_AGENT, KB_MGR, RETRIEVAL, OLLAMA, RUNNER, STAGE, UPDATE_SVC):
    r = subprocess.run([PY, "-c",
                        f"import py_compile,sys; py_compile.compile(r'{p}', doraise=True)"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        line(f"  ✓ 语法 {p.name}")
    else:
        line(f"  ✗ 语法 {p.name}：{(r.stderr or '').strip()[:200]}")
        ok = False

line()
line("=" * 66)
line("③ 压缩指令（配置核对）")
line("=" * 66)

raw = CFG.read_bytes()
j = json.loads(raw.decode("utf-8-sig"))
ps_cfg = j["provider_settings"]
ci = ps_cfg.get("llm_compress_instruction", "")
cmtime = datetime.datetime.fromtimestamp(CFG.stat().st_mtime)
has_new = "留住语气" in ci and "未花" in ci
has_old = "produce a concise summary of key takeaways" in ci

line(f"  配置：{CFG}")
line(f"  改了 {cmtime:%m-%d %H:%M:%S}　BOM={raw[:3] == b'\xef\xbb\xbf'}")
line(f"  指令 {len(ci)} 字")
line(f"  {'✓' if has_new else '✗'} 是新版（含「留住语气」+「未花」）" if has_new
     else f"  ✗ 不是新版")
if has_old:
    line("  ✗ 还是内置那条英文通用指令")
    ok = False
if not has_new:
    ok = False
# ⚠️ 判据只用**内容**，不能用整个文件的 mtime 去推「流水线读没读到」——
#    cmd_config.json 会因为任何无关改动（启插件、切工具、改人格名）被 AstrBot
#    整个重写一遍，mtime 跟着变，于是这里会误报"需重启"。
#    真正有意义的判据是：**这条压缩指令的内容**最后一次变是什么时候。
#    内容对得上就是对的；实在要确认生效，去看日志里压缩那次实际用了什么 prompt。
if start and cmtime > start:
    line("  ⚠️ 配置文件在启动后被重写过（可能只是启插件/切工具的副作用）——")
    line("     这条指令的内容本身是新版，所以通常无需重启。要确认就看她压缩过一次之后的摘要里有没有留下语气。")
else:
    line("  ✓ 配置改动早于后端启动 → 流水线已读到")
line(f"  压缩 provider：{ps_cfg.get('llm_compress_provider_id')!r}　"
     f"保留最近比例：{ps_cfg.get('llm_compress_keep_recent_ratio')}")

line()
line("=" * 66)
line("④ 人格（每轮现读，不需要重启）")
line("=" * 66)
line(f"  默认人格：{ps_cfg.get('default_personality')!r}")
line(f"  system_prompt 由数据库现读 → 改完即时生效")
line(f"  当前长度（从真源看）："
     f"{len(pathlib.Path(r'C:\OneDrive\MikaMisono\qq-bot\persona\bot-personality.md').read_text(encoding='utf-8')):,} 字")

line()
line("=" * 66)
line(f"结论：{'全部通过 ✓' if ok else '有项目未通过 ✗'}")
line("=" * 66)
sys.exit(0 if ok else 1)
