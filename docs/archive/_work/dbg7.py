"""Definitive structural search for the FlatBuffer in a scenario payload."""
import sys, struct
sys.path.insert(0, r"C:\OneDrive\MikaMisono\docs\archive\_work")
from extract_scenario import read_entry

d = read_entry("10001900114910089910_1704857403", "8322306_01_02_forestriver_p01_d.bytes")
n = len(d)


def u16(o): return struct.unpack_from("<H", d, o)[0]
def i32(o): return struct.unpack_from("<i", d, o)[0]
def u32(o): return struct.unpack_from("<I", d, o)[0]


print("len", n)
print("printable:", "".join(chr(b) if 32 <= b < 127 else "." for b in d[:120]))
words = [u16(i) for i in range(0, 64, 2)]
print("words[0..31]:", words)

# find any vtable: uint16 size in {4,6,8,...,40} whose slots are all in [4, 2000]
print("\nvalid vtables in first 4096 bytes:")
vtabs = []
for v in range(0, min(4096, n - 4), 2):
    sz = u16(v)
    if sz < 4 or sz > 40 or (sz - 4) % 2 or v + sz > n:
        continue
    sl = [u16(v + 4 + 2 * i) for i in range((sz - 4) // 2)]
    if all(x == 0 or 4 <= x <= 4000 for x in sl) and any(sl):
        # a real vtable has monotone non-decreasing slot offsets
        nz = [x for x in sl if x]
        if nz == sorted(nz):
            vtabs.append((v, sz, sl))
print("  count:", len(vtabs))
for v, sz, sl in vtabs[:40]:
    print("   vt=%5d size=%2d slots=%s" % (v, sz, sl))

# for each vtable, is there a table T such that T - i32(T) == v ?
print("\ntable candidates whose soffset resolves to a known vtable:")
vset = {v for v, _, _ in vtabs}
for T in range(4, min(4096, n - 8), 2):
    so = i32(T)
    if T - so in vset:
        v, sz, sl = next(x for x in vtabs if x[0] == T - so)
        fields = {i: T + x for i, x in enumerate(sl) if x}
        info = []
        for i, fo in fields.items():
            p = fo + u32(fo) if fo + 4 <= n else -1
            if 0 <= p < n - 4:
                info.append("s%d->off%d(u32=%d,len=%d)" % (i, p, u32(fo), u32(p)))
            else:
                info.append("s%d->oob" % i)
        print("   vt=%5d T=%5d soffset=%d %s" % (v, T, so, info[:6]))
