# 圣园未花 · DSH 角色与记忆系统（agent/）

> ⚠️ **2026-09-24 起，本目录由 `mika-chat/` 改名而来**（部署到 DSH 的技能名仍是 `mika-chat`）。
> 项目总览见 [`../README.md`](../README.md)，系统接线图见 [`../docs/未花系统总览.md`](../docs/未花系统总览.md)。

《蔚蓝档案》圣园未花（聖園ミカ）的 **DSH agent 侧**实现：角色提示词（`SKILL.md`）+ 知识库 + 长期记忆向量化检索。

> 📦 **跨设备部署**：见 [SETUP-GUIDE.md](SETUP-GUIDE.md)。
> 🔧 **本机部署/更新**：`pwsh -File ..\scripts\deploy_mika.ps1`（唯一管理入口）。
> 🤖 **QQ 机器人那条链路不在这里**，见 [`../qq-bot/`](../qq-bot/)。

## 目录结构

```
agent/
├── SKILL.md                  # 角色提示词（唯一真源；deploy 脚本据此生成 persona 与预设）
├── SETUP-GUIDE.md            # 跨设备部署完整步骤
├── package.json              # Node 项目清单（嵌入引擎依赖）
├── config.json               # 向量库/摘要配置
├── knowledge/                # 角色知识库（6 个 .md，SKILL.md 引用）
├── memory/
│   ├── diary/                # 未花日记（按日期 YYYY-MM-DD.md）
│   ├── cards/                # 记忆卡（digest 生成，每篇日记一张 JSON）
│   ├── summaries/            # 滚动长期记忆摘要（memory.md）
│   └── index/                # 向量库产物（自动生成，勿手改）
├── tools/                    # 记忆工具（Node 脚本）
│   ├── index.mjs             # 构建/增量更新向量索引
│   ├── search.mjs            # 语义检索
│   ├── digest.mjs            # 日记 → 记忆卡（DeepSeek API）
│   ├── auto.mjs              # 一键：补记忆卡 + 重建索引
│   ├── gen-persona-patch.mjs # SKILL.md → DSH 全局 persona patch
│   ├── migrate-sessions.ps1  # 会话数据迁移（跨设备，本机未启用）
│   └── lib/                  # 嵌入/分块/存储实现
├── skills/mika-memory/       # 对话内自动召回 skill（junction 到 ~/.agents/skills）
└── .cache/                   # 嵌入模型缓存（自动生成，体积大）
```

> **不在本目录的东西**（2026-09-24 已迁出）：
> QQ 机器人人格与笔记 → `../qq-bot/`；网页小样 → `../qq-bot/web-samples/`；
> 会话同步指南 → `../docs/archive/SESSION-SYNC-GUIDE.md`；历史备份 → `../_archive-20260924/`。

## 三个命令

| 命令 | 作用 |
|---|---|
| `node tools/index.mjs` | 增量更新向量索引（新增/修改日记后运行；`--rebuild` 全量重建） |
| `node tools/search.mjs "问题"` | 语义检索知识库 + 记忆（可加 `--k 5`、`--scope knowledge\|diary\|card`、`--full`） |
| `node tools/digest.mjs` | 为没有记忆卡的日记生成记忆卡（DeepSeek API）；`--list` 查看缺哪些；`--date 2026-08-24` 指定日期 |

也可用 npm 别名：`npm run index` / `npm run search -- "问题"` / `npm run digest`。

## 自动化（两种）

### ① 一键流程 `node tools/auto.mjs`
一条命令完成：补记忆卡（跳过已有的）→ 增量重建索引 → 汇报。
`--status` 只看状态；`--no-digest` 只重建索引不调 API。

### ② 对话内自动召回（DSH skill）
已挂载 `mika-memory` skill（junction → `skills/mika-memory/`）：
- 对话涉及未花的**过往经历/日记/知识细节**时，agent 自动运行 `search.mjs` 检索后再作答
- 老师口述新经历时，可自动写入日记并运行 `auto.mjs` 维护记忆
- skill 内容即"何时触发 + 怎么检索 + 规则"，可自行修改

> **守护进程已停用（2026-09-24）**：`tools/watch.mjs` 与配套的 `mika-watch-boot` 插件已整体删除。
> 原因是它的单实例锁只判断「PID 还活着」，而 Windows 会复用 PID——守护的 PID 被别的进程
> 顶替后，新起的守护会误判"已有实例在跑"而静默退出（本机踩过两次）。
> **现在的规矩：写完日记手动跑一次 `node tools/auto.mjs`。**

## 首次使用

```powershell
cd C:\OneDrive\MikaMisono\agent
npm install                # 已装过可跳过（依赖 @huggingface/transformers）
node tools/index.mjs       # 首次会下载多语言嵌入模型（约 120MB，缓存于 .cache/）
node tools/search.mjs "泳装 老师 海边"
node tools/digest.mjs --list   # 看哪些日记还没有记忆卡
node tools/digest.mjs          # 生成记忆卡（需要 DEEPSEEK_API_KEY，读取 DSH 的 .credentials.yaml）
node tools/index.mjs           # 把记忆卡纳入向量库
```

## 日常流程（长期记忆闭环）

1. 每天/每次对话后，在 `memory/diary/` 写一篇 `YYYY-MM-DD.md` 日记
2. **手动版**：`node tools/digest.mjs` → 记忆卡；`node tools/index.mjs` → 建索引
3. **一键版（推荐）**：`node tools/auto.mjs`（两件事一次完成）
4. 之后任何对话里，agent 用 `node tools/search.mjs "某段记忆"` 语义召回（或由 mika-memory skill 自动触发）

## 嵌入引擎

- 默认：`Xenova/multilingual-e5-small`（本地 ONNX，q8 量化，384 维，多语言含中文）
- 模型不可用时自动降级为**纯 JS 哈希 n-gram 向量**（512 维，离线零依赖，词面召回）
- 换模型：改 `config.json` 的 `embedding.model` 后 `node tools/index.mjs --rebuild`

## DSH 集成

- **全局 persona**：`~\.dsh\profiles\desktop\cordis.patch.yml`（由 `tools\gen-persona-patch.mjs`
  从 `SKILL.md` 正文生成，含知识库绝对路径注记 + `includeHarnessIdentity: false`）
- **standard preset 的遮蔽人设已禁用**：`dsh-agent-presets\presets\standard\agent.cordis.yml`
  的 persona 行 `disabled: true` —— **应用升级后要复查这一行**，否则全局 persona 会被遮蔽
- **mika 预设（整场未花）**：`~\.dsh\.agent-presets\mika\`，由 `scripts\templates\` 生成
- 记忆检索：对话中让 agent 直接运行 `node tools/search.mjs "关键词"` 即可，无需改提示词

## 备份与回滚

- `~\.dsh\backups\mika-chat-<时间戳>\` 每次部署前的自动备份
- 向量库可随时 `--rebuild`，`.cache/` 删掉会重新下载模型
