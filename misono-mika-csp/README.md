# 圣园未花 CSP 交付包

生成日期：2026-09-24

这是使用 Character Skill Producer 对工作区 `assets/story-cn/` 中的未花剧情语料进行高保真蒸馏，并以联网资料补足 Vol.3 第4章后得到的自包含角色 Skill。

## 交付内容

- `SKILL.md`：可直接安装的角色行为 Skill。
- `manifest.json`：角色、资料日期、覆盖媒体和质量分。
- `references/sources.json`：来源、哈希、失败记录和用途。
- `references/distillation.md`：六条核心行为模式及证据链。
- `references/corpus-verification.md`：本地语料校验结果。
- `references/quality-report.json`：自动质量检查结果。
- `references/research/01-setting.md`：设定与世界观。
- `references/research/02-personality.md`：人格、压力反应与成长弧。
- `references/research/03-expression.md`：992 句台词的表达质感与统计。
- `references/research/04-relationships.md`：关系算法与社会认知。
- `references/research/05-key-scenes.md`：14 个关键场景及决策逻辑。
- `references/research/06-media-coverage.md`：媒体覆盖、冲突与资料边界。

## 数据基础

- 110 篇原始剧情。
- 7,110 轮对话。
- 992 句未花台词 / 17,133 汉字。
- 117 个未花参与场景窗口。
- 本地 Vol.3 第1至第3章共 76 个主线 JSON；联网补充第4章 27 话的章节结构、关键场景与创作者访谈。

## 使用方式

把整个目录复制到支持 Agent Skills 的 skills 目录即可。不要只复制 `SKILL.md`，否则会丢失证据链和更新边界。

## 已解决的资料疑问

- 原先所谓“Vol.3 官方目录 76 节与本地一致”只覆盖第1至第3章。抓取脚本将 story id 限制为 `< 34000`，漏掉了第4章《被遗忘的诸神的垂怜经》27话。
- “Kyrie Eleison 独战圣徒会”已确认是 **Vol.3 第4章正式主线场景**，不是最终篇、技能演出或 PV 衍生传说。第23话为 `Kyrie for the Students Part 1`；未花原谅并放行阿里乌斯小队后独自阻挡尤斯蒂娜圣徒会增援，老师随后赶到救下她。
- 编剧总监梁主荣确认，《Kyrie》是在第3章之后为解决“如何拯救未花”而加入；主题是放下“公平的痛苦”，由人彼此原谅和拯救。

详见 `references/research/07-online-supplement.md`。

## 仍保留的边界

- 《夏空のやくそく》已由 NEXON 官方活动页确认，但仍缺完整剧情逐字稿。
- 社区中文翻译不是官方中文定稿。
- 旧项目的婚姻、同居等用户私有连续性未混入通用原作 Skill。
- Vol.3 第4章尚无本地可逐行检索的原始演出 JSON，因此不复刻其精确台词。
