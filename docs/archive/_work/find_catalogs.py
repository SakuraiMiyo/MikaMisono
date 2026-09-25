"""Locate media/TableCatalog bytes, test candidate passwords on one bundle (read-only)."""
import os, struct, json, re, subprocess, sys
sys.path.insert(0, r"C:\OneDrive\MikaMisono\assets\blue-archive")

BASE = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets"
OUT = r"C:\OneDrive\MikaMisono\docs\archive\_work"

# 1) what catalogs exist anywhere?
found = []
for dirpath, dirnames, filenames in os.walk(BASE):
    for fn in filenames:
        if "atalog" in fn or fn.lower().endswith((".db", ".sqlite")):
            p = os.path.join(dirpath, fn)
            found.append((os.path.relpath(p, BASE), os.path.getsize(p), open(p, "rb").read(8).hex()))
    # don't descend forever
print("catalogs found:")
for f in found:
    print("  ", f)

json.dump(found, open(os.path.join(OUT, "catalogs_found.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
