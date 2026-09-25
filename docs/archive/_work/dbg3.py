import sys
sys.path.insert(0, r"C:\OneDrive\MikaMisono\docs\archive\_work")
import fb_dump as F

d = F.read_entry("10001900114910089910_1704857403", "8322306_01_02_forestriver_p01_d.bytes")
print("len", len(d))
for w in range(0, 28, 4):
    root = w + F.u32(d, w)
    ok = 8 <= root < len(d) - 8
    f = F.fields_of(d, root, 0) if ok else None
    print("w=%2d u32=%d root=%s inrange=%s fields=%s" % (w, F.u32(d, w), root, ok, f))
    if f:
        for slot, o in f.items():
            ds, L, _ = F.read_vec(d, o)
            print("    slot", slot, "vec len", L, "ds", ds)
print("origin_for:", F.origin_for(d))
