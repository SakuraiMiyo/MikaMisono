"""Explicit, fully-traced FlatBuffers walk of a BA scenario .bytes payload."""
import sys, struct
sys.path.insert(0, r"C:\OneDrive\MikaMisono\docs\archive\_work")
from extract_scenario import read_entry

d = read_entry("10001900114910089910_1704857403", "8322306_01_02_forestriver_p01_d.bytes")
n = len(d)
print("len", n)
print("first 64:", d[:64].hex(" "))


def u16(o): return struct.unpack_from("<H", d, o)[0]
def i16(o): return struct.unpack_from("<h", d, o)[0]
def i32(o): return struct.unpack_from("<i", d, o)[0]
def u32(o): return struct.unpack_from("<I", d, o)[0]


print("\n-- header words --")
for w in range(0, 32, 4):
    print("  @%2d u32=%-12d i32=%d" % (w, u32(w), i32(w)))

# Hypothesis H: the root uoffset is at offset 4 and the buffer is a *shifted*
# flatbuffer: table_pos = 4 + uoffset. Also try offset 8 and offset 0.
for w in (0, 4, 8):
    root = w + u32(w)
    if not (0 < root < n - 8):
        print("\nH(w=%d): root %d out of range" % (w, root))
        continue
    print("\nH(w=%d): root=%d" % (w, root))
    print("   i32(root)=%d  u16(root)=%d  u16(root-2)=%d u16(root-4)=%d" % (i32(root), u16(root), u16(root - 2), u16(root - 4)))
    for cand_vt in (root - i32(root), root - 4 - i32(root), root - 8 - i32(root), 4, 0, root - 16):
        if 0 <= cand_vt <= n - 4:
            print("   vt cand %d: size=%d words=%s" % (
                cand_vt, u16(cand_vt),
                [u16(cand_vt + 4 + 2 * k) for k in range(max(0, (u16(cand_vt) - 4) // 2))][:12]))

# Brute force: find any position that behaves like a table whose slots give
# strings, scanning the first 200 bytes.
print("\n-- brute force table scan (first 300 bytes) --")
for pos in range(4, min(300, n - 8), 2):
    for v in range(max(0, pos - 40), pos, 2):
        sz = u16(v)
        if sz < 4 or sz > 60 or (sz - 4) % 2 or v + sz > n or sz > pos - v:
            continue
        slots = {}
        bad = False
        for i in range((sz - 4) // 2):
            svo = u16(v + 4 + i * 2)
            if svo == 0:
                continue
            fo = pos + svo
            if fo + 4 > n:
                bad = True
                break
            slots[i] = fo
        if bad or not slots:
            continue
        # every slot should point at a plausible string or scalar
        strs = 0
        for i, fo in slots.items():
            p = fo + u32(fo)
            if 0 < p < n - 4:
                L = u32(p)
                if 0 < L <= 4000 and p + 4 + L <= n:
                    raw = d[p + 4:p + 4 + L]
                    try:
                        s = raw.decode("utf-16-le")
                        if len(s) > 1 and all(c.isprintable() for c in s):
                            strs += 1
                            continue
                    except Exception:
                        pass
                    try:
                        s = raw.decode("utf-8")
                        if len(s) > 1 and all(c.isprintable() for c in s):
                            strs += 1
                    except Exception:
                        pass
        if strs >= 2:
            print("  pos=%d vt=%d slots=%s strings=%d" % (pos, v, slots, strs))
            for i, fo in slots.items():
                p = fo + u32(fo)
                L = u32(p)
                raw = d[p + 4:p + 4 + L]
                try:
                    print("     slot%d len=%d utf16=%r" % (i, L, raw.decode("utf-16-le")[:60]))
                except Exception:
                    print("     slot%d len=%d utf8=%r" % (i, L, raw.decode("utf-8", "replace")[:60]))
