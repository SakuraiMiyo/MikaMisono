"""Locate the main Excel table bundle: try the recovered password on all
multi-entry TableBundles and list which known tables each contains."""
import os, sys, zipfile, json
from base64 import b64encode
sys.path.insert(0, r"C:\OneDrive\MikaMisono\assets\blue-archive")
from lib.MersenneTwister import MersenneTwister
from lib.XXHashService import CalculateHash

TB = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\TableBundles"
OUT = r"C:\OneDrive\MikaMisono\docs\archive\_work"

def pw(seed):
    return b64encode(MersenneTwister(CalculateHash(seed)).NextBytes(15))

# every disk file that has more than one entry, from the earlier scan
multi = [
    "15171489324176746188_1544061357",
    "16300795542385574620_4128271700",
    "12478936438010851834_4172722046",
    "3297747414422744131_1963913160",
    "17586053117680496933_2160747873",
    "5258342604481549157_3631853498",
    "7876225261659261401_2005779007",
    "1858308081688323146_3447461123",
    "7258182013662367530_694028104",
    "13742729995315846359_2534791568",
]

SEEDS = ["Excel.zip", "Module.zip", "Battle.zip"]

report = []
for disk in multi:
    p = os.path.join(TB, disk)
    if not os.path.isfile(p):
        print("missing", disk); continue
    with zipfile.ZipFile(p) as z:
        names = z.namelist()
    rec = {"disk": disk, "size": os.path.getsize(p), "entry_count": len(names), "entries": names}
    rec["seeds_tried"] = {}
    for s in SEEDS:
        try:
            with zipfile.ZipFile(p) as z:
                z.read(names[0], pwd=pw(s))
            rec["seeds_tried"][s] = "OK"
        except Exception as e:
            rec["seeds_tried"][s] = type(e).__name__
    report.append(rec)
    print("%-24s %10d %4d entries  %s" % (disk, rec["size"], len(names), rec["seeds_tried"]))
    print("     first entries:", names[:6])

json.dump(report, open(os.path.join(OUT, "multi_entry_bundles.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
