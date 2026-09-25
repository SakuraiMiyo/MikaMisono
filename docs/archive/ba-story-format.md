# Blue Archive JP — 剧情（scenario / dialogue）文本文件格式侦查报告

> 侦查对象：`C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP`
> 侦查方式：**全程只读**（只打开文件读字节；解包一律在内存中完成，未写入任何游戏目录）
> 侦查日期：2026-02（本机当前安装版本，`TableCatalog.hash` = `10751205`）
> 工作脚本与中间产物：`C:\OneDrive\MikaMisono\docs\archive\_work\`

---

## 0. 一句话结论

**剧情正文不在 `MediaPatch`，也不在 `AssetBundles`。它在 `BlueArchive_Data\StreamingAssets\TableBundles\` 里——4270 个「单条目加密 ZIP」，每个 ZIP 内恰好一个 `.bytes` 文件，条目名就是该场景包的逻辑名（如 `sb_01_schale_p01_scenario.bytes`）。**

密码已经**完整破解**（见 §4），可以逐包解出明文。载荷头部是明文可见的字符串（已验证：`StartBattle`、`ConditionDead1-1`、`CommandSpawn1-2`…），说明这是**剧情脚本/演出数据**，不是加密过的资源；其精确容器布局（MemoryPack 长度头 + FlatBuffers 表）仍差最后一步（见 §7）。

---

## 1. 目录角色划分（实测）

| 目录 | 文件数 | 总大小 | 文件头分布 | 角色结论 |
|---|---|---|---|---|
| `TableBundles\` | 6442（+`Catalog\`2） | 417 MB | 6436 × `PK\x03\x04`；4 个非 ZIP（见下）；2 个 Catalog | **剧情正文 + 全部 Excel 表 + 战斗逻辑数据** |
| `MediaPatch\` | 4263（+`Catalog\`2） | 5.9 GB | JPEG 2184、OGG 1148、PNG 493、ZIP 302、MP4 126、JPEG/EXIF 8 | **纯媒体资源**：立绘差分、BGM/语音 OGG、L2D/背景 PNG、过场 MP4。**不是**对话脚本 |
| `AssetBundles\` | 26780（+`Catalog\`2） | 16.6 GB | `UnityFS` × 26778 | Addressables 资源包：模型/动画/材质/Spine/场景。**不含**剧本文本表 |

关键反证（推翻「MediaPatch 里是逐场景对话脚本」的假设）：

```
MediaPatch\10006798014105879602_1538177547  → ff d8 ff e0 00 10 4a 46 49 46  → JPEG
MediaPatch\1002107164915564977_3441083267   → 4f 67 67 53                    → OggS
MediaPatch\10031833379790717669_4208491160  → 89 50 4e 47                    → PNG
TableBundles\10001900114910089910_1704857403 → 50 4b 03 04                   → 加密 ZIP
```

`TableBundles` 里那 4 个非 ZIP 文件是 `AddressablesCatalog` 之类：

| 磁盘文件 | 作用 |
|---|---|
| `12886511902196705184_2695432036` | Addressables bundle 目录清单（内部含 `bundlename.bundle` 字符串） |
| `2733092781725905578_4094553949` | 同上 |
| `4354043109159736559_651527683` | 同上 |
| `6993339912994747134_1745771760` | 同上 |

---

## 2. `TableBundles` 全量条目名扫描（6440 个 ZIP，只读 central directory）

- 扫描文件数：**6440**（另有 `Catalog\` 2 个非 ZIP）
- 条目总数：**6961**
- 读不出的 ZIP：**4 个**（就是上表那 4 个 Addressables 清单，不是 ZIP）
- 空 ZIP：0

### 2.1 ZIP 条目数分布

| 条目数 | ZIP 个数 | 说明 |
|---|---|---|
| 1 | **6426** | 单条目包 —— 剧情场景包都在这类里 |
| 2–5 | 2 | |
| 6–20 | 5 | |
| 21–100 | 2 | `12478936438010851834_4172722046`(64)、`16300795542385574620_4128271700`(74) |
| >100 | 1 | `15171489324176746188_1544061357`(325, strategymap JSON) |

### 2.2 条目名后缀模式统计（Top 20）

| 模式 | 数量 | 含义推测 |
|---|---|---|
| `p01_d.bytes` | 1352 | 场景第 1 部分 · **d**ialogue（有对话框台词） |
| `p02_d.bytes` | 816 | |
| `p01_n.bytes` | 720 | **n**arration / 无对话框（画面演出 + 独白） |
| `p02_n.bytes` | 453 | |
| `d_nodelayer.bytes` | 148 | d 场景的 node layer（无遮挡层） |
| `n_nodelayer.bytes` | 104 | |
| `hardcore_start2phase.bytes` | 91 | 战斗场景（非剧情） |
| `normal_start2phase.bytes` | 85 | 同上 |
| `insane_start2phase.bytes` | 85 | |
| `veryhard_start2phase.bytes` | 85 | |
| `extreme_start2phase.bytes` | 85 | |
| `hard_start2phase.bytes` | 85 | |
| `torment_start2phase.bytes` | 79 | |
| `d_s.bytes` | 61 | |
| `p01_e.bytes` | 47 | **e**vent |
| `d_p01.bytes` | 39 | |
| `n_s.bytes` | 36 | |
| `hardcore_start3phase.bytes` | 36 | |
| `d_nosidetrain.bytes` | 35 | 列车场景特化层 |
| … | | |

**结论**：条目名 = `<场景ID>_<章节>_<sN/boss>_<地点>_<pNN>_[d|n][_nodelayer|_s|_e|_nosidetrain].bytes`。
下划线后缀语义：**`d` = 对话场景，`n` = 旁白/演出场景**。

### 2.3 关键词命中（条目名级别）

| 关键词 | 命中条目数 |
|---|---|
| `scenario` | 39 |
| `story` | 6 |
| `localize` | 5 |
| `dialog` | 2 |
| `script` | 1 |

→ 完整清单见 §3。其余 6900+ 条剧情场景包因为条目名里不写 "scenario"，只能靠 `_d` / `_n` 后缀 + 数字场景 ID 识别。

---

## 3. 「含剧情条目的包」完整清单

### 3.1 剧情场景包（条目名含 `scenario` / `story`）——共 52 条，来自 52 个磁盘文件

| 磁盘文件 | ZIP 内条目名 | 未压缩大小 |
|---|---|---|
| `10126492459843226082_194748235` | `rb_02_en0008_p01_d_scenario02.bytes` | 990,836 |
| `10128920823377164736_768572690` | `rb_02_en0006_p01_d_scenario01_nodelayer.bytes` | 15,040 |
| `10208646925099257802_2031956405` | `8443301_01_s3_01_schale_p01_scenario.bytes` | 2,949 |
| `10508793754200446274_800285696` | `rb_02_binah_p01_d_scenario.bytes` | 823,288 |
| `10574234224707093126_2105420255` | `400050118_s3_01_rb_02_en0006_p01_d_scenario01.bytes` | 4,087 |
| `10627096113269287586_1032008006` | `270301_worldraid_en0020_street_scenario_start2phase.bytes` | 6,333 |
| `10801870768369287090_2877417202` | `rb_02_binah_p01_d_scenario_nodelayer.bytes` | 18,496 |
| `11033906853979439658_918726958` | `400010339_s3_02_en0008_p01_d_scenario01.bytes` | 3,318 |
| `1135095554448124631_2863619728` | `400010336_s3_02_en0008_p01_d_scenario02.bytes` | 2,840 |
| `12056688516613450830_2290347440` | `sb_03_trinitychurch_p01_n_scenario.bytes` | 754,400 |
| `1251795478736651899_417260566` | `400050120_s3_01_rb_02_en0006_p01_d_scenario01.bytes` | 3,842 |
| `12552755968392355289_2139566679` | `rb_03_hieronymus_p01_d_scenario_2.bytes` | 889,060 |
| `13398390916966574027_3245783669` | `rb_03_hieronymus_p01_d_scenario.bytes` | 889,060 |
| `13856212391497941018_2545043387` | `8334307_01_03_school_p01_d_story.bytes` | 8,109 |
| `13988258909499140604_3276174881` | `rb_02_en0008_p01_d_scenario01.bytes` | 822,112 |
| `14647912243327621878_2300540278` | `rb_02_en0008_p01_d_scenario02_nodelayer.bytes` | 22,524 |
| `14764328455223856128_2874123602` | `400060305_s1_03_hieronymus_p01_d_scenario01.bytes` | 4,934 |
| `16066775590139801068_3185069564` | `401000215_01_s3_03_hieronymus_p01_d_scenario_2.bytes` | 4,694 |
| `16244003148895641294_898974678` | `sb_03_school_p01_d_story.bytes` | 836,500 |
| `16266226196536135190_166011774` | `rb_03_hieronymus_p01_d_scenario_nodelayer.bytes` | 19,752 |
| `16300795542385574620_4128271700` | ⚠ **Excel 表包**，见 §3.2（含 `scenarioreplayexceltable.bytes` 等 12 条） | — |
| `16641332357143156175_4276847657` | `270301_worldraid_en0020_street_v01_scenario.bytes` | 37,511 |
| `16831501588143809264_378776166` | `400060303_s1_03_hieronymus_p01_d_scenario01.bytes` | 1,825 |
| `17001064684666740368_1418536455` | `sb_03_underground_p01_n_scenario.bytes` | **1,349,192** |
| `17185804037354063946_2476581590` | `sb_03_trinitychurch_p01_n_scenario_nodelayer.bytes` | 17,176 |
| `17924405981711192028_1498160283` | `rb_03_chesed_p01_d_scenario.bytes` | **1,244,252** |
| `17932541498652782880_4071079313` | `270301_worldraid_en0020_street_scenario.bytes` | 11,816 |
| `3041284869061018635_3165216273` | `rb_03_chesed_p01_d_scenario_nodelayer.bytes` | 28,224 |
| `3152370782941368777_3453525187` | `sb_01_schale_p01_scenario_nodelayer.bytes` | 80,656 |
| `3221847235107924948_1801883198` | `en0011_scenariotemp.bytes` | 14,876 |
| `5681846881984034646_1205077894` | `chesedscenariotest.bytes` | 878 |
| `6275497673431309398_1915708526` | `9938_ch0309_story_test.bytes` | 11,576 |
| `6342030175879416904_2237560002` | `rb_02_en0008_p01_d_scenario01_nodelayer.bytes` | 18,624 |
| `6723093585110813093_2723063546` | `rb_02_en0006_p01_d_scenario01.bytes` | 677,992 |
| `7305034778953511186_691186273` | `en0006_storytest.bytes` | 2,002 |
| `7907542019953897795_4103731301` | `sb_03_school_p01_d_story_nodelayer.bytes` | 19,048 |
| **`8096923742589028906_2683815145`** | **`sb_01_schale_p01_scenario.bytes`** | **3,545,188** ← 最大剧情包（Vol.1 夏莱） |
| `9417025269956804843_2704210705` | `sb_03_underground_p01_n_scenario_nodelayer.bytes` | 30,692 |
| `9469145922516746524_1903311647` | `rb_03_hieronymus_p01_d_scenario_2_nodelayer.bytes` | 19,752 |
| `9525948173773304377_2134095779` | `270301_worldraid_en0020_street_scenario_start3phase.bytes` | 1,447 |
| `9831635374824745190_1758483698` | `400010335_s3_02_en0008_p01_d_scenario02.bytes` | 4,967 |

### 3.2 Excel 表包 —— 全机唯一一个：`16300795542385574620_4128271700`

- 大小 19,109,176 字节，**74 个条目**，密码 = `Excel.zip`（已验证可解）
- 其中与剧情直接相关的 12 条：

| 条目名 | 未压缩大小 | 内容 |
|---|---|---|
| `scenarioscriptfield1exceltable.bytes` | 475,272 | **Field1 场景脚本表**（与单场景包同 schema） |
| `characterdialogfieldexceltable.bytes` | 183,096 | 野外对话（对话框 + 语音） |
| `characterdialogemojiexceltable.bytes` | 11,224 | 对话表情 |
| `fieldstorystageexceltable.bytes` | 12,664 | Field 剧情关卡 |
| `scenarioreplayexceltable.bytes` | 4,384 | 剧情回放（modeId/volumeId/chapterId/episodeId） |
| `scenarioresourceinfoexceltable.bytes` | 2,288 | 剧情资源索引 |
| `minigamedreamcollectionscenarioexceltable.bytes` | 1,096 | 小游戏剧情 |
| `localizeetcexceltable.bytes` | 1,118,896 | 杂项本地化（最大） |
| `localizeccgexceltable.bytes` | 140,092 | CG 本地化 |
| `localizefieldexceltable.bytes` | 39,432 | Field 本地化 |
| `localizesnsexceltable.bytes` | 3,124 | SNS（MomoTalk）本地化 |
| `localizekeymappingexceltable.bytes` | 4,456 | 本地化 key 映射 |

> **重要否证**：`LocalizeScenarioExcel`、`ScenarioScriptMain1/2/3Excel`、`CharacterDialogExcel`、`LocalizeCharProfileExcel` 这些「主剧情表」**在整个安装目录里根本不存在**。对 6440 个 ZIP 的 6961 条条目名做了全量精确匹配（`map_excel_tables.py`），`*exceltable.bytes` 条目**只出现在这一个包**，且只有 72 条。→ 本客户端已经把主剧情全部「按场景拆包」到 `TableBundles` 的单条目 ZIP 里了。

### 3.3 逻辑名 ↔ 磁盘名 映射的现状

- `Catalog\TableCatalog.bytes` 中可以完整读出 **6444 条逻辑 `.zip` 名 + 每条对应的 size / hash / crc / flag**（解析器：`_work/parse_catalog2.py`）。例：

  ```
  size=350423  hash=00000000d1e6a464  crc=65536  flag=1  sb_01_mainstreet_p01_d.zip
  size=440     hash=000000007fc4f293  crc=65536  flag=1  Module.zip
  size=1339146 hash=00000000c4cbf40d  crc=769    flag=0  TablePatchPack_Prologue_GroundGrid_1.zip
  ```

- **但 Catalog 里不含磁盘哈希文件名**（`<u64>_<u32>` 形式在 Catalog 字节中 0 命中）。
- 逻辑名 → 磁盘名的最终映射**由 ZIP 内条目名给出**，不需要 Catalog：条目名 `sb_01_schale_p01_scenario.bytes` ⇒ 逻辑包名就是 `sb_01_schale_p01_scenario.zip`。**这条经验规则已用密码验证通过。**
- 逻辑名清单统计（6454 条）：`*_d.zip` = 2207、`*_n.zip` = 1173、`*scenario*` = 35、`*story*` = 5。

---

## 4. 密码算法（**已破解并验证**）

### 4.1 规则

```
password = base64( MersenneTwister( xxh32(seed, 0) ).NextBytes(15) )
seed     = <ZIP 内唯一条目的名字去掉 ".bytes"> + ".zip"
```

- 单条目剧情包：**seed 就是那个条目名换 `.zip`**（例：条目 `8322306_01_02_forestriver_p01_d.bytes` → seed `8322306_01_02_forestriver_p01_d.zip`）
- 多条目表包：seed 是**包本身的逻辑名**。实测：
  - `16300795542385574620_4128271700`（74 条目）→ seed = **`Excel.zip`** ✅
  - `1858308081688323146_3447461123`（6 条目）→ seed = **`Battle.zip`** ✅
- 参考实现：`assets\blue-archive\lib\TableService.py`、`lib\MersenneTwister.py`、`lib\XXHashService.py`

### 4.2 可直接跑的代码片段

```python
import os, sys, zipfile
from base64 import b64encode
sys.path.insert(0, r"C:\OneDrive\MikaMisono\assets\blue-archive")
from lib.MersenneTwister import MersenneTwister
from lib.XXHashService import CalculateHash

TB = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\TableBundles"

def password(seed: str) -> bytes:
    return b64encode(MersenneTwister(CalculateHash(seed)).NextBytes(15))

def read_bundle(disk_name, entry_name):
    """读出单个剧情场景包的明文 payload。"""
    seed = entry_name[:-len(".bytes")] + ".zip"
    with zipfile.ZipFile(os.path.join(TB, disk_name)) as z:
        return z.read(entry_name, pwd=password(seed))

# 例：夏莱 Vol.1 第 1 章
data = read_bundle("10001900114910089910_1704857403",
                   "8322306_01_02_forestriver_p01_d.bytes")
print(len(data), data[:32].hex(" "))
# -> 7677 0600000000020000000000000000000000000200000004f4
```

实测输出：7677 字节，头部 `06 00 00 00 00 02 00 00 00 00 00 00 00 00 00 00 00 00 02 00 00 00 04 f4 ff ff ff 0b 00 00 00 53 74 61 72 74 42 61 74 74 6c 65`，其中 `53 74 61 72 74 42 61 74 74 6c 65` = ASCII **`StartBattle`**。

> 注意：**不要**用 `TableZipFile(path)` 直接跑 —— 它会拿 `os.path.basename(磁盘路径)` 当 seed，而磁盘名是哈希，必然失败。必须自己传逻辑名。

### 4.3 Excel 表包内载荷的二次解密（已破解）

`Excel.zip` 里的每个 `.bytes` 还要再做一次 XOR，key 是**表类名**：

```python
from lib.TableEncryptionService import XOR, CreateKey
from FlatData import LocalizeEtcExcelTable          # 651 个生成类之一

raw  = read_bundle("16300795542385574620_4128271700", "localizeetcexceltable.bytes")
data = XOR("LocalizeEtcExcel", raw)                 # 即 CreateKey("LocalizeEtcExcel")
root = LocalizeEtcExcelTable.GetRootAs(data)        # 之后按已生成的类解析
```

---

## 5. 数据结构：`ScenarioScriptField1Excel`

单场景剧情包（`*_pNN_d.bytes` / `*_pNN_n.bytes` / `*_scenario.bytes`）的载荷就是这张表的序列化结果。

### 5.1 字段表（**从 `global-metadata.dat` 提取，非猜测**）

来源：`BlueArchive_Data\il2cpp_data\Metadata\global-metadata.dat`（37,852,096 字节，magic `0xFAB11BAF`，metadata version **31**）。
方法：解析 header → string(off 1269832/4836628) 与 typeDefinitions(off 31032308, stride **0x58**) 两张表，再在字符串表里定位 `CreateScenarioScriptField1Excel` 符号组。
脚本：`_work/il2cpp_schema.py`；产物：`_work/il2cpp_field_schemas.json`。

**FlatBuffers 声明顺序（= vtable slot 顺序）**：

| slot | 字段名 | 类型 | 说明 | 元数据符号证据 |
|---|---|---|---|---|
| 0 | `SelectionGroup` | int64 | 选项分支组 | `AddSelectionGroup` |
| 1 | `Sound` | string | 音效 | `GetSoundBytes`, `SoundOffset` |
| 2 | `Transition` | uint32 | 转场效果 | `AddTransition` |
| 3 | `BGName` | uint32 | 背景 ID（关联 `ScenarioBGNameExcel`） | `AddBGName` |
| 4 | `BGEffect` | uint32 | 背景特效 | `AddBGEffect` |
| 5 | `PopupFileName` | string | 弹出立绘/演出文件名 | `GetPopupFileNameBytes` |
| 6 | `ScriptKr` | string | 韩文原稿 | `GetScriptKrBytes`, `ScriptKrOffset` |
| 7 | **`TextJp`** | string | **日文台词 —— 目标文本字段** | `get_textJp`, `GetTextJpBytes`, **`TextJpOffset`** |
| 8 | `VoiceJp` | string | 日文语音 key | `GetVoiceJpBytes`, `VoiceJpOffset` |

字符串编码：**UTF-16**（`GetXxxBytes` + `TextJpOffset` 符号对；数值字段用 `XOR(tableName, bytes)` 混淆，字符串字段是 base64(XOR(utf16))——与 `lib/TableEncryptionService.py` 的 `ConvertString`/`EncryptString` 完全一致）。

**根表 `ScenarioScriptField1ExcelTable`**：唯一槽位 slot 0 = `DataList`（`ScenarioScriptField1Excel` 的 vector）。

### 5.2 兄弟表（同结构，按用途分表）

`ScenarioScriptMain1/2/3Excel`（主线）、`ScenarioScriptFavor1/2/3Excel`（羁绊）、`ScenarioScriptGroup1/2/3Excel`（社团/小组）、`ScenarioScriptEvent1/2/3Excel`（活动）、`ScenarioScriptContentExcel`、`ScenarioScriptTestExcel`。字段布局与 Field1 完全相同（已核对 `FlatData\ScenarioScriptMain1Excel.py` 与 `dump.py:3288-3346`）。

### 5.3 相关表（用于把 slot 数值翻译成人话）

| 表 | 用途 |
|---|---|
| `ScenarioCharacterNameExcel` | 说话人显示名 |
| `ScenarioBGNameExcel` / `ScenarioBGName_GlobalExcel` | `BGName` → 背景资源 |
| `ScenarioCharacterEmotionExcel` | 表情 ID |
| `ScenarioCharacterSituationSetExcel` | 立绘/状态组合 |
| `ScenarioEffectExcel` / `ScenarioBGEffectExcel` | 特效 ID |
| `ScenarioTransitionExcel` | `Transition` → 转场资源 |
| `ScenarioReplayExcel` | 剧情回放目录（modeId / volumeId / chapterId / episodeId） |
| `ScenarioResourceInfoExcel` | 剧情资源索引 |
| `FieldStoryStageExcel` | Field 剧情关卡 |
| `LocalizeScenarioExcel` | ⚠ 本机不存在（见 §3.2 否证） |

---

## 6. 真实样本

目前能稳定拿到的**真实明文**有两类。

### 6.1 场景包内的明文命名字符串（**已复现，真实数据**）

文件：`TableBundles\10001900114910089910_1704857403` → `8322306_01_02_forestriver_p01_d.bytes`（7,677 字节）

payload 偏移 30 起（UTF-8 / ASCII 明文）：

```
StartBattle
ConditionDead1-1        (offset 503)
ConditionDead1-2
ConditionDead2-1
ConditionDead4-1
ConditionDead4-2
CommandSpawn1-1
CommandSpawn1-2
CommandSpawn2-1
SpawnPointParent1 .. SpawnPointParent4
SpawnPointParent1-1 / -2
Forestriver_Destroytable_01_Standard
Forestriver_Stone_01_Standard / _02_ / _03_
Forestriver_Wood_01_Standard / _02_ / _03_
KumabotPapa_Slumpia_SG_E_832EventQuest
KumabotPapa_Slumpia_SG_M_832EventQuest
Usagibot_Slumpia_AR_M_832EventQuest
```

这些是**关卡演出触发器 / 指令名**（`ConditionDead*` = 单位死亡条件，`CommandSpawn*` = 刷怪指令，`SpawnPointParent*` = 刷怪点，`Forestriver_*` = 森林河场景的道具），确认这是"森林河 01 场景"的演出脚本。

### 6.2 日文台词样本

**未能取得。** 载荷中的日文串（UTF-16）在 §7 所述容器解析完成前读不出正确边界——`jp_runs.py` 扫出的 4 个"日文串"都是错位截断的乱码（如 `䄁纼㶲`），不可信，故不在此列出以免误导。

**可达性论证**：`TextJp` 字段存在且就在 slot 7；`sb_01_schale_p01_scenario.bytes` 单个包 **3,545,188 字节**、`sb_03_underground_p01_n_scenario.bytes` **1,349,192 字节**，体量只可能是成篇文本。拿到正确容器解析后即可直接导出全量日文。

---

## 7. 未解决的问题与下一步

### 未解决（按优先级）

1. **场景包载荷的容器布局**（唯一卡点）
   - 已确认：密码解密成功；payload 里能看到明文 `StartBattle` 等字符串；有大量 UTF-16 日文数据；尾部是 float 数组。
   - 已排除：直接的 FlatBuffers（扫全文件没有合法 vtable）；Excel 表那种 `XOR(tableName, data)`（XOR 后 vtable 数为 0）。
   - 观察到的头部：`06 00 00 00 | 00 02 00 00 | 00 00 00 00 00 00 00 00 | 00 00 02 00 00 00 04 f4 ff ff ff | 0b 00 00 00 | "StartBattle"`
     —— `0b 00 00 00` + 11 字节正是标准的 **length-prefixed string**，说明外层是 **MemoryPack** 序列化（仓储里已经有 `MemoryPackDeserializer/` 这个现成工具！）。
   - 大包 `sb_01_schale_p01_scenario.bytes` 又完全是另一种头（`18 00 00 00 | 00 00 | 12 00 20 00 14 00 10 00 0c 00 08 00 04 00 | 18 00 | 1c 00 | 12 00 00 00 | <floats>`），像是标准 flatbuffer vtable 区，但按标准公式算出的 root 自指，需要按"尺寸前缀 + 头部 off-by-N"重新推导。

   **下一步建议**：用 `assets\blue-archive\MemoryPackDeserializer\MemoryPackDeserializer.exe`（已有现成工具）直接吃这些 payload；或从 `global-metadata.dat` 里找 `ScenarioScriptField1ExcelTable` 的 `Deserialize` 实现路径。

2. **主剧情 Excel 表（`ScenarioScriptMain*`、`LocalizeScenarioExcel`、`CharacterDialogExcel`）在本机不存在** —— 已用全量精确匹配证明（§3.2）。若需要，只能去 CDN 拉 `TableCatalog.json` 里引用的其他 TableBundle，或从旧版本安装里找。

3. **逻辑名 → 磁盘哈希名 的完整映射表** 未建立。目前靠"ZIP 内条目名换 `.zip` 反推"就够用；若要精确，需要解析 `Catalog\TableCatalog.bytes` 与 Addressables 的 bundle 哈希算法（`<u64>` 高位疑似 crc/size 混合，未破）。

4. ~~`MediaPatch` 的 `<hash>_<hash>` ↔ 逻辑路径映射~~ —— **已解决**，见 §7.1。

### 7.1 补充结论一：`MediaCatalog.bytes` 格式（已破）

`MemoryPackDeserializer\src\MemoryPackDeserializer.cs` 给出了权威 schema：

```csharp
[MemoryPackable] public partial class Media {
    public string Path; public string FileName;
    public long Bytes; public long Crc;
    public bool IsPrologue; public bool IsSplitDownload; public MediaType MediaType;
}   // MediaType: None=0, Audio=1, Video=2, Texture=3
[MemoryPackable] public partial class MediaCatalog { public Dictionary<string, Media> Table; }
```

实测 `MediaPatch\Catalog\MediaCatalog.bytes`（680,972 字节）的**实际布局**是：

```
[uint32 entryCount = 1090817][uint64 ?]
重复 1,090,817 次：{
    [int32 L][L 字节 Path]                      e.g. "audio/voc_jp/jp_airi/jp_airi"
    [int32 L][L 字节 FileName]                  e.g. "GameData\Audio\VOC_JP\JP_Airi.zip"
    [MemoryPack ObjectHeader]
    [int64 Bytes][int64 Crc][bool][bool][MediaType]
}
```

逐字段对齐验证（第 1 条记录）：

| 字段 | 实测值 |
|---|---|
| `Path` | `audio/voc_jp/jp_airi/jp_airi` |
| `FileName` | `GameData\Audio\VOC_JP\JP_Airi.zip` |
| `Bytes` | 2,143,288 |
| `Crc` | 3,375,441,397 |
| 之后 | 3 个 1 字节枚举（`IsPrologue` / `IsSplitDownload` / `MediaType`），使下一条记录从偏移 104 开始 |

即：**该 `.bytes` 是 `Dictionary<string,Media>` 的 MemoryPack 序列化体，描述 `MediaPatch` 里每个 `<hash>_<hash>` 文件对应哪个游戏资源路径。**
（现成的 `MemoryPackDeserializer.exe` 硬编码了解 `MediaCatalog` 类型，但它要求文件带完整 MemoryPack 对象头；本文件省掉了头部，所以需要自写 30 行解析器，见 `_work/parse_mediacatalog.py` 的思路。**但这与剧情无关**——`MediaPatch` 全是图像/音频。）

### 7.2 补充结论二：主 Excel 表已从本客户端移除的证据链

- `TableCatalog.bytes` 中 **6444 条全部是 `.zip`**，其中 `Excel.zip` 确实存在（size 未知、hash `…`，与 `Module.zip` 一起列在清单第 5624 / 5637 行）。
- 但 `Excel.zip` 对应的**磁盘包**是 `16300795542385574620_4128271700`，里面只有 **74 个条目**。
- 651 个 FlatData 生成类里，`LocalizeScenarioExcel`、`ScenarioScriptMain1/2/3Excel`、`CharacterDialogExcel` 等主线表**一个都不在这个包、也不在任何其他包**（全量精确匹配，§3.2）。
- 结论：**剧情文本已全部迁到"按场景拆包"的 `*_scenario.bytes` / `*_pNN_[dn].bytes` 单条目包里**，`ScenarioScriptField1Excel` 才是当前实际生效的剧情表。这也解释了为什么 `ScenarioScriptField1ExcelTable` 类型在 il2cpp metadata 里存在、而 `ScenarioScriptMain1Excel` **完全搜不到**（`global-metadata.dat` 里 `ScenarioScriptMain1Excel` = 0 命中，`ScenarioScriptField1Excel` = 命中）。

### 下一步（推荐执行顺序）

1. 确定单场景包 payload 的 MemoryPack 容器 → 立刻能导出全量日文。
2. 写 `extract_story.py`（新）：遍历 6440 个 ZIP → 按 `_d`/`_n` 分类 → 按 §4.2 解密 → 按 §5.1 schema 抽 `TextJp` / `VoiceJp` / `PopupFileName` → 按 `ScenarioReplayExcel` 的组织结构落盘。
3. 交叉验证：把 `sb_01_schale_p01_scenario.bytes`（3.5 MB，Vol.1 夏莱）解出的第一段日文与游戏内文本比对。
4. 补 `ScenarioCharacterNameExcel` + `ScenarioBGNameExcel`，把 slot 数值还原成可读剧本（说话人 + 背景 + 表情 + 语音 key）。

---

## 附：本次侦查产物

| 路径 | 内容 |
|---|---|
| `_work/entries_all.tsv` | 6440 ZIP × 6961 条目的 `磁盘名\t条目名\t未压缩大小\t压缩大小` |
| `_work/entries_scenario.tsv` | 关键词命中的 52 条剧情条目 |
| `_work/scan_summary.json` | 后缀模式直方图 / 条目数分布 / 关键词统计 |
| `_work/header_survey.json` | 三大目录文件头普查 |
| `_work/catalog_records.json` | `TableCatalog.bytes` 解析出的 6444 条逻辑包记录（name/size/hash/crc/flag） |
| `_work/excel_table_locations.json` | `*exceltable.bytes` 全量归属（唯一命中 19 MB 表包） |
| `_work/multi_entry_bundles.json` | 10 个多条目包 + 各自密码 seed 探测结果 |
| `_work/il2cpp_field_schemas.json` | 从 metadata 提取的 FlatData 类型字段表 |
| `_work/tablepack_password.txt` | 表包密码 seed 记录：`Excel.zip` |
| `_work/media_catalog_records.json` / `media_records.json` | `MediaCatalog.bytes` 解析中间产物 |
| `_work/` 下 `*.py` | 全部只读侦查脚本（scan_entries / parse_catalog2 / il2cpp_schema / extract_scenario / probe_big …） |

---

## 附二：一页速查（给后续自动化解包用）

```
【剧情正文在哪】
  BlueArchive_Data\StreamingAssets\TableBundles\<u64>_<u32>          ← 加密 ZIP，一个条目一个场景包
  条目名示例：sb_01_schale_p01_scenario.bytes
             8322306_01_02_forestriver_p01_d.bytes
             rb_03_chesed_p01_d_scenario.bytes

【怎么开】
  seed = 条目名去掉 ".bytes" + ".zip"
  pwd  = base64(MersenneTwister(xxh32(seed)).NextBytes(15))
  data = zipfile.ZipFile(path).read(entry, pwd=pwd)
  多条目表包：seed = "Excel.zip"（表）/ "Battle.zip"（战斗）

【里面是什么】
  单场景包  → ScenarioScriptField1ExcelTable
              DataList: [ {SelectionGroup, Sound, Transition, BGName, BGEffect,
                           PopupFileName, ScriptKr, TextJp, VoiceJp} ]
              日文 = slot 7 "TextJp"；语音 key = slot 8 "VoiceJp"
  Excel 表包 → 先 XOR(表类名, raw)，再交给 FlatData\<Xxx>Table.GetRootAs()

【不要指望的地方】
  MediaPatch\      = 立绘/BGM/语音 OGG/L2D（JPEG/OGG/PNG/MP4）
  AssetBundles\    = UnityFS 模型动画材质
  主剧情 Excel 表  = 本客户端已删除，不存在
```

