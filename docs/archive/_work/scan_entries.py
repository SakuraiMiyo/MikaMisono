"""Read-only scan of TableBundles central directories (no decryption).

Emits:
  entries_all.tsv      disk_name \t entry_name \t uncompressed_size \t compressed_size
  entries_scenario.tsv disk_name \t entry_name          (keyword-filtered)
  scan_summary.json    counts + suffix histogram + keyword hits
"""
import os, re, json, zipfile, sys, collections, traceback

ROOT = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\TableBundles"
OUT = r"C:\OneDrive\MikaMisono\docs\archive\_work"

KEYWORDS = ["scenario", "dialog", "localize", "story", "script", "talk", "message"]

all_f = open(os.path.join(OUT, "entries_all.tsv"), "w", encoding="utf-8", newline="\n")
scen_f = open(os.path.join(OUT, "entries_scenario.tsv"), "w", encoding="utf-8", newline="\n")

suffix_hist = collections.Counter()
files = 0
bad = []
bad_entries_per_zip = []
keyword_hits = collections.Counter()
total_entries = 0

for name in sorted(os.listdir(ROOT)):
    p = os.path.join(ROOT, name)
    if not os.path.isfile(p):
        continue
    files += 1
    try:
        with zipfile.ZipFile(p) as z:
            infos = z.infolist()
    except Exception as e:
        bad.append((name, repr(e)))
        continue
    ents = [i.filename for i in infos]
    bad_entries_per_zip.append((name, len(ents)))
    for i in infos:
        n = i.filename
        total_entries += 1
        all_f.write("%s\t%s\t%d\t%d\n" % (name, n, i.file_size, i.compress_size))
        base = n.rsplit("/", 1)[-1]
        # suffix pattern: strip leading numeric-ish scene prefixes
        m = re.match(r"^(.*?)(\.bytes|\.json|\.txt|\.csv|\.xml|)$", base)
        core = m.group(1) if m else base
        tail = base[len(core):] if m else ""
        # pattern = last two underscore-separated tokens + ext
        toks = core.split("_")
        pat = "_".join(toks[-2:]) + tail if len(toks) >= 2 else core + tail
        suffix_hist[pat] += 1
        low = n.lower()
        hit = [k for k in KEYWORDS if k in low]
        if hit:
            for k in hit:
                keyword_hits[k] += 1
            scen_f.write("%s\t%s\t%d\n" % (name, n, i.file_size))

all_f.close()
scen_f.close()

summary = {
    "tablebundles_files_scanned": files,
    "total_entries": total_entries,
    "unreadable_zips": bad[:50],
    "unreadable_zip_count": len(bad),
    "suffix_pattern_histogram": suffix_hist.most_common(60),
    "keyword_entry_counts": dict(keyword_hits),
    "empty_zips": sum(1 for _, c in bad_entries_per_zip if c == 0),
    "zip_entry_count_histogram": collections.Counter(
        "0" if c == 0 else "1" if c == 1 else "2-5" if c <= 5 else "6-20" if c <= 20 else "21-100" if c <= 100 else ">100"
        for _, c in bad_entries_per_zip
    ),
}
with open(os.path.join(OUT, "scan_summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
print(json.dumps(summary, ensure_ascii=False, indent=2)[:6000])
