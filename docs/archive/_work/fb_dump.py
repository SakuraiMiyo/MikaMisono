"""FlatBuffers dumper for BA Field*/Scenario field scripts (read-only).

Container observed: [i32 payload_len][u32 root_offset][vtable ...][table ...]
i.e. the 4-byte MemoryPack length prefix shifts the whole flatbuffer by 4.
"""
import os, sys, zipfile, struct, json
from base64 import b64encode
sys.path.insert(0, r"C:\OneDrive\MikaMisono\assets\blue-archive")
from lib.MersenneTwister import MersenneTwister
from lib.XXHashService import CalculateHash

TB = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\TableBundles"
OUT = r"C:\OneDrive\MikaMisono\docs\archive\_work"


def pw(seed):
    return b64encode(MersenneTwister(CalculateHash(seed)).NextBytes(15))


def read_entry(disk, entry):
    with zipfile.ZipFile(os.path.join(TB, disk)) as z:
        return z.read(entry, pwd=pw(entry[:-6] + ".zip"))


def u16(b, o): return struct.unpack_from("<H", b, o)[0]
def i32(b, o): return struct.unpack_from("<i", b, o)[0]
def u32(b, o): return struct.unpack_from("<I", b, o)[0]
def i64(b, o): return struct.unpack_from("<q", b, o)[0]


def _root_score(buf, root, base=4):
    """Count how many root slots resolve to a plausible DataList vector."""
    best = 0
    for slot, o in fields_of(buf, root, base).items():
        try:
            ds, L, _ = read_vec(buf, o)
        except Exception:
            continue
        if 0 < L < 1000000 and ds + L * 4 <= len(buf):
            best = max(best, L)
    return best


def origin_for(buf):
    """Detect the flatbuffer layout.

    Observed container (MemoryPack):
        [i32 payload_len][i32 n_fields?][u32 root_soffset][vtable][root]
    The root soffset may be relative to buffer offset 0 (base=0) or to offset 4
    (base=4); probe both. A layout wins when its root exposes a DataList vector.
    """
    best = None
    for w in range(0, 28, 4):
        root = w + u32(buf, w)
        if not (8 <= root < len(buf) - 8):
            continue
        for base in (0, 4):
            score = _root_score(buf, root, base)
            if score and (best is None or score > best[2]):
                best = (base, root, score)
    if best is None:
        return None, None, {}
    base, root, _ = best
    return base, root, fields_of(buf, root, base)


def root_pos(buf):
    o, r, f = origin_for(buf)
    return r


def vt_table(buf, pos, base=4):
    """Return (vtable_abs, size, {slot: field_abs}) for a table at `pos`.

    The vtable is at pos - vt_off where vt_off is the int32 stored at pos.
    `base` compensates for a MemoryPack length prefix shifting the flatbuffer.
    A candidate vtable is only accepted if every slot value, read as uint16,
    yields an in-bounds field offset (u16 is used, never u32, otherwise header
    words masquerade as 512-entry vtables).
    """
    vo = i32(buf, pos)
    for vt in (pos - vo, pos - base - vo):
        if not (0 <= vt <= len(buf) - 4):
            continue
        sz = u16(buf, vt)
        if sz < 4 or sz > 400 or (sz - 4) % 2 or vt + sz > len(buf):
            continue
        slots = {}
        ok = True
        for i in range((sz - 4) // 2):
            svo = u16(buf, vt + 4 + i * 2)
            if svo == 0:
                continue
            if svo < 2 or pos + svo + 4 > len(buf):
                ok = False
                break
            slots[i] = pos + svo
        if ok:
            return vt, sz, slots
    return None, 0, {}


def fields_of(buf, pos, base=4):
    return vt_table(buf, pos, base)[2]


def read_str(buf, o):
    p = o + u32(buf, o)
    L = u32(buf, p)
    return buf[p + 4:p + 4 + L]


def read_vec(buf, o):
    p = o + u32(buf, o)
    return p + 4, u32(buf, p), p + 4


def elem_table(buf, ds, i):
    return ds + i * 4 + u32(buf, ds + i * 4)


def decode_text(raw):
    if not raw:
        return None, None
    if len(raw) % 2 == 0:
        try:
            s = raw.decode("utf-16-le")
            if s and all(c.isprintable() or c in "\r\n\t" for c in s):
                return "utf-16-le", s
        except UnicodeDecodeError:
            pass
    try:
        s = raw.decode("utf-8")
        if s and all(c.isprintable() or c in "\r\n\t" for c in s):
            return "utf-8", s
    except UnicodeDecodeError:
        pass
    return None, None


def describe(buf, pos, depth=0, origin=4):
    out = {}
    for slot, o in sorted(fields_of(buf, pos, origin).items()):
        entry = None
        try:
            raw = read_str(buf, o)
            if 0 < len(raw) <= 6000:
                enc, s = decode_text(raw)
                if s is not None:
                    entry = {"k": "str", "enc": enc, "v": s}
        except Exception:
            pass
        if entry is None:
            try:
                ds, L, _ = read_vec(buf, o)
                if 0 <= L <= 100000 and ds + L * 4 <= len(buf):
                    entry = {"k": "vec", "len": L}
                    if L and depth < 1:
                        try:
                            entry["e0"] = describe(buf, elem_table(buf, ds, 0), depth + 1)
                        except Exception:
                            pass
            except Exception:
                pass
        if entry is None:
            entry = {"k": "scalar", "u32": u32(buf, o), "i64": i64(buf, o)}
        out["slot%d" % slot] = entry
    return out


def rows(buf):
    origin, rp, f = origin_for(buf)
    if rp is None:
        return None, None, 0, None
    best = (None, 0)
    for slot, o in sorted(f.items()):
        try:
            ds, L, _ = read_vec(buf, o)
            if 0 < L < 1000000 and ds + L * 4 <= len(buf) and L > best[1]:
                best = (ds, L)
        except Exception:
            continue
    return rp, best[0], best[1], origin


if __name__ == "__main__":
    disk = sys.argv[1] if len(sys.argv) > 1 else "10001900114910089910_1704857403"
    entry = sys.argv[2] if len(sys.argv) > 2 else "8322306_01_02_forestriver_p01_d.bytes"
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    data = read_entry(disk, entry)
    print("== %s / %s : %d bytes, prefix=%d" % (disk, entry, len(data), u32(data, 0)))
    rp, ds, L, origin = rows(data)
    print("root@%s ds=%s rows=%d origin=%s" % (rp, ds, L, origin))
    for i in range(min(L or 0, n)):
        t = elem_table(data, ds, i)
        print(" row %d @%d: %s" % (i, t, json.dumps(describe(data, t, 0, origin), ensure_ascii=False)[:1400]))
