"""Locate the table region in a scenario payload by testing every offset as a
table position and scoring the resulting slot set."""
import sys, struct
sys.path.insert(0, r"C:\OneDrive\MikaMisono\docs\archive\_work")
from extract_scenario import read_entry

d = read_entry("10001900114910089910_1704857403", "8322306_01_02_forestriver_p01_d.bytes")
n = len(d)


def u16(o): return struct.unpack_from("<H", d, o)[0]
def i32(o): return struct.unpack_from("<i", d, o)[0]
def u32(o): return struct.unpack_from("<I", d, o)[0]


print("len", n)
print("tail 64:", d[-64:].hex(" "))
print("printable tail:", "".join(chr(b) if 32 <= b < 127 else "." for b in d[-120:]))

best = []
for pos in range(8, n - 8):
    so = i32(pos)
    v = pos - so
    if not (0 <= v <= n - 4):
        continue
    sz = u16(v)
    if sz < 4 or sz > 80 or (sz - 4) % 2 or v + sz > n or v + sz > pos:
        continue
    sl = [u16(v + 4 + 2 * i) for i in range((sz - 4) // 2)]
    nz = [x for x in sl if x]
    if not nz or nz != sorted(nz) or nz[0] < sz or nz[-1] > n - pos:
        continue
    best.append((pos, v, sz, sl, so))

print("table candidates:", len(best))
for b in best[:20]:
    print("   pos=%d vt=%d size=%d slots=%s soffset=%d" % b)
