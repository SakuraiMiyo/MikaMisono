"""Map which TableBundles zip physically contains each *exceltable.bytes,
using the entry names visible in the (unencrypted) central directory."""
import os, json, collections

OUT = r"C:\OneDrive\MikaMisono\docs\archive\_work"
TSV = os.path.join(OUT, "entries_all.tsv")
TB = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\TableBundles"

targets = ["localizescenarioexceltable", "scenarioscriptmain1exceltable",
           "scenarioscriptmain2exceltable", "scenarioscriptmain3exceltable",
           "characterscriptexceltable", "characterdialogexceltable",
           "scenarioscriptfavor1exceltable", "scenarioscriptgroup1exceltable",
           "scenarioscriptevent1exceltable", "localizecharexceltable"]
hits = collections.defaultdict(list)
all_excel = collections.defaultdict(list)
by_disk = collections.Counter()

for line in open(TSV, encoding="utf-8"):
    parts = line.rstrip("\n").split("\t")
    if len(parts) < 3:
        continue
    disk, entry, size = parts[0], parts[1], int(parts[2])
    low = entry.lower()
    if low.endswith("exceltable.bytes"):
        all_excel[disk].append((entry, size))
        for t in targets:
            if low == t + ".bytes":
                hits[t].append((disk, entry, size))

print("disks with *exceltable.bytes entries:")
for d, lst in sorted(all_excel.items(), key=lambda kv: -len(kv[1])):
    print("  %-24s %3d entries  total=%d" % (d, len(lst), sum(x[1] for x in lst)))
print()
for t in targets:
    print("%-34s %s" % (t, hits.get(t, "NOT FOUND")))

json.dump({k: v for k, v in hits.items()},
          open(os.path.join(OUT, "excel_table_locations.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump({k: v[:0] for k, v in all_excel.items()},
          open(os.path.join(OUT, "excel_disks.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
