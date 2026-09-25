"""Brute-force discovery of the table/vtable layout in a BA scenario payload."""
import sys, struct, collections
sys.path.insert(0, r"C:\OneDrive\MikaMisono\docs\archive\_work")
from extract_scenario import read_entry

d = read_entry("10001900114910089910_1704857403", "8322306_01_02_forestriver_p01_d.bytes")
n = len(d)


def u16(o): return struct.unpack_from("<H", d, o)[0]
def i32(o): return struct.unpack_from("<i", d, o)[0]
def u32(o): return struct.unpack_from("<I", d, o)[0]


# 1) enumerate all (vt, size) candidates in the first 256 bytes
print("-- vtable candidates (vt, size, slots) in first 256 bytes --")
for v in range(0, 256, 2):
    sz = u16(v)
    if sz < 4 or sz > 80 or (sz - 4) % 2 or v + sz > n:
        continue
    sl = [u16(v + 4 + 2 * i) for i in range((sz - 4) // 2)]
    if all(x == 0 or 4 <= x <= 500 for x in sl):
        print("  vt=%4d size=%3d slots=%s" % (v, sz, sl))

# 2) for every candidate table position, test the hypothesis
#    table_pos = vt + soffset-word stored at table_pos  (0 => vt == table_pos)
print("\n-- tables reachable from vtables --")
for v in range(0, 400, 2):
    sz = u16(v)
    if sz < 4 or sz > 80 or (sz - 4) % 2 or v + sz > n:
        continue
    sl = [u16(v + 4 + 2 * i) for i in range((sz - 4) // 2)]
    if not sl or not all(x == 0 or 4 <= x <= 1000 for x in sl):
        continue
    for pos in set([v] + [v + 4] + [v + x for x in sl if x]):
        if not (0 <= pos < n - 8):
            continue
        f = {}
        ok = True
        for i, x in enumerate(sl):
            if x == 0:
                continue
            fo = pos + x
            if fo + 4 > n:
                ok = False
                break
            f[i] = fo
        if not ok or not f:
            continue
        # does any slot look like a length-prefixed vector or string?
        sig = []
        for i, fo in f.items():
            p = fo + u32(fo)
            if not (0 <= p < n - 4):
                sig.append("oob")
                continue
            L = u32(p)
            ch = d[p + 4:p + 8]
            sig.append("%d:%s" % (L, ch.hex()))
        if any(s.startswith(("2:", "3:", "4:", "5:")) for s in sig):
            print("  vt=%4d table=%4d slots=%s sig=%s" % (v, pos, f, sig))
