import sys, struct
sys.path.insert(0, r"C:\OneDrive\MikaMisono\docs\archive\_work")
from extract_scenario import read_entry, u16, i32, u32, vt, slots_of, get_vec

d = read_entry("10001900114910089910_1704857403", "8322306_01_02_forestriver_p01_d.bytes")
print("len", len(d))
for w in range(0, 20, 4):
    cand = w + u32(d, w)
    print("w=%2d u32=%d cand=%d vt=%s slots=%s" % (w, u32(d, w), cand, vt(d, cand) if 12 <= cand < len(d) - 8 else "-",
          (slots_of(d, cand) if 12 <= cand < len(d) - 8 else "-")))
print()
for pos in (12, 16, 20, 24, 28, 32, 36, 40):
    print("pos", pos, "i32", i32(d, pos), "vt", vt(d, pos), "slots", slots_of(d, pos))
