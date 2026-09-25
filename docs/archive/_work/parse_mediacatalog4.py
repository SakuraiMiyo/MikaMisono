"""Map MediaCatalog records -> disk files via the trailing 32-bit value."""
import struct, json, os, collections

P = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\MediaPatch\Catalog\MediaCatalog.bytes"
MP = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\MediaPatch"
TB = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\TableBundles"
OUT = r"C:\OneDrive\MikaMisono\docs\archive\_work"
data = open(P, "rb").read()
n = len(data)
count0 = struct.unpack_from("<i", data, 0)[0]

def get_str(off):
    L = struct.unpack_from("<i", data, off)[0]
    if not (0 < L <= 4096) or off + 4 + L > n:
        return None
    try:
        s = data[off+4:off+4+L].decode("utf-8")
    except UnicodeDecodeError:
        return None
    return s, off + 4 + L

# trust the three-string-per-record structure: walk record by record
recs = []
off = 4
while off + 4 < n:
    r1 = get_str(off)
    if not r1: break
    r2 = get_str(r1[1])
    if not r2: break
    r3 = get_str(r2[1])
    if not r3: break
    tail_off = r3[1]
    if tail_off + 24 > n: break
    a, b, c = struct.unpack_from("<QQQ", data, tail_off)
    recs.append({"path": r1[0], "full": r2[0], "name": r3[0], "a": a, "b": b, "c": c,
                 "off": off, "end": tail_off + 24})
    off = tail_off + 24

print("records:", len(recs), "consumed", off, "of", n, "count0", count0)

def disk_index(d):
    idx = {}
    for fn in os.listdir(d):
        fp = os.path.join(d, fn)
        if os.path.isfile(fp):
            idx.setdefault(fn, []).append(fp)
    return idx

for label, d in (("MediaPatch", MP), ("TableBundles", TB)):
    idx = disk_index(d)
    hi = collections.Counter()
    for r in recs:
        for k in ("a", "b", "c"):
            v = r[k]
            if str(v) in idx: hi[k] += 1
            if v < 2**32 and ("%d_%d" % (0, v)) in idx: pass
    print(label, "exact whole-name matches by field:", hi.most_common())

# also: 64-bit field may itself be `<u64>_<u32>` collapsed; check whether low32 of `a` pairs with `b`
sample = recs[:5]
for r in sample:
    print(r["name"], "a=%d b=%d c=%d" % (r["a"], r["b"], r["c"]),
          "a_low32=%d" % (r["a"] & 0xffffffff), "a_high32=%d" % (r["a"] >> 32))

json.dump(recs, open(os.path.join(OUT, "media_records.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
