"""Dump Excel.zip table bundles using the recovered password, parse with FlatData."""
import os, sys, zipfile, json, re
from base64 import b64encode

sys.path.insert(0, r"C:\OneDrive\MikaMisono\assets\blue-archive")
from lib.MersenneTwister import MersenneTwister
from lib.XXHashService import CalculateHash
from lib.TableEncryptionService import XOR
import FlatData

TB = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\TableBundles"
OUT = r"C:\OneDrive\MikaMisono\docs\archive\_work"
lower = {k.lower(): v for k, v in FlatData.__dict__.items()}
JP = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")


def pw(seed):
    return b64encode(MersenneTwister(CalculateHash(seed)).NextBytes(15))


PWD = pw("Excel.zip")


def reopen(disk):
    return zipfile.ZipFile(os.path.join(TB, disk))


def read(disk, entry):
    with reopen(disk) as z:
        return z.read(entry, pwd=PWD)


def dump(disk, entry, limit=5):
    raw = read(disk, entry)
    stem = entry[:-6]
    cls = lower.get(stem)
    print("== %s / %s  %d bytes  class=%s" % (disk, entry, len(raw), cls.__name__ if cls else None))
    if cls is None:
        print("   (no generated class; head=%s)" % raw[:24].hex(" "))
        return None, []
    data = XOR(cls.__name__[:-5], raw)
    root = cls.GetRootAs(data)
    n = root.DataListLength()
    print("   rows=%d" % n)
    rows = []
    for i in range(min(n, limit)):
        e = root.DataList(i)
        d = {}
        for name in dir(e):
            if name.startswith("_") or name == "Init":
                continue
            try:
                v = getattr(e, name)
                if callable(v):
                    continue
            except Exception:
                continue
            d[name] = v
        rows.append(d)
    for r in rows:
        print("   ", json.dumps(r, ensure_ascii=False)[:600])
    return root, rows


if __name__ == "__main__":
    disk = "16300795542385574620_4128271700"
    with reopen(disk) as z:
        names = z.namelist()
    print("entries:", len(names))
    for n in names:
        print("  ", n)
    for e in [x for x in names if "scenario" in x or "dialog" in x or "localize" in x or "story" in x]:
        dump(disk, e, 3)
