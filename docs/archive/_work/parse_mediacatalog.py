"""Parse MediaCatalog.bytes (per-record leading byte-length) -> logical name + trailing ints."""
import struct, json, os, collections

P = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\MediaPatch\Catalog\MediaCatalog.bytes"
OUT = r"C:\OneDrive\MikaMisono\docs\archive\_work"
MP = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\MediaPatch"

data = open(P, "rb").read()
n = len(data)

def rd(off):
    L = struct.unpack_from("<i", data, off)[0]
    assert 0 <= L <= 4096, (off, L)
    return data[off+4:off+4+L].decode("utf-8"), off + 4 + L

recs = []
off = 0
while off + 4 <= n:
    total = struct.unpack_from("<i", data, off)[0]
    end = off + 4 + total
    if total <= 0 or end > n:
        print("stop at", off, "total", total)
        break
    body = off + 4
    a, o = rd(body)
    b, o = rd(o)
    nums = struct.unpack_from("<QQQ", data, o)
    extra = end - (o + 24)
    recs.append({"path": a, "name": b, "n": list(nums), "extra_bytes": extra, "record_len": total})
    off = end

print("records:", len(recs), "consumed", off, "of", n)

disk = set(fn for fn in os.listdir(MP) if os.path.isfile(os.path.join(MP, fn)))
print("disk files:", len(disk))
m = [0, 0, 0]
for r in recs:
    for i in range(3):
        if str(r["n"][i]) in disk:
            m[i] += 1
print("trailing int matches disk filenames: n0=%d n1=%d n2=%d" % tuple(m))

# try concatenations
forms = collections.Counter()
for r in recs:
    for i in range(3):
        for j in range(3):
            if i != j and ("%d_%d" % (r["n"][i], r["n"][j])) in disk:
                forms[(i, j)] += 1
print("pairs matching disk:", forms.most_common(5))

print(json.dumps(recs[:3], ensure_ascii=False, indent=1))
json.dump(recs, open(os.path.join(OUT, "media_catalog_records.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
