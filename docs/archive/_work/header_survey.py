"""Read-only: classify file headers across StreamingAssets subtrees."""
import os, collections, json, sys

BASE = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets"
OUT = r"C:\OneDrive\MikaMisono\docs\archive\_work"

def head(path, n=16):
    with open(path, "rb") as f:
        return f.read(n)

result = {}
for sub in ["TableBundles", "MediaPatch", "AssetBundles"]:
    d = os.path.join(BASE, sub)
    if not os.path.isdir(d):
        result[sub] = {"exists": False}
        continue
    hist = collections.Counter()
    examples = {}
    n_files = 0
    total = 0
    # AssetBundles may be nested; walk
    for dirpath, dirnames, filenames in os.walk(d):
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            n_files += 1
            try:
                sz = os.path.getsize(p)
                total += sz
                h = head(p, 16)
            except Exception as e:
                hist["<error>"] += 1
                continue
            sig = h[:4]
            if sig == b"PK\x03\x04":
                k = "ZIP(PK\\x03\\x04)"
            elif h[:7] == b"UnityFS":
                k = "UnityFS"
            elif h[:8] == b"UnityWeb":
                k = "UnityWeb"
            elif h[:9] == b"CAB-":
                k = "CAB-"
            elif len(h) < 8:
                k = "tiny/empty"
            else:
                k = "other:%s" % h[:4].hex()
            hist[k] += 1
            if k not in examples:
                examples[k] = os.path.relpath(p, d)
    result[sub] = {
        "exists": True,
        "file_count": n_files,
        "total_bytes": total,
        "header_histogram": hist.most_common(20),
        "examples": examples,
    }

with open(os.path.join(OUT, "header_survey.json"), "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(json.dumps(result, ensure_ascii=False, indent=2))
