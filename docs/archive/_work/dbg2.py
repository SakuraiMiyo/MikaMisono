import sys
sys.path.insert(0, r"C:\OneDrive\MikaMisono\docs\archive\_work")
import fb_dump as F

d = F.read_entry("10001900114910089910_1704857403", "8322306_01_02_forestriver_p01_d.bytes")
print("len", len(d), "prefix", F.u32(d, 0))
print("u32 @0,4,8,12:", [F.u32(d, i) for i in (0, 4, 8, 12)])
rp = 4 + F.u32(d, 4)
print("root(4 + u32@4) =", rp)
print("fields_of(root):", F.fields_of(d, rp))
for slot, o in sorted(F.fields_of(d, rp).items()):
    print(" slot", slot, "off", o, "u32", F.u32(d, o))
    try:
        ds, L, _ = F.read_vec(d, o)
        print("   vec ds", ds, "len", L)
        if 0 < L < 10000:
            for i in range(min(L, 4)):
                t = F.elem_table(d, ds, i)
                print("     elem", i, "@", t, F.describe(d, t))
    except Exception as e:
        print("   uoffset? str:", F.decode_text(F.read_str(d, o)))
