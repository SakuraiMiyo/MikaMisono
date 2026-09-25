"""Anchor-based scan of MediaCatalog.bytes: find string offsets, then figure record stride."""
import struct, json, os, collections

P = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\MediaPatch\Catalog\MediaCatalog.bytes"
data = open(P, "rb").read()
n = len(data)

offs = []  # offsets where a length-prefixed utf8-ish string starts
i = 0
while i + 4 < n:
    L = struct.unpack_from("<i", data, i)[0]
    if 3 <= L <= 512 and i + 4 + L <= n:
        try:
            s = data[i+4:i+4+L].decode("utf-8")
        except UnicodeDecodeError:
            i += 1; continue
        if all(0x20 <= ord(c) < 0x7f for c in s) and any(c.isalnum() for c in s) and "\\" not in s[:1]:
            if any(c in s for c in ("/", "\\", ".zip", ".bytes", ".json")) or s.isalnum():
                offs.append((i, L, s))
                i += 4 + L
                continue
    i += 1

print("string offsets:", len(offs))
print("head:", offs[:12])

# stride histogram between consecutive *record-start* candidates:
# a record start is a string offset whose predecessor string is a filename followed by 24 bytes of ints
stride = collections.Counter()
for k in range(len(offs) - 1):
    d = offs[k+1][0] - offs[k][0]
    stride[d] += 1
print("stride top20:", stride.most_common(20))

# find pairs (path,name) with 24 bytes of ints after name, then see the next record start
recs = []
for k, (o, L, s) in enumerate(offs):
    if k + 1 >= len(offs):
        break
    o2, L2, s2 = offs[k+1]
    end = o2 + 4 + L2
    if end + 24 <= n:
        nums = struct.unpack_from("<QQQ", data, end)
        recs.append((o, s, s2, nums, end + 24))
print("candidate (path,name,int24) units:", len(recs))
for r in recs[:6]:
    print(r[0], r[1][:50], "|", r[2][:50], "|", r[3], "| next", r[4])

# what follows the ints?
after = collections.Counter()
for r in recs[:20000]:
    nxt = r[4]
    if nxt + 8 <= n:
        after[data[nxt:nxt+4].hex()] += 1
print("4 bytes after int-triple (top):", after.most_common(8))
