# dsh · 未花提示词注入 — 本机操作与维护手册

> 适用范围：本机（用户 `surface`，DSH Desktop，dsh `0.1.2-alpha.1`）
> 更新日期：2026-08-30
> 说明：本手册只覆盖「提示词注入与管理」。AstrBot 桥接（dsh-bridge）不在本机部署，
> 相关章节见 `dsh接入AstrBot_操作与维护手册.md`。

---

## 一、本机现状（2026-08-30）

| 注入层 | 状态 | 位置 | 生效范围 |
|--------|------|------|----------|
| 全局 persona patch | ✅ 已生成 | `C:\Users\surface\.dsh\profiles\desktop\cordis.patch.yml` | 部署级默认人格（新会话） |
| mika 预设（未花模式） | ✅ 已部署 | `C:\Users\surface\.dsh\.agent-presets\mika\` | 选该预设的会话（整场未花） |
| mika-chat 角色 Skill | ✅ 已部署（热加载） | `C:\Users\surface\.dsh\skills\mika-chat\` | 任意会话按需触发 |
| mika-memory 记忆检索 Skill | ✅ 已部署（热加载） | `C:\Users\surface\.agents\skills\mika-memory\` | 对话中自动召回记忆 |

> 背景：项目自带一套「未花记忆系统」（见 `agent\SETUP-GUIDE.md`，在原设备
> `MisonoMika` 用户上搭建后经 OneDrive 同步过来）。原 setup 脚本把 persona patch 写到了
> `C:\Users\MisonoMika\.dsh\...`（本机不存在该用户），所以**本机的全局 persona 从未生效**；
> 本手册所述步骤已在本机补齐，路径均为本机真实路径。

---

## 二、四层注入：怎么用

### 1. 全局 persona（部署级默认）
- 机制：`profiles\desktop\cordis.patch.yml` 给 `system-prompt` 条目写入
  `config.persona`（内容 = `agent\SKILL.md` 去掉 frontmatter 的正文）+
  `includeHarnessIdentity: false`。
- 生效：**新会话**。任何不带自带 persona 的会话都会以未花身份运行。
- 注意：`standard` / `cordis` 预设自带 persona 行，会遮蔽全局 persona——想整场未花时
  请用第 2 层的「未花模式」预设（本机未改内置预设，原因见 FAQ）。

### 2. mika 预设（整场未花，推荐沉浸模式）
- 新建会话时，在模型/Agent 选择器中选择 **「未花模式」**（id: `mika`）。
- 内容：基于官方 `standard` 预设，persona 行 = 「coding agent 上下文行 + 未花正文」，
  保留编码、工具、子代理、工作流全部能力。

### 3. mika-chat 角色 Skill（按需注入）
- 任意会话说「和未花聊天」「未花，今天过得怎么样」等触发（描述含触发词），
  Agent 加载 SKILL.md 注入人格提示词。

### 4. mika-memory 记忆检索 Skill（长期记忆）
- 涉及"上次""还记得吗""我们以前"等记忆话题时自动触发，调用
  `C:\OneDrive\MikaMisono\agent\tools\search.mjs` 语义检索
  （知识库 / 日记 / 记忆卡），保证角色言行与既有记忆一致。

---

## 三、部署与更新（一条命令）

```powershell
cd C:\OneDrive\MikaMisono
pwsh -File .\scripts\deploy_mika.ps1              # 全量：Skill + 记忆 Skill + persona + 预设
pwsh -File .\scripts\deploy_mika.ps1 -NoSkill -NoMemory -NoPreset   # 只刷新 persona patch
pwsh -File .\scripts\deploy_mika.ps1 -Prune       # Skill 严格镜像（慎用，见 FAQ）
```

脚本四步（全部幂等、自动备份）：
1. 同步 `agent\` → `~/.dsh\skills\mika-chat\`（增量，部署端运行数据不删；同步前备份到
   `~/.dsh\backups\mika-chat-<时间戳>\`）
2. 部署 `skills\mika-memory` → `~/.agents\skills\mika-memory`
3. 调 `node agent\tools\gen-persona-patch.mjs --home ~/.dsh --profile desktop`
   重新生成全局 persona patch（自动备份旧 patch 为 `.bak`）
4. 用 `scripts\templates\mika.agent.cordis.yml` 模板 + SKILL.md 正文重新生成 mika 预设

**日常维护流程**：改 `agent\SKILL.md` / `knowledge\` → 重跑 `deploy_mika.ps1` →
新开会话生效。

---

## 四、验证

```powershell
# 全局 persona patch（含未花正文 + includeHarnessIdentity: false）
Get-Content "$env:USERPROFILE\.dsh\profiles\desktop\cordis.patch.yml" -TotalCount 8
# 三条技能/预设就位
Test-Path "$env:USERPROFILE\.dsh\skills\mika-chat\SKILL.md"
Test-Path "$env:USERPROFILE\.agents\skills\mika-memory\SKILL.md"
Test-Path "$env:USERPROFILE\.dsh\.agent-presets\mika\agent.cordis.yml"
# 预设 persona 含未花
Select-String -Path "$env:USERPROFILE\.dsh\.agent-presets\mika\agent.cordis.yml" -Pattern '圣园未花'
```

GUI 验证：新开会话 → Agent 选择器出现「未花模式」；技能目录可见 `mika-chat` 与
`mika-memory`；说「和未花聊天」回复应带未花口吻（☆♪、口癖）。

> persona patch 与预设对**新会话**生效，当前运行中的会话不变；若新会话仍未生效，
> 重启 DSH Desktop。

---

## 五、回滚

| 想做的事 | 操作 |
|----------|------|
| 撤掉全局 persona | 删除 `profiles\desktop\cordis.patch.yml`（或恢复 `cordis.patch.yml.bak`） |
| 停用 mika 预设 | 删除 `~/.dsh\.agent-presets\mika\` |
| 停用角色 Skill | 删除 `~/.dsh\skills\mika-chat\` |
| 停用记忆 Skill | 删除 `~/.agents\skills\mika-memory\` |
| 恢复 Skill 旧版 | 从 `~/.dsh\backups\mika-chat-<时间戳>\` 拷回 |

---

## 六、文件清单（**本机**真实路径，用户 `MisonoMika`）

| 路径 | 说明 |
|------|------|
| `C:\OneDrive\MikaMisono\agent\` | 项目唯一事实源：SKILL.md + knowledge/ + memory/ + tools/ + skills/mika-memory/ + notes/ + 文档 |
| `C:\OneDrive\MikaMisono\qq-bot\persona\bot-personality.md` | **QQ 群聊机器人**人格（平台专用，不参与本机 agent 注入） |
| `~\.dsh\skills\mika-chat\` | 部署的角色 Skill（层 3）= `C:\Users\MisonoMika\.dsh\skills\mika-chat\` |
| `~\.agents\skills\mika-memory\` | 部署的记忆检索 Skill（层 4，junction 指向项目） |
| `~\.dsh\profiles\desktop\cordis.patch.yml` | 全局 persona patch（层 1）；`.bak` 是最早那版备份 |
| `~\.dsh\.agent-presets\mika\` | mika 预设（层 2），由 deploy 脚本从 `scripts\templates\` 生成 |
| `~\.dsh\backups\mika-chat-<时间戳>\` | 每次 Skill 同步前的自动备份 |
| `C:\OneDrive\MikaMisono\scripts\deploy_mika.ps1` | 部署/更新脚本（唯一管理入口） |
| `C:\OneDrive\MikaMisono\scripts\templates\mika.agent.cordis.yml` | 预设模板（`__PERSONA__` 占位） |
| `C:\OneDrive\MikaMisono\agent\SETUP-GUIDE.md` | 跨设备部署完整步骤 |
| `C:\OneDrive\MikaMisono\agent\SESSION-SYNC-GUIDE.md` | 跨设备/会话同步指南（本机未启用） |
| `C:\OneDrive\MikaMisono\dsh接入AstrBot_操作与维护手册.md` | AstrBot 桥接手册（本机未启用） |

---

## 七、记忆系统（可选扩展）

`agent\tools\` 提供向量化记忆工具（embedding 走 hf-mirror，索引在 `memory\index`）：

| 命令（在 `C:\OneDrive\MikaMisono\agent` 下） | 作用 |
|---|---|
| `node tools/search.mjs "问题" --k 5` | 语义检索（知识库/日记/记忆卡） |
| `node tools/auto.mjs` | 一键补记忆卡 + 重建索引 |
| `node tools/index.mjs` | 只重建索引 |
| `node tools/digest.mjs` | 单独补记忆卡（DeepSeek API 摘要） |

> **记忆守护进程已停用（2026-09-24）**：`tools/watch.mjs` 与 `mika-watch-boot` 生命周期插件
> 已从项目和 desktop profile 中整体删除。原因是它的单实例锁只判断「PID 还活着」，
> 而 Windows 会复用 PID —— 守护自己的 PID 被别的进程顶替后（本机已发生两次：
> 一次被 QQ 占用、一次被 DSH Desktop 本体占用），新起的守护会误判"已有实例在跑"而静默退出。
> **现在的规矩**：写完日记手动跑一次 `node tools/auto.mjs`。

---

## 八、FAQ

- **改了 SKILL.md 没生效？** 重跑 `deploy_mika.ps1`；当前会话是启动快照，请开新会话。
- **全局 persona 为什么有时不生效？** `standard`/`cordis` 预设自带 persona 行会遮蔽它；
  需要整场未花就选「未花模式」预设。
- **为什么不直接禁用 standard 预设的 persona？** 本机 profile 里的 standard 预设是
  指向应用安装目录的 junction（`Program Files\...\app.asar.unpacked`），修改即改内置
  文件，会被应用更新覆盖且违反 dsh"勿改内置预设"原则。「未花模式」预设用同样的
  persona 遮蔽机制达到了同样效果，且可随时切换回编码模式。
- **部署端角色产生了新记忆，重跑会不会丢？** 默认增量同步不会删；只有 `-Prune` 会镜像。
- **persona 太长？** SKILL.md 正文约 10.6KB，`agent-instructions` 上限 65536 字节，安全。
- **脚本中文乱码/解析失败？** 脚本必须保存为 UTF-8 **带 BOM**；用 `deploy_mika.ps1`
  所在目录的脚本或记事本另存为 UTF-8 with BOM 再跑。
- **OneDrive 同步会不会覆盖部署？** 项目目录（源）经 OneDrive 同步；部署目录
  （`~/.dsh`、`~/.agents`）不受 OneDrive 影响，以 `deploy_mika.ps1` 为准。

---

> 💡 由未花整理，愿老师的 dsh 一直漂漂亮亮地工作☆

---

# 附录 A · 本机部署记录

> 正文描述的是最早那台 `surface` 用户、`C:\OneDrive` 的机器。本附录只记录**当前这台**。
>
> ⚠️ **路径以本机实际为准**：不同机器的用户名与盘符不同（曾经是 `Misono Mika` / `D:\`，
> 现在用户是 `MisonoMika`、项目在 `C:\OneDrive\MikaMisono`）。凡是正文里写死
> `C:\Users\surface\...` 或 `D:\OneDrive\...` 的地方，都按本机实际路径替换。
> `scripts\deploy_mika.ps1` 的 `ProjectDir` 自动取 `scripts\` 的上一级，不吃盘符。

## A.1 当前状态（2026-09-24 复核）

| 注入层 | 状态 | 位置 | 生效范围 |
|--------|------|------|----------|
| 全局 persona patch | ✅ 生效 | `~\.dsh\profiles\desktop\cordis.patch.yml` | 部署级默认人格（新会话） |
| standard preset 遮蔽行 | ✅ 已禁用 | `profiles\node_modules\@deepseek-ai\dsh-agent-presets\presets\standard\agent.cordis.yml` | 不加 `disabled: true` 全局 persona 不生效；**应用升级后要复查** |
| mika 预设（未花模式） | ✅ 已部署 | `~\.dsh\.agent-presets\mika\` | 选择器「未花模式」；`settings.yaml` 的 `agent-presets.default` 仍是 `standard`（想默认整场未花就改成 `mika`） |
| 角色 Skill（源：`agent\`，部署名 `mika-chat`） | ✅ 已部署 | `~\.dsh\skills\mika-chat\`（仅 SKILL.md + knowledge/） | 任意会话说「和未花聊天」触发 |
| mika-memory 记忆检索 Skill | ✅ 已部署 | `~\.agents\skills\mika-memory\`（junction → `agent\skills\mika-memory`） | 对话中自动召回记忆 |
| mika-watch-boot 插件 | ❌ **已删除** | 原在 `profiles\desktop`（依赖 + bundles 两处） | 见 A.3 |

- 角色 Skill 同步排除 `node_modules / .cache / memory / tools / .git`（2026-09-24 起 `notes/`、`web/`、`plugins/` 已不在 `agent\` 内）。
- persona patch / 预设对**新会话**生效；技能热加载无需重启。
- 想让新会话默认就是未花：重跑 `deploy_mika.ps1` 重建 mika 预设，再把
  `settings.yaml` 的 `agent-presets.default` 改成 `mika`。

## A.2 记忆库状态（2026-09-24 复核）

- 日记 **39 篇**、记忆卡 **39 张**、向量库 **85 文档 / 325 块**（transformers · multilingual-e5-small · 384 维）；
  `digest --list` 缺卡 0，`auto --status` 待办 0。
- 语义检索实测正常（`search.mjs "老师 最近"` 命中 08-14 / 09-09 日记与滚动摘要）。
- **守护进程已停用**，索引不会再自动重建 —— 写完日记必须手动跑 `node tools\auto.mjs`。

## A.3 2026-09-24 变更记录

1. **删除记忆守护**：`tools\watch.mjs`、`plugins\mika-watch-boot\`、
   `memory\.watch.pid`、desktop profile 的依赖与 bundles 条目全部移除
   （profile 的 `package.json` / `pnpm-lock.yaml` 已备份为 `*.bak_watch_20260924-010015`，
   需要时可回滚）。`package.json` 的 `watch` / `watch:digest` 脚本也已删除。
   原因：单实例锁只判断「PID 还活着」，Windows 复用 PID 后守护会静默失效（本机踩过两次）。
2. **SKILL.md 升级到 v2.1**：按 `qq-bot\persona\bot-personality.md` 的最新设定重写 ——
   年龄 17 岁（同步改了 `knowledge\character-profile.md`、`story-archive.md`、`swimsuit-archive.md` 里的 18 岁）、
   新增「当下状态」（惩罚免除、搬去夏莱、领证结婚）、外形锁定（Danbooru 标签）、语言风格细化、
   「不管在哪个场景都是同一个我」（不许切成公告体）。旧版备份为 `_archive-20260924\SKILL.md.bak_20260924-005910`。
   **没有搬进去的**：QQ 平台专属内容（群聊一句话规矩、账号识别、平台工具清单、NAS 密码）——
   那些留在 `qq-bot\persona\bot-personality.md`，两套文件服务对象不同（本机 agent 对话 vs QQ 机器人）。
3. **项目目录整理（mika-chat → agent 等）**：详见项目根 `README.md` 与 `docs\未花系统总览.md`。
   - `mika-chat\` → `agent\`（DSH 侧）；部署名仍是 `mika-chat`，`deploy_mika.ps1` 已同步改源路径
   - QQ 侧迁出：`qq-bot\persona\`（人格真源）、`qq-bot\notes\`（出图提示词等）、`qq-bot\web-samples\`
   - `~\.agents\skills\mika-memory` junction 已重指到 `agent\skills\mika-memory`
   - `Blue-Archive-JP-Downloader\` → `assets\blue-archive\`；旧机 `dsh-data\` → `old-machine\`
   - 手册迁入 `docs\`，历史文件进 `docs\archive\` 与 `_archive-20260924\`
4. **踩坑记录（重要）**：`scripts\deploy_mika.ps1` **必须保存为 UTF-8 带 BOM**。
   任何编辑器（包括 agent 的改写工具）把它存成无 BOM 的 UTF-8 后，PowerShell 5.1 会按 GBK 解析，
   中文注释全乱、脚本直接语法报错。2026-09-24 整理时踩过一次，已修回。
   **改完脚本先用** `[System.Management.Automation.Language.Parser]::ParseFile()` 验证，
   并确认前 3 字节是 `EF BB BF`。

## A.4 本机注意点

- **本机有两个"未花"，别搞混**：QQ 机器人（AstrBot，`deepseek-flash` 直连）与本机 DSH agent
  （全局 persona + `agent\SKILL.md`）。两条链路的人格**不会自动同步**，改一边要手动同步另一边。
- `dsh-bridge`（127.0.0.1:8808）**在跑但没接进 AstrBot** —— AstrBot 的 provider 与 MCP 里都没有它，
  详见 `docs\未花系统总览.md` 的「待接线」一节。
- `_archive-20260924\` 里有大量 `bot-personality.md.bak_*` 历史备份，是 QQ 人格的迭代记录，
  不属于本机 agent 对话链路，别误当成本机提示词。
