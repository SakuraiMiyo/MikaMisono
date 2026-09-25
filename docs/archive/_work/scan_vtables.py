"""Scan the big _scenario.bytes payloads for legitimate flatbuffers vtables
(slot offsets must be non-decreasing and >= header size) and report them."""
import sys, struct, collections
sys.path.insert(0, r"C:\OneDrive\MikaMisono\docs\archive\_work")
from extract_scenario import read_entry


def u16(b, o): return struct.unpack_from("<H", b, o)[0]
def i32(b, o): return struct.unpack_from("<i", b, o)[0]
def u32(b, o): return struct.unpack_from("<I", b, o)[0]


def find_vtables(b, limit=200000):
    out = []
    for v in range(0, min(limit, len(b) - 4), 2):
        sz = u16(b, v)
        if sz < 4 or sz > 64 or (sz - 4) % 2 or v + sz > len(b):
            continue
        sl = [u16(b, v + 4 + 2 * i) for i in range((sz - 4) // 2)]
        nz = [x for x in sl if x]
        if not nz:
            continue
        if nz != sorted(nz):
            continue
        if nz[0] < sz:
            continue
        if nz[-1] > 4000:
            continue
        out.append((v, sz, sl))
    return out


for disk, entry in [
    ("3152370782941368777_3453525187", "sb_01_schale_p01_scenario_nodelayer.bytes"),
    ("8096923742589028906_2683815145", "sb_01_schale_p01_scenario.bytes"),
]:
    d = read_entry(disk, entry)
    print("== %s (%d bytes)" % (entry, len(d)))
    vts = find_vtables(d)
    print("   vtables found:", len(vts), vts[:8])
    print("   head:", d[:48].hex(" "))
    print("   root u32@0:", u32(d, 0), " i32@0:", i32(d, 0))
