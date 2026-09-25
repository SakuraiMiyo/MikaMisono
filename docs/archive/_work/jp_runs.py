"""Pull every UTF-16LE / UTF-8 text run out of a decrypted scenario payload."""
import sys, re, os, json
sys.path.insert(0, r"C:\OneDrive\MikaMisono\docs\archive\_work")
from extract_scenario import read_entry

OUT = r"C:\OneDrive\MikaMisono\docs\archive\_work"
JP = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff\uff00-\uffef]")

disk = sys.argv[1] if len(sys.argv) > 1 else "10001900114910089910_1704857403"
entry = sys.argv[2] if len(sys.argv) > 2 else "8322306_01_02_forestriver_p01_d.bytes"
d = read_entry(disk, entry)

runs = []
seen = set()


def add(off, enc, s):
    s = s.strip("\x00")
    if len(s) < 2 or not JP.search(s):
        return
    if (off, s) in seen:
        return
    seen.add((off, s))
    runs.append({"offset": off, "enc": enc, "text": s})


# UTF-16LE runs: pairs of (byte, 0x00) or (byte, 0x30-0x9f / 0xff)
for m in re.finditer(b"(?:[\x00-\xff][\x00\x20-\xff])+", d):
    raw = m.group()
    if len(raw) % 2:
        raw = raw[:-1]
    if len(raw) < 4:
        continue
    try:
        s = raw.decode("utf-16-le")
    except UnicodeDecodeError:
        continue
    if JP.search(s) and all(c.isprintable() or c in "\r\n\t" for c in s):
        add(m.start(), "utf-16-le", s)

# UTF-8 runs
for m in re.finditer(rb"(?:[\x20-\x7e]|[\xc2-\xf4][\x80-\xbf]+|[\n\t])+", d):
    raw = m.group()
    if len(raw) < 6:
        continue
    try:
        s = raw.decode("utf-8")
    except UnicodeDecodeError:
        continue
    if JP.search(s) and all(c.isprintable() or c in "\r\n\t" for c in s):
        add(m.start(), "utf-8", s)

print("japanese runs:", len(runs))
with open(os.path.join(OUT, "jp_runs_%s.txt" % entry.replace(".bytes", "")), "w", encoding="utf-8") as f:
    for r in runs:
        f.write("[%06d %s] %s\n" % (r["offset"], r["enc"], r["text"]))
print("wrote", os.path.join(OUT, "jp_runs_%s.txt" % entry.replace(".bytes", "")))
