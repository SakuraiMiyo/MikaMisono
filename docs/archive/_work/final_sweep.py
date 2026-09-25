"""Final evidence sweep (read-only):
 - MediaPatch content classification by magic
 - AssetBundles: look for Localization / scenario TextAsset bundles
 - TableBundles entry-name pattern stats from the earlier scan
"""
import os, json, collections, re, sys

BASE = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets"
OUT = r"C:\OneDrive\MikaMisono\docs\archive\_work"
res = {}

MAGIC = {
    b"\xff\xd8\xff\xe0": "JPEG",
    b"\xff\xd8\xff\xe1": "JPEG(exif)",
    b"\x89PNG": "PNG",
    b"OggS": "OGG",
    b"PK\x03\x04": "ZIP",
    b"UnityFS": "UnityFS",
    b"RIFF": "WAV/RIFF",
    b"ID3": "MP3/ID3",
    b"\x00\x00\x00\x1c": "MP4(ftyp)",
    b"\x01\xa5\x10\x00": "MediaCatalog",
}

for sub in ("MediaPatch", "AssetBundles"):
    d = os.path.join(BASE, sub)
    if not os.path.isdir(d):
        continue
    hist = collections.Counter()
    examples = {}
    for dirpath, dirnames, filenames in os.walk(d):
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            try:
                with open(p, "rb") as f:
                    h = f.read(8)
            except OSError:
                hist["<err>"] += 1
                continue
            k = None
            for m, name in MAGIC.items():
                if h.startswith(m):
                    k = name
                    break
            if k is None:
                k = "other:%s" % h[:4].hex()
            hist[k] += 1
            examples.setdefault(k, os.path.relpath(p, d))
    res[sub] = {"histogram": hist.most_common(20), "examples": examples}

# AssetBundles: which bundle names mention localization / scenario / text
ab = os.path.join(BASE, "AssetBundles")
hits = []
for dirpath, dirnames, filenames in os.walk(ab):
    for fn in filenames:
        low = fn.lower()
        if re.search(r"localiz|scenario|script|text|dialog|story", low):
            hits.append((os.path.relpath(os.path.join(dirpath, fn), ab), os.path.getsize(os.path.join(dirpath, fn))))
res["assetbundle_name_hits"] = sorted(hits)[:400]
res["assetbundle_name_hit_count"] = len(hits)

with open(os.path.join(OUT, "final_sweep.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)

print(json.dumps({k: (v if k != "assetbundle_name_hits" else v[:25]) for k, v in res.items()},
                 ensure_ascii=False, indent=1))
