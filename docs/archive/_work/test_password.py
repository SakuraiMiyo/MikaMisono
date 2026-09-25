"""Test password derivation candidates against a known scenario bundle (read-only)."""
import os, sys, struct, zipfile
from base64 import b64encode
sys.path.insert(0, r"C:\OneDrive\MikaMisono\assets\blue-archive")
from lib.MersenneTwister import MersenneTwister
from lib.XXHashService import CalculateHash

TB = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\TableBundles"

targets = [
    ("10001900114910089910_1704857403", "8322306_01_02_forestriver_p01_d.bytes"),
    ("8096923742589028906_2683815145", "sb_01_schale_p01_scenario.bytes"),
]

def pw(seed_name):
    return b64encode(MersenneTwister(CalculateHash(seed_name)).NextBytes(15))

for disk, entry in targets:
    p = os.path.join(TB, disk)
    if not os.path.isfile(p):
        print("MISSING", p); continue
    base = entry[:-6]  # strip .bytes
    cands = []
    for nm in (entry, base):
        cands += [nm, nm + ".zip", nm + ".bytes", nm.replace("_", "/")]
        cands += ["GameData\\Scenario\\" + nm, "GameData/Scenario/" + nm,
                  "GameData\\" + nm, "GameData/" + nm, disk]
    seen = set()
    z = zipfile.ZipFile(p)
    namelist = z.namelist()
    print("=== %s : entries=%d" % (disk, len(namelist)))
    for nm in cands:
        if nm in seen: continue
        seen.add(nm)
        try:
            pwd = pw(nm)
            with zipfile.ZipFile(p) as zz:
                d = zz.read(namelist[0], pwd=pwd)
            print("  OK  seed=%-60r -> %d bytes  head=%s" % (nm, len(d), d[:16].hex()))
        except Exception as e:
            pass
    print("  done, tried", len(seen), "candidates")
