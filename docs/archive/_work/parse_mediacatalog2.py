"""Resync-walking parser for MediaCatalog.bytes."""
import struct, json, os, collections, re

P = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\MediaPatch\Catalog\MediaCatalog.bytes"
OUT = r"C:\OneDrive\MikaMisono\docs\archive\_work"
MP = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\MediaPatch"
data = open(P, "rb").read()
n = len(data)
disk = set(fn for fn in os.listdir(MP) if os.path.isfile(os.path.join(MP, fn)))

def read_str(off):
    if off + 4 > n: return None
    L = struct.unpack_from("<i", data, off)[0]
    if L < 0 or L > 512 or off + 4 + L > n: return None
    try:
        s = data[off+4:off+4+L].decode("utf-8")
    except UnicodeDecodeError:
        return None
    if any(ord(c) < 0x20 for c in s): return None
    return s, off + 4 + L

recs = []
off = 4
while off + 4 < n:
    r1 = read_str(off)
    if not r1:
        off += 1; continue
    r2 = read_str(r1[1])
    if not r2:
        off += 1; continue
    o = r2[1]
    if o + 24 > n:
        break
    nums = struct.unpack_from("<QQQ", data, o)
    recs.append({"off": off, "path": r1[0], "name": r2[0], "n": list(nums)})
    off = o + 24

print("records:", len(recs))
print("first 3:", json.dumps(recs[:3], ensure_ascii=False))
m = [0,0,0]
for r in recs:
    for i in range(3):
        if str(r["n"][i]) in disk: m[i] += 1
print("trailing int == disk filename: n0=%d n1=%d n2=%d" % tuple(m))
forms = collections.Counter()
for r in recs:
    for i in range(3):
        for j in range(3):
            if i != j and ("%d_%d" % (r["n"][i], r["n"][j])) in disk:
                forms[(i,j)] += 1
print("pairs matching disk:", forms.most_common(5))
json.dump(recs, open(os.path.join(OUT, "media_catalog_records.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
