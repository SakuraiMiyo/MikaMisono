# 圣园未花 · 本机全项目

> 《蔚蓝档案》圣园未花（聖園ミカ / Misono Mika）在本机的完整实现：
> **一个 QQ 机器人 + 一个本机 DSH agent，共享同一个人格内核。**
>
> 📖 **先看这个** → [`docs/未花系统总览.md`](docs/未花系统总览.md)（全链路接线图、依赖、坑、速查）

---

## 目录结构（2026-09-24 整理后）

```
MikaMisono/
├── README.md                  ← 你在这里（项目地图）
├── docs/
│   ├── 未花系统总览.md          ★ 全链路接线图 + 两条链路差异 + 快查
│   ├── dsh-未花提示词注入.md     DSH 侧部署 / 更新 / 回滚 / 验证手册
│   ├── dsh接入AstrBot桥接.md    桥接手册（⚠️ 当前链路断开，见文件内横幅）
│   └── archive/                历史文档：桥接旧版、会话同步指南、一次性脚本
├── agent/                     ★ ② DSH 侧：角色 + 知识库 + 长期记忆（原 mika-chat/）
│   ├── SKILL.md               DSH 人格真源（deploy 脚本据此生成 persona 与预设）
│   ├── knowledge/             角色知识库（6 篇）
│   ├── memory/                日记 / 记忆卡 / 滚动摘要 / 向量索引
│   ├── tools/                 index · search · digest · auto · gen-persona-patch
│   └── skills/mika-memory/    对话内记忆召回 skill（junction 到 ~/.agents/skills）
├── qq-bot/                    ★ ① QQ 侧（本机不执行，只存真源与素材）
│   ├── persona/               bot-personality.md（QQ 人格真源）· _欢迎回来，未花.md
│   ├── notes/                 出图提示词系统 · 麦当劳点餐备忘
│   ├── web-samples/           早期前端小样
│   └── legacy/                bot.md（旧书：写给老师的真心话）
├── scripts/
│   ├── deploy_mika.ps1        ★ DSH 侧部署唯一入口（改完 SKILL.md 就跑它）
│   └── templates/             mika 预设模板
├── assets/
│   ├── blue-archive/          碧蓝档案素材提取工具（git 仓库，需要时手动跑）
│   └── story-cn/              ★ 未花剧情语料库（110 篇官方原文 + 992 句她本人的台词）
│                              ← 交给别的模型做蒸馏用这个；见其中 README.md
├── old-machine/               旧机器 D 盘的 dsh 会话数据（留档，本机不用）
└── _archive-20260924/         本次整理的历史备份（人格迭代 / 旧 SKILL / deprecated 脚本）
```

---

## 两个「未花」怎么区分

| | ① QQ 机器人 | ② 本机 DSH agent |
|---|---|---|
| 谁在说话 | 群聊里的未花（老师 + 群友都看得到） | 只有老师看到的未花（agent 对话） |
| 平台 | AstrBot Desktop + NapCat（QQ） | DSH Desktop |
| 人格真源 | `qq-bot/persona/bot-personality.md` | `agent/SKILL.md` |
| 说话规矩 | 群聊一句话、不主动写动作、句末 ☆ | 场景 / 动作 / 内心三层，可长可短 |

> ⚠️ 两条链路**不共享存储、不自动同步**。角色设定（年龄、外形、经历、称呼）改一边要手动同步另一边；
> 平台专属规矩**不要互搬**。

---

## 常用操作

```powershell
# ① 改完 agent\SKILL.md 或 knowledge\ → 重新部署（persona + skill + 预设，全部幂等带备份）
pwsh -File .\scripts\deploy_mika.ps1

# ② 写完日记 → 补记忆卡 + 重建索引
cd agent; node tools\auto.mjs

# ③ 语义检索记忆
cd agent; node tools\search.mjs "问题" --k 5
```

> 记忆守护进程（`watch.mjs` + `mika-watch-boot` 插件）已于 2026-09-24 停用删除 —— 索引不再自动重建，
> 写完日记记得手动跑一次 `auto.mjs`。

---

## 状态一览（2026-09-24）

| 部件 | 状态 |
|------|------|
| DSH 全局 persona（未花） | ✅ 生效（`includeHarnessIdentity: false`） |
| 「未花模式」预设 | ✅ 已部署（`settings.yaml` 的默认 preset 仍是 `standard`） |
| 角色 Skill / 记忆 Skill | ✅ 已部署（后者 junction 指向 `agent/skills/`） |
| 记忆库 | ✅ 39 篇日记 / 39 张卡 / 85 文档 · 330 块 |
| QQ 机器人（AstrBot） | ✅ 线上运行（`deepseek-flash` 直连） |
| dsh-bridge（8808） | ⚠️ **在跑但没接进 AstrBot**（详见总览第四节） |
| 记忆守护进程 | ❌ 已删除（改手动 `auto.mjs`） |
| 全家桶架构文档（OneDrive 根） | ⚠️ 停留在 v2.6 / 7 月，尚未同步 8-9 月进展 |

---

## 参考资料

- [萌娘百科·圣园弥香](https://zh.moegirl.org.cn/圣园弥香)
- [维基百科·圣园弥香](https://zh.wikipedia.org/wiki/聖園彌香)
- [百度百科·圣园未花](https://baike.baidu.com/item/圣园未花/63285327)

## 许可

仅供个人娱乐用途。角色形象与《蔚蓝档案》版权归 NEXON Games 所有。
