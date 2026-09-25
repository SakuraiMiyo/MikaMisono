# 本机客户端里能找到什么、找不到什么

> 目的：把「Vol.3 第四章去哪里拿」这件事的**现场状态**记下来，免得下次重复摸索。
> 结论写于 2026-09-24，基于本机 `BlueArchivesJP` 客户端（构建日期 2026-03 左右）。

---

## 一句话结论

**Vol.3 第四章的原文，本机客户端里目前拿不到。** 它不在已下载的 TableBundles 里；
主线剧情表几乎可以肯定在 `ExcelDB.db` 里，而那个文件是**加密封装**（不是 ZIP、不是 SQLite），
比之前已经攻破的 `Excel.zip` 难一个量级。

---

## 一、客户端目录的实际情况

```
StreamingAssets/
├── catalog_Remote.json     Unity Addressables 目录，登记 173,774 个 bundle
├── TableBundles/    6440 文件 /  397 MB
├── MediaPatch/      4261 文件 / 5,871 MB
├── AssetBundles/   26778 文件 / 15,795 MB
└── Video/、aa/、Xigncode/
```

`catalog_Remote.json` 的 `m_InternalIds` 里，**bundle 逻辑名是明文**，例如
`academy-_mxload-prefabs-2025-07-02_assets_all_965806563.bundle`。
但登记了 173,774 个，本地只有约 37,479 个 → **客户端是按需下载的，大部分包不在本地。**

---

## 二、TableBundles：表数据在哪

物理名 = `{xxh64(逻辑名)}_{crc32}`，用 `ba-bundle-name-map.json` 反查逻辑名。
6440 条里，只有 2 个像「表」：

| 逻辑名 | 大小 | 是什么 |
|--------|------|--------|
| `Excel.zip` | 18.2 MB | **ZIP，口令已攻破**（`base64(MT(xxh32(物理名)).NextBytes(15))`）。里面 **74 张表**，但**全是 Field／小游戏／常量类**，没有一张剧情表 |
| `ExcelDB.db` | **202.8 MB** | **加密封装，未攻破**。不是 SQLite（无 `SQLite format 3`）、不是 ZIP（前 8 MB 无 `PK\x03\x04`、尾部无 `PK\x05\x06`）、前 4 MB 里搜不到 `Excel`/`Table`/`Scenario` 等任何明文字符串。头部 16 字节 `d6 35 11 97 cd d3 0a 40 8e d9 58 d1 a8 28 bf 58` 完全随机 |

其余 6438 条是关卡资源（`sb_*` / `rb_*` / `EN00xx` / 编号段）。

### `Excel.zip` 的 74 张表（全列，证明没有剧情表）

`animationblend` `animatordata` `bossphase` `characterdialogemoji` `characterdialogfield`
`characterleveladjustment` `cleardeckrule` `conqueststep` `constarena` `constaudio`
`constcombat` `constcommon` `constconquest` `constcontents` `consteventcommon`
`constfield` `constkeymapping` `constminigameccg` `constminigamejanken`
`constminigameroadpuzzle` `constminigameshooting` `constminigametbg` `constnewbiecontent`
`conststrategy` `couponstuff` `defaultcharacter` `defaultechelon` `defaultfurniture`
`defaultmail` `defaultparcel` `eventcontentboxgachaelement` `fieldcontentstage`
`fieldcontentstagereward` `fieldcurtaincallfreemode` `fielddate` `fieldevidence`
`fieldinteraction` `fieldkeyword` `fieldmastery` `fieldmasterylevel` `fieldmasterymanage`
`fieldquest` `fieldreward` `fieldscene` `fieldseason` `fieldstorystage` `fieldtutorial`
`fieldworldmapzone` `gachaselectpickupgroup` `interactiveworldraidcarrier` `limitedstage`
`limitedstagereward` `limitedstageseason` `localizeccg` `localizeetc` `localizefield`
`localizekeymapping` `localizesns` `minigamecard` `minigamedefensefixedstate`
`minigamedreamcollectionscenario` `minigameroadpuzzle` `minigameshooting`
`productbattlepass` `protocolsetting` `scenarioreplay` `scenarioresourceinfo`
`scenarioscriptfield1` `systemmail` `tacticarenasimulatorsetting`
`tacticdamagesimulatorsetting` `tacticsimulatorsetting` `tactictimeattacksimulatorconfig` `tag`

**注意 `scenarioscriptfield1`** —— 有 `Field1` 就说明存在 `ScenarioScriptMain1/2/3`、
`ScenarioScriptFavor1/2/3`、`ScenarioScriptEvent1/2/3`、`ScenarioScriptGroup1/2/3` 这一族表，
而它们**都不在这 74 张里**。

> 顺带一提：项目里的 `FlatData/` 已经由 `BlueArchive.fbs` 生成好了
> `ScenarioScriptMain1Excel` / `Main2` / `Main3`、`LocalizeScenarioExcel`、
> `ScenarioCharacterNameExcel` 等**全部**剧情相关类。也就是说**反序列化这一侧是现成的**，
> 缺的只是「把表读出来」这一步。

---

## 三、MediaPatch：不是剧情

4261 个逻辑名里，前缀分布是 `BG`(2192 张背景图)、`Theme`(385)、`JP`(302)、`Main`(288)、
`Event01`…、角色名等，基本都是 jpg / ogg / mp4。

其中看起来最像剧情、其实不是的是：

```
JP_CH0058.zip   →  ch0058_cafe_monolog_1.ogg / ch0058_battle_damage_1.ogg / …
JP_CH0060.zip   →  ch0060_battle_in_1.ogg / ch0060_battle_move_1.ogg / …
```

**`CH####` 是角色编号，不是章节编号。** 这些是角色的战斗／咖啡馆／大厅语音包（186 个）。

---

## 四、AssetBundles 与 Addressables 目录

- 本地 26,778 个，文件名即逻辑名。
- 在 `catalog_Remote.json` 的 173,774 条里搜 `excel` / `localize` → **0 条命中**；
  搜 `scenario` 只有角色模型（`assets-_mx-characters-ch0331_scenario-…`）和关卡场景。
- 结论：**Excel 表不走 Addressables**，它走的是另一套下载清单（TableBundles 那套）。

---

## 五、所以下一步能怎么走

按性价比排序：

1. **攻 `ExcelDB.db`**（推荐）
   需要的钥匙在 `dump.cs`（项目的 `assets/blue-archive/dump.cs`，76 MB 反编译产物）里。
   思路：搜 `ExcelDB` / 读取该文件的代码，找它的解密方式（BA 对部分容器用固定 key 的
   AES，key 通常硬编码在 Assembly-CSharp 里）。
   一旦打开，就同时拿到**全部卷**的剧情脚本，不只 Ch4 —— 这是唯一能一次补齐所有缺口的路径。

2. **换一个已下全的客户端**（最省事）
   本机客户端是按需下载的。找一份完整的 TableBundles（或直接找已经有人导出的
   `ScenarioScriptMain3ExcelTable.json`）。第四章属于 Vol.3，脚本应在 `Main3` 那张表里。

3. **找民间已导出的第四章文本**
   之前核过 ba-archive（preview + 正式站，两边都只有 Vol.3 前三章）、1788 个 event id、
   bawiki-data、SchaleDB、HuggingFace，都没有。可以再试：
   - B 站／NGA 的第四章剧情翻译帖（文字版）
   - BA 中文 wiki 的剧情页
   - `bilibili` 剧情字幕（视频，需 OCR/ASR，成本高）

4. **英文社区版**
   英文玩家社区做过 Vol.3 全章的翻译整理，可作为「章节结构／话数」的第二重验证源，
   但文本是英译，用于中文人格蒸馏需要再翻一次，不理想。

---

## 六、复现本文件的所有结论

```powershell
$py = "C:\SoftWare\Astrbot\backend\python\python.exe"
cd C:\OneDrive\MikaMisono\assets\story-cn

& $py probe_vol3_ch4.py          # 全站 31xxx-39xxx 穷举（结论：公开站没有 Ch4）
& $py catalog_blue_archive_io.py # 抽正式站自己的 mainStoryIndex（结论：max=33250）
& $py game\audit_game_assets.py  # 本机已下载 vs 目录登记
& $py game\list_excel_tables.py  # Excel.zip 全部 74 张表
& $py game\probe_exceldb.py      # ExcelDB.db 的封装格式判定
```
