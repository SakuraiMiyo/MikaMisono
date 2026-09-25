"""Find the main Excel.zip DataTableBundle: a bundle whose first entry is
XOR-obfuscated with CreateKey(<SomeExcelTable>)."""
import os, sys, struct, zipfile, json
from base64 import b64encode
sys.path.insert(0, r"C:\OneDrive\MikaMisono\assets\blue-archive")
from lib.MersenneTwister import MersenneTwister
from lib.XXHashService import CalculateHash
from lib.TableEncryptionService import XOR, CreateKey
import FlatData

TB = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\TableBundles"
OUT = r"C:\OneDrive\MikaMisono\docs\archive\_work"

names = [k for k in dir(FlatData) if k.endswith("ExcelTable") and not k.startswith("_")]
print("candidate table classes:", len(names))


def pw(seed):
    return b64encode(MersenneTwister(CalculateHash(seed)).NextBytes(15))


PWD = pw("Excel.zip")


def plausible(buf):
    if len(buf) < 16:
        return False
    root = struct.unpack_from("<I", buf, 0)[0]
    if not (4 <= root <= 64) or root + 4 > len(buf):
        return False
    v = root - struct.unpack_from("<i", buf, root)[0]
    if not (0 <= v <= len(buf) - 4):
        return False
    sz = struct.unpack_from("<H", buf, v)[0]
    return 4 <= sz <= 400 and (sz - 4) % 2 == 0


hits = []
files = [f for f in os.listdir(TB) if os.path.isfile(os.path.join(TB, f))]
print("scanning", len(files), "bundles")
for i, fn in enumerate(files):
    p = os.path.join(TB, fn)
    if os.path.getsize(p) < 20000:
        continue
    try:
        with zipfile.ZipFile(p) as z:
            nl = z.namelist()
            if not nl:
                continue
            head = z.read(nl[0], pwd=PWD)[:256]
    except Exception:
        continue
    stem = nl[0][:-6] if nl[0].endswith(".bytes") else nl[0]
    for cls in (stem.capitalize(),):
        pass
    for cls in names:
        try:
            x = XOR(cls[:-5], head)
        except Exception:
            continue
        if plausible(x):
            hits.append((fn, nl[0], cls, os.path.getsize(p), len(nl)))
            print("HIT", hits[-1])
            break

json.dump(hits, open(os.path.join(OUT, "main_excel_hits.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("total hits:", len(hits))
