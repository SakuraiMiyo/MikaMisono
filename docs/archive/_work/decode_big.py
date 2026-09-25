"""Decode the big _scenario.bytes bundles (plain flatbuffers, 13-field Field1 table)."""
import sys, struct, json, os, re
sys.path.insert(0, r"C:\OneDrive\MikaMisono\docs\archive\_work")
from extract_scenario import read_entry

OUT = r"C:\OneDrive\MikaMisono\docs\archive\_work"
JP = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")


def u16(b, o): return struct.unpack_from("<H", b, o)[0]
def i32(b, o): return struct.unpack_from("<i", b, o)[0]
def u32(b, o): return struct.unpack_from("<I", b, o)[0]
def i64(b, o): return struct.unpack_from("<q", b, o)[0]


def vt_of(buf, pos):
    v = pos - i32(buf, pos)
    if 0 <= v <= len(buf) - 4:
        sz = u16(buf, v)
        if 4 <= sz <= 400 and (sz - 4) % 2 == 0 and v + sz <= len(buf):
            return v, sz
    return None, None


def slots(buf, pos):
    v, sz = vt_of(buf, pos)
    if v is None:
        return {}
    out = {}
    for i in range((sz - 4) // 2):
        x = u16(buf, v + 4 + 2 * i)
        if x:
            out[i] = pos + x
    return out


def vlen(buf, o):
    p = o + u32(buf, o)
    return p + 4, u32(buf, p)


def s_at(buf, o):
    p = o + u32(buf, o)
    L = u32(buf, p)
    return buf[p + 4:p + 4 + L]


def sval(buf, o):
    raw = s_at(buf, o)
    for enc in ("utf-16-le", "utf-8"):
        try:
            t = raw.decode(enc)
        except UnicodeDecodeError:
            continue
        if t and all(c.isprintable() or c in "\r\n\t\u3000" for c in t):
            return enc, t
    return None, raw[:24].hex()


def walk(buf, disk, entry, limit=None):
    root = u32(buf, 0)
    print("root=%d  vt=%s slots=%s" % (root, vt_of(buf, root), list(slots(buf, root).keys())))
    f = slots(buf, root)
    for slot, o in f.items():
        try:
            ds, L = vlen(buf, o)
        except Exception:
            continue
        print("  root slot %d -> vector len %d (ds=%d)" % (slot, L, ds))
        if not (0 < L < 200000):
            continue
        got = 0
        jp_rows = 0
        samples = []
        for i in range(L):
            ep = ds + 4 * i
            t = ep + u32(buf, ep)
            ff = slots(buf, t)
            if not ff:
                continue
            row = {"_i": i}
            for s, fo in ff.items():
                # decide string vs scalar by testing
                try:
                    enc, val = sval(buf, fo)
                    if enc:
                        row["slot%d" % s] = val
                        continue
                except Exception:
                    pass
                row["slot%d" % s] = u32(buf, fo)
            if any(isinstance(v, str) and JP.search(v) for v in row.values()):
                jp_rows += 1
            if len(samples) < 8 and any(isinstance(v, str) and len(v) > 2 for v in row.values()):
                samples.append(row)
            got += 1
        print("  rows parsed=%d jp_rows=%d" % (got, jp_rows))
        return samples, got, jp_rows
    return [], 0, 0


if __name__ == "__main__":
    disk, entry = sys.argv[1], sys.argv[2]
    d = read_entry(disk, entry)
    print("== %s / %s (%d bytes)" % (disk, entry, len(d)))
    samples, got, jp = walk(d, disk, entry)
    with open(os.path.join(OUT, "big_bundle_samples_%s.json" % os.path.basename(disk)), "w", encoding="utf-8") as fh:
        json.dump(samples, fh, ensure_ascii=False, indent=1)
    for s in samples:
        print(json.dumps(s, ensure_ascii=False)[:400])
