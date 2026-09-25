"""Password-derivation probe against a known scenario bundle (read-only)."""
import os, sys, zipfile, traceback
from base64 import b64encode
sys.path.insert(0, r"C:\OneDrive\MikaMisono\assets\blue-archive")
from lib.MersenneTwister import MersenneTwister
from lib.XXHashService import CalculateHash

TB = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\TableBundles"
disk = "10001900114910089910_1704857403"
entry = "8322306_01_02_forestriver_p01_d.bytes"
p = os.path.join(TB, disk)

def pw(seed):
    return b64encode(MersenneTwister(CalculateHash(seed)).NextBytes(15))

base = entry[:-6]
stem = base.rsplit("_", 1)[0]
cands = {
    "entry+zip": entry[:-6] + ".zip",
    "entry": entry,
    "base": base,
    "base+zip": base + ".zip",
    "diskname": disk,
    "diskname+zip": disk + ".zip",
}
for k, v in list(cands.items()):
    cands[k + "|bslash"] = "GameData\\Scenario\\" + v
    cands[k + "|slash"] = "GameData/Scenario/" + v

print("computed password for entry.zip:", pw(entry[:-6] + ".zip"))
z = zipfile.ZipFile(p)
names = z.namelist()
print("entries:", names)

for k, seed in cands.items():
    try:
        with zipfile.ZipFile(p) as zz:
            d = zz.read(names[0], pwd=pw(seed))
        print("OK   %-16s seed=%r -> %d bytes head=%s" % (k, seed, len(d), d[:24].hex()))
    except Exception as e:
        if k in ("entry+zip", "entry", "base+zip", "diskname"):
            print("fail %-16s %s" % (k, type(e).__name__))

# brute: does the mersenne twister output ever start with a plausible zip password?
# also try: password = the EntryName as-is but zip requires bytes; check if setpassword works with raw
try:
    with zipfile.ZipFile(p) as zz:
        zz.setpassword(b"password")
        print("raw probe done")
except Exception as e:
    print(e)
