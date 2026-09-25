"""Fast probe of the big _scenario.bytes bundles: walk rows generically and
record (a) the table positions, (b) the vtable slot sets actually seen,
(c) any recoverable text."""
import sys, struct, json, os, re, collections
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
    return {i: pos + u16(buf, v + 4 + 2 * i) for i in range((sz - 4) // 2) if u16(buf, v + 4 + 2 * i)}


def probe(disk, entry, max_rows=400):
    d = read_entry(disk, entry)
    n = len(d)
    print("== %s / %s (%d bytes)" % (disk, entry, n))
    root = u32(d, 0)
    v, sz = vt_of(d, root)
    print("root=%d vt=%s size=%s slots=%s" % (root, v, sz, slots(d, root)))
    # root slot 0 should be the DataList vector
    rs = slots(d, root)
    if 0 not in rs:
        print("no DataList at slot 0"); return
    o = rs[0]
    p = o + u32(d, o)
    L = u32(d, p)
    ds = p + 4
    print("vector: p=%d len=%d ds=%d  (ds+4*len=%d)" % (p, L, ds, ds + 4 * L))

    slot_sets = collections.Counter()
    first_rows = []
    jp_hits = 0
    for i in range(min(L, max_rows)):
        ep = ds + 4 * i
        if ep + 4 > n: break
        t = ep + u32(d, ep)
        if not (0 <= t < n - 4): continue
        f = slots(d, t)
        slot_sets[tuple(sorted(f))] += 1
        row = {}
        for s, fo in f.items():
            if fo + 8 > n: continue
            # try string (uoffset -> len -> bytes)
            try:
                sp = fo + u32(d, fo)
                if 0 <= sp < n - 4:
                    SL = u32(d, sp)
                    if 0 < SL <= 2000 and sp + 4 + SL <= n:
                        raw = d[sp + 4:sp + 4 + SL]
                        for enc in ("utf-16-le", "utf-8"):
                            try:
                                txt = raw.decode(enc)
                            except UnicodeDecodeError:
                                continue
                            if txt and all(c.isprintable() or c in "\r\n\t\u3000" for c in txt):
                                row["s%d" % s] = (enc, txt)
                                break
            except Exception:
                pass
            if "s%d" % s not in row:
                row["s%d" % s] = ("i", i64(d, fo))
        if any(isinstance(v, tuple) and v[0] != "i" and JP.search(v[1]) for v in row.values()):
            jp_hits += 1
        if len(first_rows) < 12:
            first_rows.append({"i": i, "t": t, **{k: v[1] for k, v in row.items()}})
    print("slot-set histogram:", slot_sets.most_common(6))
    print("jp rows in first %d: %d" % (min(L, max_rows), jp_hits))
    for r in first_rows:
        print("  ", json.dumps(r, ensure_ascii=False)[:400])
    return first_rows


if __name__ == "__main__":
    probe(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 60)
