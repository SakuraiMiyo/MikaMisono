import sys, struct
sys.path.insert(0, r"C:\OneDrive\MikaMisono\docs\archive\_work")
import fb_dump as F

d = F.read_entry("10001900114910089910_1704857403", "8322306_01_02_forestriver_p01_d.bytes")
print("len", len(d))
print("first 24 bytes:", d[:24].hex(" "))
print("u16@8", F.u16(d, 8), "u32@12", F.u32(d, 12))

pos = 12
vt = pos - F.i32(d, pos)
print("pos", pos, "i32", F.i32(d, pos), "vt", vt, "u16(vt)", F.u16(d, vt))
vt2 = pos + F.i32(d, pos)
print("alt vt", vt2, "u16", F.u16(d, vt2))

def raw_fields(buf, pos, vt):
    sz = F.u16(buf, vt)
    out = {}
    for i in range((sz - 4) // 2):
        vo = F.u16(buf, vt + 4 + i * 2)
        if vo:
            out[i] = pos + vo
    return out

print("raw fields(vt=4):", raw_fields(d, pos, 4))
for slot, o in raw_fields(d, pos, 4).items():
    print(" slot", slot, "off", o, "u32", F.u32(d, o))
    try:
        ds, L, _ = F.read_vec(d, o)
        print("    vec ds", ds, "len", L)
        for i in range(min(L, 3)):
            t = F.elem_table(d, ds, i)
            print("      elem", i, "table@", t)
            print("      describe:", F.describe(d, t))
    except Exception as e:
        print("    str?", F.decode_text(F.read_str(d, o)))
