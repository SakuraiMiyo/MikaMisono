"""Extract Japanese scenario text from BA TableBundles scenario zips.

Schema for ScenarioScriptField1Excel recovered from global-metadata.dat
(FlatData.ScenarioScriptField1Excel, il2cpp metadata v31), declaration order:

  slot 0  SelectionGroup   int64
  slot 1  Sound            string
  slot 2  Transition       uint32
  slot 3  BGName           uint32
  slot 4  BGEffect         uint32
  slot 5  PopupFileName    string
  slot 6  ScriptKr         string (base64-of-XOR-of-utf16)
  slot 7  TextJp           string
  slot 8  VoiceJp          string

Root table = ScenarioScriptField1ExcelTable with DataList at slot 0.
"""
import os, sys, zipfile, struct, json, base64
from base64 import b64encode

sys.path.insert(0, r"C:\OneDrive\MikaMisono\assets\blue-archive")
from lib.MersenneTwister import MersenneTwister
from lib.XXHashService import CalculateHash
from lib.TableEncryptionService import CreateKey, XOR as TableXOR

TB = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\TableBundles"

FIELD1_SLOTS = {
    1: ("Sound", "str"),
    2: ("Transition", "u32"),
    3: ("BGName", "u32"),
    4: ("BGEffect", "u32"),
    5: ("PopupFileName", "str"),
    6: ("ScriptKr", "str"),
    7: ("TextJp", "str"),
    8: ("VoiceJp", "str"),
}
# slot 0 = SelectionGroup (int64), listed for completeness


def pw(seed):
    return b64encode(MersenneTwister(CalculateHash(seed)).NextBytes(15))


def read_entry(disk, entry, out_dir=None):
    with zipfile.ZipFile(os.path.join(TB, disk)) as z:
        return z.read(entry, pwd=pw(entry[:-6] + ".zip"))


def u16(b, o): return struct.unpack_from("<H", b, o)[0]
def i32(b, o): return struct.unpack_from("<i", b, o)[0]
def u32(b, o): return struct.unpack_from("<I", b, o)[0]
def i64(b, o): return struct.unpack_from("<q", b, o)[0]


def vt(buf, pos):
    """vtable address for a table at `pos`.

    The payload carries a 4-byte MemoryPack length prefix, so the whole
    flatbuffer is shifted by 4 bytes and the soffset stored at the table start
    must be applied relative to buffer offset 4 (not to `pos`).
    """
    vo = i32(buf, pos)
    for v in (4 - vo, pos - vo):
        if not (0 <= v <= len(buf) - 4):
            continue
        sz = u16(buf, v)
        if 4 <= sz <= 400 and (sz - 4) % 2 == 0 and v + sz <= len(buf) and v + sz <= pos:
            return v, sz
    return None, None


def slots_of(buf, pos):
    v, sz = vt(buf, pos)
    if v is None:
        return {}
    return {i: pos + u16(buf, v + 4 + i * 2) for i in range((sz - 4) // 2) if u16(buf, v + 4 + i * 2)}


def get_str(buf, o):
    p = o + u32(buf, o)
    L = u32(buf, p)
    return buf[p + 4:p + 4 + L]


def get_vec(buf, o):
    p = o + u32(buf, o)
    return p + 4, u32(buf, p)


def root_table(buf):
    """Locate the root table: the uoffset word lives in the MemoryPack header."""
    for w in (4, 8, 0):
        cand = w + u32(buf, w)
        if 8 <= cand < len(buf) - 8:
            s = slots_of(buf, cand)
            if 0 in s:
                try:
                    ds, L = get_vec(buf, s[0])
                    if 0 < L < 1000000 and ds + L * 4 <= len(buf):
                        return cand, ds, L
                except Exception:
                    pass
    return None, None, 0


def decode_text(raw):
    """Scenario strings are either plain UTF-16 or base64(XOR(utf16))."""
    if not raw:
        return ""
    try:
        s = raw.decode("utf-16-le")
        if s and all(c.isprintable() or c in "\r\n\t\u3000" for c in s):
            return s
    except UnicodeDecodeError:
        pass
    try:
        s = raw.decode("utf-8")
        if s and all(c.isprintable() or c in "\r\n\t" for c in s):
            return s
    except UnicodeDecodeError:
        pass
    return "<binary:%d bytes %s>" % (len(raw), raw[:16].hex())


def parse_field1(data):
    rp, ds, L = root_table(data)
    if rp is None:
        return None, []
    rows = []
    for i in range(L):
        t = ds + i * 4 + u32(data, ds + i * 4)
        f = slots_of(data, t)
        row = {"SelectionGroup": i64(data, f[0]) if 0 in f else None}
        for slot, (name, kind) in FIELD1_SLOTS.items():
            if slot not in f:
                row[name] = None
                continue
            if kind == "str":
                row[name] = decode_text(get_str(data, f[slot]))
            else:
                row[name] = u32(data, f[slot])
        rows.append(row)
    return rp, rows


def parse_main(data, cls):
    """generated FlatData classes handle their own base64 XOR decryption."""
    root = cls.GetRootAs(data)
    n = root.DataListLength()
    out = []
    for i in range(n):
        e = root.DataList(i)
        out.append({
            "GroupId": e.GroupId(),
            "BGMId": e.BGMId(),
            "TextJp": e.TextJp(),
            "VoiceJp": e.VoiceJp(),
            "PopupFileName": e.PopupFileName(),
        })
    return out


if __name__ == "__main__":
    disk, entry = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    data = read_entry(disk, entry)
    rp, rows = parse_field1(data)
    print("== %s / %s  (%d bytes) root=%s rows=%d" % (disk, entry, len(data), rp, len(rows)))
    for i, r in enumerate(rows[:n]):
        print("--- row %d" % i)
        for k, v in r.items():
            print("    %-16s %s" % (k, v))
