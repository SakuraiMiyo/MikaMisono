#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blue Archive (JP) StreamingAssets 哈希文件名 <-> 逻辑名 映射工具
================================================================
反推出的公式（已在 10701 个文件上 100% 验证）：

    磁盘文件名 = f"{xxh64(规范化逻辑名, seed=0)}_{crc32(文件全部字节)}"

  * 第一段：XXH64（seed = 0），输入 = 逻辑 bundle 名
      - TableBundles : 逻辑名需 **转小写** 后再哈希
      - MediaPatch   : 逻辑名 **原样**（区分大小写）
      - AssetBundles : 磁盘上是明文名；其哈希名同规则（见 BundlePackingInfo.bytes）
  * 第二段：CRC32（zlib.crc32）of **整个文件的字节流**（不是解压后内容）

逻辑名清单来源（Catalog 里只存逻辑名，不存哈希名）：
  * TableBundles/Catalog/TableCatalog.bytes  -> TableBundles
  * MediaPatch/Catalog/MediaCatalog.bytes    -> MediaPatch
两个文件都是「4 字节小端长度前缀 + ASCII 字符串」的连续记录流。

用法:
  python ba-bundle-name-map.py            # 构建映射 + 全量校验
  python ba-bundle-name-map.py --dump out.json
"""
import os
import re
import sys
import json
import zlib
import struct
import argparse

import xxhash

DEFAULT_ROOT = r'C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets'


def read_len_prefixed_strings(path, max_len=400):
    """解析「int32 LE 长度 + ASCII」记录流，返回全部字符串（含重复）。"""
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
        off += 1
    return out


def hash_segment(logical_name):
    """逻辑名 -> 磁盘文件名第一段（XXH64, seed=0）。"""
    return xxhash.xxh64(logical_name.encode('utf-8')).intdigest()


def crc_segment(path):
    """文件 -> 磁盘文件名第二段（CRC32 of file bytes）。"""
    c, CH = 0, 1 << 22
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(CH), b''):
            c = zlib.crc32(chunk, c)
    return c & 0xffffffff


def scan_disk(directory):
    """{xxh64 段: (crc 段, 文件名, 完整路径)}"""
    out = {}
    for name in os.listdir(directory):
        fp = os.path.join(directory, name)
        if not os.path.isfile(fp):
            continue
        m = re.match(r'^(\d+)_(\d+)$', name)
        if m:
            out[int(m.group(1))] = (int(m.group(2)), name, fp)
    return out


def build_map(root=DEFAULT_ROOT, verify_crc=True):
    """返回 {(kind, disk_filename): logical_name}，并记录校验统计。"""
    specs = [
        ('table', 'TableBundles', os.path.join('TableBundles', 'Catalog', 'TableCatalog.bytes'), True),
        ('media', 'MediaPatch', os.path.join('MediaPatch', 'Catalog', 'MediaCatalog.bytes'), False),
    ]
    result, stats = {}, {}
    for kind, sub, cat_rel, lower in specs:
        disk = scan_disk(os.path.join(root, sub))
        names = read_len_prefixed_strings(os.path.join(root, cat_rel))
        mapped, crc_ok, crc_bad, collisions = {}, 0, 0, 0
        for s in names:
            key = s.lower() if lower else s
            h = hash_segment(key)
            if h in disk:
                if h in mapped and mapped[h] != s:
                    collisions += 1
                mapped[h] = s
        for a, name in mapped.items():
            crc, fname, fp = disk[a]
            if verify_crc:
                if crc_segment(fp) == crc:
                    crc_ok += 1
                else:
                    crc_bad += 1
            result[(kind, fname)] = name
        stats[kind] = dict(catalog_strings=len(names), disk_files=len(disk),
                           mapped=len(mapped), unmapped=len(set(disk) - set(mapped)),
                           crc_verified=crc_ok, crc_failed=crc_bad, name_collisions=collisions,
                           case_normalization='lowercase' if lower else 'as-is')
    return result, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=DEFAULT_ROOT)
    ap.add_argument('--dump')
    ap.add_argument('--no-crc', action='store_true')
    args = ap.parse_args()

    mapping, stats = build_map(args.root, verify_crc=not args.no_crc)
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    print('\n%-56s %s' % ('逻辑名 (catalog)', '磁盘文件名'))
    for (kind, fname), logical in list(mapping.items())[:10]:
        print('%-56s %s' % (logical, fname))
    print('\n总映射条目:', len(mapping))
    if args.dump:
        json.dump({f: v for (k, f), v in mapping.items()},
                  open(args.dump, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
        print('已写出', args.dump)


if __name__ == '__main__':
    main()
