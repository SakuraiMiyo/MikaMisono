"""Extract & parse scenario episode scripts (read-only)."""
import os, sys, zipfile, json, re, glob
from base64 import b64encode
sys.path.insert(0, r"C:\OneDrive\MikaMisono\assets\blue-archive")
from lib.MersenneTwister import MersenneTwister
from lib.XXHashService import CalculateHash
import flatbuffers
import FlatData

TB = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\TableBundles"
OUT = r"C:\OneDrive\MikaMisono\docs\archive\_work"

lower = {k.lower(): v for k, v in FlatData.__dict__.items()}

def pw(seed):
    return b64encode(MersenneTwister(CalculateHash(seed)).NextBytes(15))

def read_bundle(disk, entry):
    with zipfile.ZipFile(os.path.join(TB, disk)) as z:
        stem = entry[:-6]
        return z.read(entry, pwd=pw(stem + ".zip"))

def dump_fb(buf, cls, limit=8):
    root = cls.GetRootAs(buf)
    n = root.ValuesLength() if hasattr(root, "ValuesLength") else None
    out = []
    for i in range(min(n or 0, limit)):
        e = root.Values(i)
        d = {}
        for name in dir(e):
            if name.startswith("_") or name in ("Init",):
                continue
            attr = getattr(e, name)
            if not callable(attr):
                continue
            try:
                v = attr()
            except Exception:
                continue
            if callable(v):
                continue
            d[name] = v
        out.append(d)
    return n, out

data = read_bundle("10001900114910089910_1704857403", "8322306_01_02_forestriver_p01_d.bytes")
print("bytes:", len(data))
cls = lower["scenarioscriptfield1excel"]
n, rows = dump_fb(data, cls, 5)
print("row count:", n)
print(json.dumps(rows, ensure_ascii=False, indent=1)[:4000])
