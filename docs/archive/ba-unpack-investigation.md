# Blue Archive JP — 哈希文件名 ↔ 原始名 映射公式 侦查报告

- **目标**：反推 `StreamingAssets` 中 `<大数>_<数>` 形式文件名的生成公式
- **结论**：**已找到，且在全部 10,701 个文件上 100% 验证通过**
- **日期**：2026-02（本次会话）
- **环境**：Windows / PowerShell 7 / Python 3.12.12 (`C:\SoftWare\Astrbot\backend\python\python.exe`)，依赖 `xxhash`
- **只读侦查**：未修改、未移动、未解包任何游戏文件

---

## 0. 结论速览

```
磁盘文件名 = f"{XXH64(规范化逻辑名, seed=0)}_{CRC32(文件全部字节)}"
```

| 目录 | 逻辑名来源 | 规范化方式 | 验证结果 |
|------|-----------|-----------|---------|
| `TableBundles\` | `TableBundles\Catalog\TableCatalog.bytes` | **转小写** | **6440 / 6440** ✅ |
| `MediaPatch\` | `MediaPatch\Catalog\MediaCatalog.bytes` | **原样（区分大小写）** | **4261 / 4261** ✅ |
| `AssetBundles\` | `AssetBundles\Catalog\BundlePackingInfo.bytes`（明文配对表，无需反推） | 原样（含 `.bundle`） | **26,778 组配对，明文可读** ✅ |

- 第一段 = XXH64(seed=0) of 逻辑名 → 20 位十进制（唯一值 6440/4261，**零碰撞**）
- 第二段 = `zlib.crc32(整个文件字节流)` → 10 位十进制（**10701/10701 全部吻合，0 例外**）
- **Catalog 里不存哈希名**：`TableCatalog.bytes` / `MediaCatalog.bytes` 中既没有 ASCII 数字串（`\d{12,20}` 命中 0 次），也没有对应 uint64 的 binary 表示（大小端均未命中）。所以哈希名是**游戏运行时算出来的**，必须靠反推——这也解释了为什么目录解析路线走不通。

### 为什么之前的尝试全部失败：**大小写**

这是唯一的差别：

```
xxh64("Excel.zip") =  3622299440866786438   ← 之前测的（catalog 里的原始写法）
xxh64("excel.zip") = 16300795542385574620   ← 磁盘上真实存在的文件
```

而 `16300795542385574620_4128271700` **正是你原帖里举的那个例子文件名**。也就是说：公式没错、哈希函数没错、seed 没错，唯一的偏差是**哈希输入必须是小写后的逻辑名**。Catalog 保留了原始大小写，而构建时哈希用的是小写形式。

---

## 1. 可直接运行的 Python 片段

完整可复用脚本：`ba-bundle-name-map.py`（与本报告同目录，已全量跑通）

```python
import os, re, zlib, struct, json
import xxhash

ROOT = r'C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets'

def read_len_prefixed_strings(path, max_len=400):
    """解析「int32 LE 长度前缀 + ASCII」记录流，返回全部字符串（含重复）。"""
    blob = open(path, 'rb').read()
    out, off, n = [], 0, len(blob)
    while off + 4 <= n:
        ln = struct.unpack_from('<i', blob, off)[0]
        if 1 <= ln <= max_len and off + 4 + ln <= n:
            s = blob[off + 4:off + 4 + ln]
            if all(32 <= c < 127 for c in s):
                out.append(s.decode('ascii'))
                off += 4 + ln
                continue
        off += 1                      # 未对齐则滑动 1 字节重新同步
    return out

def crc_segment(fp, chunk=1 << 22):
    c = 0
    with open(fp, 'rb') as fh:
        for blk in iter(lambda: fh.read(chunk), b''):
            c = zlib.crc32(blk, c)
    return c & 0xffffffff

# ---------- 方向 A：磁盘名 -> 逻辑名（实用方向） ----------
def build_reverse_map(root=ROOT):
    """{磁盘文件名: 逻辑名}，覆盖 TableBundles + MediaPatch 全部 10701 个文件。"""
    specs = [('TableBundles', r'TableBundles\Catalog\TableCatalog.bytes', True),
             ('MediaPatch',   r'MediaPatch\Catalog\MediaCatalog.bytes',   False)]
    mapping = {}
    for sub, cat, lower in specs:
        d = os.path.join(root, sub)
        disk = {int(m.group(1)): m.group(0)
                for f in os.listdir(d)
                if (m := re.match(r'^(\d+)_\d+$', f))}
        for s in read_len_prefixed_strings(os.path.join(root, cat)):
            key = s.lower() if lower else s          # ← 关键：Table 小写，Media 原样
            a = xxhash.xxh64(key.encode('utf-8')).intdigest()
            if a in disk:
                mapping[disk[a]] = s
    return mapping

# ---------- 方向 B：逻辑名 -> 第一段（第二段需读文件本身） ----------
def hash_segment(logical_name, lowercase):
    key = logical_name.lower() if lowercase else logical_name
    return xxhash.xxh64(key.encode('utf-8')).intdigest()

if __name__ == '__main__':
    m = build_reverse_map()
    print(len(m), 'entries')
    for k in list(m)[:5]:
        print(' ', k, '->', m[k])
    # 正向自检
    name, lower = 'Excel.zip', True
    a = hash_segment(name, lower)
    fp = os.path.join(ROOT, 'TableBundles', f'{a}_4128271700')
    assert os.path.exists(fp) and crc_segment(fp) == 4128271700
    print('forward check OK:', fp)
```

> **注意方向性**：第一段可以纯靠逻辑名算出，但**第二段（CRC32）必须读文件字节**——它无法从名字推导。
> 所以「逻辑名 → 磁盘文件名」只在已知 CRC 时成立（例如从服务器的 packing 清单拿到）；
> 而离线解包需要的「磁盘文件名 → 逻辑名」是**完全可解**的，就是方向 A。

---

## 2. 验证结果

### 2.1 全量统计（`ba-bundle-name-map.py` 输出）

```json
{
  "table": { "catalog_strings": 13452, "disk_files": 6440, "mapped": 6440, "unmapped": 0,
             "crc_verified": 6440, "crc_failed": 0, "name_collisions": 0,
             "case_normalization": "lowercase" },
  "media": { "catalog_strings": 12783, "disk_files": 4261, "mapped": 4261, "unmapped": 0,
             "crc_verified": 4261, "crc_failed": 0, "name_collisions": 0,
             "case_normalization": "as-is" }
}
```

- 覆盖 **10,701 / 10,701** 个文件，**0 个未映射**，**0 个名字碰撞**
- **10,701 / 10,701** 个文件的 `CRC32(file bytes)` 等于文件名第二段，**0 例外**
- Catalog 中大量字符串是**资产键**（`rawdata/table/excel/*.bytes`、`audio/voc_jp/...`、`uis/...`），不参与匹配；只有哈希命中的那些才是 bundle 逻辑名

### 2.2 成功配对样例（每一行都做过独立复验：文件存在 + xxh64 段吻合 + CRC32 段吻合）

| # | 逻辑名 | 磁盘文件名 | 大小(B) | xxh64 | crc32 |
|---|--------|-----------|--------|-------|-------|
| 1 | `Excel.zip` | `16300795542385574620_4128271700` | 19,109,176 | OK | OK |
| 2 | `ExcelDB.db` | `6993339912994747134_1745771760` | 212,639,744 | OK | OK |
| 3 | `Battle.zip` | `1858308081688323146_3447461123` | 179,007 | OK | OK |
| 4 | `RootMotion.zip` | `12478936438010851834_4172722046` | 99,083 | OK | OK |
| 5 | `ConquestMap.zip` | `17586053117680496933_2160747873` | 49,944 | OK | OK |
| 6 | `sb_01_mainstreet_p01_d.zip` | `2403037476982693755_3521553508` | 350,423 | OK | OK |
| 7 | `1011101_01_s1_01_mainstreet_p01_d.zip` | `17691958144066159012_1353796851` | 1,428 | OK | OK |
| 8 | `LogicEffectDataDBSchema.db` | `4354043109159736559_651527683` | 10,010,624 | OK | OK |
| 9 | `LevelSkillDataDBSchema.db` | `2733092781725905578_4094553949` | 21,282,816 | OK | OK |
| 10 | `JP_Airi.zip`（MediaPatch） | `5581597052211433951_3375441397` | 2,143,288 | OK | OK |

### 2.3 副产品：AssetBundles 的映射是**明文**的

`AssetBundles\Catalog\BundlePackingInfo.bytes`（4,664,302 B）里直接存着成对记录：

```
academy-_mxload-prefabs-2025-07-02_assets_all_965806563.bundle
9009846755877532686_965806563
```

- 28,831 条 `.bundle` 名（26,778 个唯一值 = 磁盘上 26,778 个 bundle 全部覆盖）
- 28,831 条 `<哈希>_<crc>` 名，**26,778 个唯一值**
- 同一公式成立：`xxh64(含 .bundle 的完整名, seed=0)` = 哈希段（**26,778/26,778**）
- `crc` 段 = 真名尾部数字 = `crc32(文件字节)`（**28,831/28,831**，另抽 200 个文件独立复算 CRC32 → 200/200）
- 该目录**磁盘上用的是明文名**，哈希名只在 packing 表里（推测用于 CDN 下载）
- 表里还有 `r95`、`FullPatch_000.zip` … `FullPatch_018.zip` 等字符串

结论：**AssetBundles 完全不需要爆破**——配对表就在文件里；只有 TableBundles / MediaPatch 需要反推，而反推已完成。

---

## 3. 验证 / 推翻的假设清单

| # | 假设 | 结论 | 证据（命令与输出摘要） |
|---|------|------|----------------------|
| 1 | 第二段是文件大小 | ❌ **推翻** | `s1_sets.py`：`B == size` → `False`；样例 `(size=1834, B=1704857403)` |
| 2 | 第二段是 CRC32(文件内容) | ✅ **成立** | 全量：TableBundles `ok=6440 bad=0`，MediaPatch `ok=4261 bad=0`；AssetBundles 抽 200 → 200/200 |
| 3 | `catalog_Remote.json` 能给磁盘名 | ❌ **推翻** | `s7_exhaustive.py`：173,774 个 `m_InternalIds`（去前缀、原样/小写）对 A_tb / A_mp 命中 **0**。该目录只索引 `AssetBundles\` |
| 4 | Catalog 里存了哈希名（ASCII） | ❌ **推翻** | `TableCatalog.bytes` / `MediaCatalog.bytes` 中 `\d{12,20}` 命中 **0** 次 |
| 5 | Catalog 里存了哈希名（binary uint64） | ❌ **推翻** | 对 `16300795542385574620` 等 3 个值做 8 字节大小端搜索，`present: False` |
| 6 | `m_EntryDataString` / `m_ExtraDataString` 藏着 bundle 名 | ❌ **推翻** | 它们是标准 Addressables 的 key/bucket/entry/extra 表，指向 `m_InternalIds`；而 `m_InternalIds` 只含 `AssetBundles\*.bundle` |
| 7 | 哈希是 xxh32 / crc32 / md5 / sha1 / fnv / murmur / spooky / xxh3 | ❌ **推翻** | `s4_brute.py`：对 26,778 组真值配对，14 个基础哈希 + 各摘要算法 6 种切片 + 多 seed 变体，**仅 xxh64(seed=0) 命中 800/800**，其余全 0 |
| 8 | `xxh64(逻辑名) = 第一段` | ✅ **成立** | `s3/s11`：AssetBundles 26,778/26,778；TableBundles 6,440/6,440；MediaPatch 4,261/4,261 |
| 9 | 哈希输入需要大小写规范化 | ✅ **成立（且是关键）** | TableBundles：原始大小写命中 **4,770/6,454**，小写命中 **6,436/6,454**；MediaPatch 反之（原样 **4,261/4,261**，小写仅 287） |
| 10 | 你的「用磁盘哈希名当密码」为何 Bad password | ✅ **已定位（Python 侧原因）** | Zip 的 general purpose flag = `0x0009`（bit0 加密 + **bit3 有 data descriptor**），而本地头 DOS time = `0`。Python `zipfile` 在 bit3 置位时用 `_raw_time >> 8` 当校验字节 → 恒为 `0x00`，与密文头末字节不符 → **无论密码对错都会报 Bad password**。详见 §4 |
| 11 | ZIP 密码 = `base64(MT19937(xxh32(逻辑名basename)).NextBytes(15))` | ⚠️ **未能复现** | 见 §4：换用**正确的逻辑名**后，手写 ZipCrypto + 1280 种配方 × 200 个文件，无一命中 |

---

## 4. 未解决项：ZIP 密码派生（超出本次任务范围，但已定位到关键线索）

本次任务（映射公式）已完成，但顺带做的密码验证有以下发现，**值得你调整方向**：

### 4.1 Python `zipfile` 的假失败（确定）

所有 TableBundles 加密条目都是 `flag = 0x0009`、`method = 8`、**本地头 DOS time = 0x0000**：

```
504b0304 1400 0900 0800 0000 0000 efe060f2 2d580500 28481300 1c000000 "sb_01_mainstreet_p01_d.bytes" 64c4be24 5c8e78bc 09307a13 ...
```

Python 的 `_ZipDecrypter` 在 `flag_bits & 0x8` 时用 `(zinfo._raw_time >> 8) & 0xff` 作校验字节。这里 raw_time = 0，而密文头第 12 字节解密后并不等于 0 → **`RuntimeError: Bad password` 恒成立**，与密码正确性无关。
→ **不要再用 `zipfile.read(pwd=...)` 判断密码对错**，必须手写 ZipCrypto（或改用不校验该字节的实现）。

### 4.2 用正确逻辑名重试，仍未命中（不确定原因）

手写标准 ZipCrypto（`key0/1/2` 初值 `0x12345678/0x23456789/0x34567890`，`crc32` 表更新）后，做了两级测试：

1. **校验字节多文件一致性**（`s14_pw_consensus.py`）：150 个加密 zip × 672 种配方，最高命中 **5/150**（随机基线 1.17）→ 属噪声
2. **不依赖校验字节的 inflate 判据**（`s15_inflate_consensus.py`）：200 个加密 zip × **1280** 种配方，判据为「解密后能否成功 `zlib.decompress(-15)`」，最高 **1/200** → 全部为偶然

配方空间覆盖：

- 名称形态 8 种：逻辑名原样 / 小写 / 去扩展名 / 去扩展名+小写 / zip 内条目名 / 条目名去扩展名 / 磁盘哈希名 / 磁盘哈希名第一段
- 种子函数 5 种：`xxh32`、`xxh32(seed=1)`、`xxh64 低32`、`xxh64(seed=1) 低32`、`crc32`
- MT 取字节方式 8 种：Python `Random.randbytes`、`getrandbits` 大端、标准 MT19937 小端/大端、以及取 `(byte)word` / `>>8` / `>>16` / `>>24`（对应 C# 各类 `NextBytes` 实现）
- 编码 4 种：`base64`、`base64` 去 padding、原始 15 字节、hex

**结论**：在「MT19937 的 15 字节 → base64 作密码」这个配方族内，无论名称形态、种子、取字节方式怎么组合，都无法解开这些 zip。可能原因（按可能性排序）：

1. 种子哈希的**输入不是 bundle 逻辑名**，而是别的字符串（例如某个内部 ID、或带目录的完整路径）
2. MT 不是标准 MT19937（例如 C# 的 `System.Random` 减法发生器，或某个具体 NuGet 实现，其 `NextBytes` 语义与上面 8 种都不同）
3. 生成了不止 15 字节 / 密码用的是别的截取方式
4. 这些 zip 的加密**不是标准 ZipCrypto**（写入方把 bit3 置位同时又填了 CRC、并把 time 清零，行为不符合任何标准 zip 工具；校验字节约定可能被改写）

### 4.3 好消息：**不需要密码也能拿到条目清单**

ZIP 的本地头 / central directory **不加密**。实测可直接读出条目名、原始大小、压缩大小、CRC：

```
2403037476982693755_3521553508  ->  entry sb_01_mainstreet_p01_d.bytes   raw 1263656  comp 350253  crc 0xf260e0ef
17691958144066159012_1353796851 ->  entry 1011101_01_s1_01_mainstreet_p01_d.bytes raw 5214 comp 1236 crc 0xef51a5bd
16300795542385574620_4128271700 ->  entry animationblendtable.bytes (Excel.zip, 多条目)
```

即：**文件名映射 + 条目清单都能拿到，只有条目内容需要密码。** 这已经把「知道哪个包是什么」的问题彻底解决了。

### 4.4 其他未解释的小文件

| 文件 | 内容 | 状态 |
|------|------|------|
| `TableBundles\Catalog\TableCatalog.hash` | `1075120550\r\n` | 未解释（10 位十进制，疑似 catalog 自身校验/版本） |
| `MediaPatch\Catalog\MediaCatalog.hash` | `3910120436\r\n` | 同上 |
| `AssetBundles\Catalog\BundlePackingInfo.hash` | `2139923031\r\n` | 同上 |
| `aa\settings.json` (184 B) `aa\AddressablesLink\link.xml` | — | 未检查，与映射无关 |

### 4.5 Catalog 二进制格式（附带说明）

`TableCatalog.bytes` / `MediaCatalog.bytes` 不是 base64 的 Addressables catalog，而是紧凑二进制，记录形如
`<int32 负类型码><int32 小端长度><ASCII 字符串>`，未对齐时滑动 1 字节重新同步即可稳定解析：

```
TableCatalog : off=9   pre=-11 len=10 'ExcelDB.db'      / off=28 pre=-11 len=10 'ExcelDB.db'
               off=359 pre=-10 len=9  'Excel.zip'       / off=377 pre=-10 len=9 'Excel.zip'
               off=418 pre=-46 len=45 'rawdata/table/excel/animationblendtable.bytes' ...
MediaCatalog : off=9   'audio/voc_jp/jp_airi/jp_airi'  off=46 'GameData\Audio\VOC_JP\JP_Airi.zip'  off=87 'JP_Airi.zip'
```

可见 TableCatalog 是 `(资产键, bundle 名)` 成对；MediaCatalog 是 `(资产键, bundle 路径, bundle 名)` 三元组，**只有第三个（basename）参与哈希**。

解析得到：TableCatalog **13,452** 条、MediaCatalog **12,783** 条字符串；其中哈希命中的分别是 **6,440** / **4,261**。

---

## 5. 其他确认的事实

- `TableBundles\` 实际 **6,440** 个文件（不是 6440 以外的数）；`MediaPatch\` 实际 **4,261** 个文件（原帖写 4259，另有 2 组 CRC 段重复，但第一段 4261 个全唯一）
- `AssetBundles\` **26,778** 个明文名 bundle
- TableBundles 中 **6,436/6,440** 以 `PK` 开头；剩下 4 个正好是 4 个 `.db` schema 包（`ExcelDB.db`、`LogicEffectDataDBSchema.db`、`LevelSkillDataDBSchema.db`、`SkillVisualEffectDataDBSchema.db`），它们不是 zip（`ExcelDB.db` 的包实测 `BadZipFile`）
- MediaPatch 中只有 **302/4,261** 以 `PK` 开头（对应 MediaCatalog 里 302 个 `*.zip` 名，如 `JP_Airi.zip`）；其余 3,959 个是 `pv-v.mp4` / `pv-a.ogg` / `popup02.png` 等裸媒体文件
- 你导出的 `table_zip_names.txt` 里 6,454 个 `.zip` 名中，有 **18 个以 `TablePatchPack_` 开头**（`TablePatchPack_GroundGrid_1..13`、`GroundNodeLayer_1`、`GroundStage_1` 及 3 个 `Prologue_` 变体）在本机**没有对应 bundle**（未随本安装下载）；反过来本机的 4 个 `.db` 包不在那份 `.zip` 清单里
- `TablePatchPack_*` 的 18 个名字在「小写 + xxh64」下同样算不出磁盘文件 → 确认是**清单有而磁盘无**，不是公式例外

---

## 6. 产出物

| 文件 | 说明 |
|------|------|
| `C:\OneDrive\MikaMisono\docs\archive\ba-unpack-investigation.md` | 本报告 |
| `C:\OneDrive\MikaMisono\docs\archive\ba-bundle-name-map.py` | 可复用工具：构建映射 + 全量 CRC 校验 + `--dump` |
| `C:\OneDrive\MikaMisono\docs\archive\ba-bundle-name-map.json` | **10,701 条** `磁盘文件名 → 逻辑名` 映射清单（UTF-8，可直接给解包脚本用） |
| `C:\Users\MisonoMika\AppData\Local\Temp\ba_inv\pairs.json` | 26,778 组 AssetBundles 真名↔哈希名配对（从 BundlePackingInfo.bytes 解析） |
| `C:\Users\MisonoMika\AppData\Local\Temp\ba_inv\s1..s15_*.py` | 全部侦查脚本（集合交叉、穷举匹配、哈希爆破、ZipCrypto 验证） |

---

## 7. 下一步建议

**映射公式这件事已经结束**——可以直接复用 `ba-bundle-name-map.py` / `ba-bundle-name-map.json`。按优先级：

1. **直接用映射清单做解包**：`ba-bundle-name-map.json` 已把 10,701 个磁盘名对回逻辑名；条目清单也能不从密码获得（§4.3）。如果目标只是「搞清楚每个包是什么 / 提取未加密的 3,959 个 MediaPatch 裸媒体」，现在就能做。
2. **修正密码验证方式**：不要再依赖 `zipfile(pwd=)`（§4.1 已证明它会无条件报 Bad password）。改用 `pyzipper`，或用手写 ZipCrypto + `zlib.decompressobj(-15)` 成败作判据（`s15_inflate_consensus.py` 里现成实现）。
3. **重新确认密码派生式的来源**：既然输入现在是**已知正确**的逻辑名，而你原来的配方仍不命中，那么问题不在名字上。建议回到配方本身核对三处：① 种子哈希喂进去的到底是哪个字符串（可能不是 bundle 名）；② 所谓 `MersenneTwister` 具体是哪个实现（C# `System.Random` 的 `NextBytes` 与任何 MT 都不同）；③ 是否真的取 15 字节。可考虑直接用 `TableBundles` 里**同一逻辑名、不同 CRC** 的两个包做交叉验证。
4. **如果目标是解密全部内容**：与其继续猜密码，不如走「内存/运行时 hooks」路线——游戏解密后再落盘的位置（或游戏自己的 `ZipFile` 调用点）比离线爆破更省力；本报告已确认离线侧只剩密码这一个未知量。
5. **可选**：把 `*.hash` 三个 10 位数字（§4.4）拿去和 `xxh32` 对一遍，若成立则说明它们也是同一套哈希体系的自校验，可顺便确认公式族。

---

## 附：公式速查卡

```python
import xxhash, zlib
# 逻辑名 -> 第一段
A = xxhash.xxh64(name.lower().encode()).intdigest()   # TableBundles
A = xxhash.xxh64(name.encode()).intdigest()           # MediaPatch / AssetBundles(含 .bundle)
# 文件 -> 第二段
B = zlib.crc32(open(path,'rb').read()) & 0xffffffff
# 于是
assert f"{A}_{B}" == os.path.basename(path)
```
