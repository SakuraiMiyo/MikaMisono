"""Parse the MemoryPack-ish TableCatalog.bytes structure (read-only).

Strategy: the blob interleaves signed-length-prefixed strings with fixed
records. We linearise it by walking: try to read an i32 length L at the cursor;
if -1000 <= L <= 1000 (|L| <= 200) and the following |L| bytes decode as valid
ASCII/UTF-8 identifier, treat it as a string token; otherwise treat the next
4 bytes as an int32 scalar and advance 4.
Then group tokens/ints into records to see the shape.
"""
import struct, json, os, re, collections

P = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\TableBundles\Catalog\TableCatalog.bytes"
OUT = r"C:\OneDrive\MikaMisono\docs\archive\_work"

data = open(P, "rb").read()

def is_ident(b):
    if not b:
        return False
    # allow printable ascii + utf8 continuation
    try:
        s = b.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return all(32 <= ord(c) < 0x7f or ord(c) > 0x7f for c in s)

tokens = []  # (offset, kind, value)
i = 0
n = len(data)
while i + 4 <= n:
    L = struct.unpack_from("<i", data, i)[0]
    if 0 < L <= 200 and i + 4 + L <= n and is_ident(data[i+4:i+4+L]):
        tokens.append((i, "s", data[i+4:i+4+L].decode("utf-8")))
        i += 4 + L
    else:
        tokens.append((i, "i", L))
        i += 4

# every 4 bytes covered?
covered = sum((4 + len(t[2].encode('utf8'))) if t[1] == "s" else 4 for t in tokens)
print("bytes", n, "tokens", len(tokens), "covered", covered)

strs = [t for t in tokens if t[1] == "s"]
print("string tokens:", len(strs))
print("first 40 tokens:", [(t[1], t[2]) for t in tokens[:40]])

svals = [t[2] for t in strs]
ext = collections.Counter(os.path.splitext(s)[1].lower() for s in svals)
print("string extensions:", ext.most_common(20))
print("distinct strings:", len(set(svals)))

# look for the disk-file-shaped tokens: digits_digits
diskish = [s for s in set(svals) if re.fullmatch(r"\d{5,25}_\d{1,12}", s)]
print("diskish token count:", len(diskish), diskish[:10])

with open(os.path.join(OUT, "catalog_tokens.json"), "w", encoding="utf-8") as f:
    json.dump({
        "total_bytes": n,
        "token_count": len(tokens),
        "string_count": len(strs),
        "distinct_strings": len(set(svals)),
        "extensions": ext.most_common(30),
        "diskish_count": len(diskish),
        "diskish_sample": diskish[:20],
        "tokens_head": [[t[0], t[1], t[2]] for t in tokens[:200]],
    }, f, ensure_ascii=False, indent=2)

with open(os.path.join(OUT, "catalog_strings.txt"), "w", encoding="utf-8") as f:
    for t in tokens:
        f.write(("S\t%s\n" % t[2]) if t[1] == "s" else ("I\t%d\n" % t[2]))
