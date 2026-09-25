"""Stream-search the 89 MB addressables catalog for bundle names of interest."""
import re, os, json

P = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\catalog_Remote.json"
OUT = r"C:\OneDrive\MikaMisono\docs\archive\_work"

pat = re.compile(rb"([A-Za-z0-9_\-\.]{2,120}?)\.bundle")
keys = [b"excel", b"localize", b"scenario", b"dialog", b"story", b"script"]
found = {}
allb = set()
with open(P, "rb") as f:
    carry = b""
    while True:
        chunk = f.read(1 << 22)
        if not chunk:
            break
        buf = carry + chunk
        for m in pat.finditer(buf):
            name = m.group(1).decode("utf-8", "replace")
            allb.add(name)
            low = name.lower()
            for k in keys:
                if k.decode() in low:
                    found.setdefault(k.decode(), set()).add(name)
        carry = buf[-256:]

print("total distinct bundle names:", len(allb))
for k, v in found.items():
    print("== %s: %d" % (k, len(v)))
    for n in sorted(v)[:25]:
        print("   ", n)

json.dump({k: sorted(v) for k, v in found.items()},
          open(os.path.join(OUT, "catalog_bundle_names.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
