"""Robust lineariser for TableCatalog.bytes / MediaCatalog.bytes (read-only).

Hypothesis (MemoryPack):
  [int32 N][string CatalogName]
  N * { [string Name][long Size][ulong Hash?][uint Crc][bool IsBuiltin] }
  [int32 M][string ...]  (second section)

Walk with lookahead + resync; report alignment.
"""
import struct, json, os, re, collections, sys

OUT = r"C:\OneDrive\MikaMisono\docs\archive\_work"
P = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\TableBundles\Catalog\TableCatalog.bytes"
data = open(P, "rb").read()
n = len(data)

def rd_str(off):
    if off + 4 > n:
        return None
    L = struct.unpack_from("<i", data, off)[0]
    if L < 0 or L > 4096 or off + 4 + L > n:
        return None
    try:
        s = data[off+4:off+4+L].decode("utf-8")
    except UnicodeDecodeError:
        return None
    if any(ord(c) < 0x09 for c in s):
        return None
    if "\x00" in s:
        return None
    return s, L, off + 4 + L

def looks_like_name(s):
    if not s or len(s) < 3:
        return False
    if not re.search(r"[A-Za-z0-9]", s):
        return False
    if not re.fullmatch(r"[A-Za-z0-9_\-\.\/]+", s):
        return False
    return True

# --- pass 1: collect every offset where a plausible filename string starts ---
cands = []
i = 0
while i + 4 <= n:
    r = rd_str(i)
    if r and looks_like_name(r[0]):
        cands.append((i, r[0], r[1], r[2]))
        i = r[2]
    else:
        i += 1

print("candidate strings:", len(cands))
ext = collections.Counter(os.path.splitext(c[1])[1].lower() for c in cands)
print("extensions:", ext.most_common(20))

# after each candidate name, check for the numeric record tail
recs = []
for (off, s, L, end) in cands:
    if end + 20 > n:
        continue
    size = struct.unpack_from("<q", data, end)[0]
    h = struct.unpack_from("<q", data, end + 8)[0]
    crc = struct.unpack_from("<I", data, end + 16)[0]
    flag = data[end + 20] if end + 21 <= n else None
    ok = (0 < size < 3_000_000_000) and (0 <= crc < 2**32) and (flag in (0, 1))
    if ok:
        recs.append({"offset": off, "name": s, "size": size, "h": h, "h_hex": "%016x" % (h & (2**64-1)), "crc": crc, "flag": flag, "end": end+21})

print("records with numeric tail:", len(recs))
diskish = [r for r in recs if re.fullmatch(r"\d{5,25}_\d{1,12}", r["name"])]
print("disk-shaped names:", len(diskish))
zipish = [r for r in recs if r["name"].endswith(".zip")]
print("zip names:", len(zipish))

with open(os.path.join(OUT, "catalog_records.json"), "w", encoding="utf-8") as f:
    json.dump({"total_bytes": n, "string_candidates": len(cands), "records": recs}, f, ensure_ascii=False, indent=1)

for r in recs[:12]:
    print(r["size"], r["h_hex"], r["crc"], r["flag"], r["name"])
