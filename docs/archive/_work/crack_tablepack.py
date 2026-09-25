"""Crack the TableBundles password for the table-pack bundles.

For the scenario bundles the seed is `<entry stem>.zip`. For the multi-entry
table packs (e.g. the 19 MB one holding scenarioscriptfield1exceltable.bytes)
the seed is something else - enumerate plausible candidates.
"""
import os, sys, zipfile, json
sys.path.insert(0, r"C:\OneDrive\MikaMisono\assets\blue-archive")
from lib.MersenneTwister import MersenneTwister
from lib.XXHashService import CalculateHash
from base64 import b64encode

TB = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\TableBundles"
CAT = r"C:\Users\MisonoMika\AppData\Local\Temp\table_zip_names.txt"

disk = sys.argv[1] if len(sys.argv) > 1 else "16300795542385574620_4128271700"
entry = sys.argv[2] if len(sys.argv) > 2 else "scenarioscriptfield1exceltable.bytes"

logical = [l.strip() for l in open(CAT, encoding="utf-8") if l.strip()]
logical_set = set(logical)
print("catalog logical names:", len(logical_set))

z = zipfile.ZipFile(os.path.join(TB, disk))
names = z.namelist()
print("entries(%d): %s" % (len(names), names[:10]))

def pw(seed):
    return b64encode(MersenneTwister(CalculateHash(seed)).NextBytes(15))

cands = []
stem = entry[:-6]
cands += [stem, stem + ".zip", stem + ".bytes"]
for l in logical:
    b = l[:-4] if l.endswith(".zip") else l
    cands += [l, b]

hit = None
for seed in cands:
    try:
        with zipfile.ZipFile(os.path.join(TB, disk)) as zz:
            d = zz.read(names[0], pwd=pw(seed))
        hit = (seed, len(d), d[:16].hex())
        break
    except Exception:
        continue
print("result:", hit)
if hit:
    with open(r"C:\OneDrive\MikaMisono\docs\archive\_work\tablepack_password.txt", "w", encoding="utf-8") as f:
        f.write("%s\t%s\t%s\n" % (disk, entry, hit[0]))
