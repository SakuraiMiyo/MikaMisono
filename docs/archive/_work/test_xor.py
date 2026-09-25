"""Test: is the scenario payload XOR-obfuscated like the Excel tables?"""
import sys, struct
sys.path.insert(0, r"C:\OneDrive\MikaMisono\assets\blue-archive")
sys.path.insert(0, r"C:\OneDrive\MikaMisono\docs\archive\_work")
from extract_scenario import read_entry
from lib.TableEncryptionService import CreateKey, XOR

d = read_entry("10001900114910089910_1704857403", "8322306_01_02_forestriver_p01_d.bytes")


def u16(b, o): return struct.unpack_from("<H", b, o)[0]
def u32(b, o): return struct.unpack_from("<I", b, o)[0]
def i32(b, o): return struct.unpack_from("<i", b, o)[0]


def vtables(b):
    out = []
    for v in range(0, min(8192, len(b) - 4), 2):
        sz = u16(b, v)
        if sz < 4 or sz > 40 or (sz - 4) % 2 or v + sz > len(b):
            continue
        sl = [u16(b, v + 4 + 2 * i) for i in range((sz - 4) // 2)]
        nz = [x for x in sl if x]
        if nz and nz == sorted(nz) and all(4 <= x <= 4000 for x in nz):
            out.append((v, sz, sl))
    return out


print("plain vtables:", len(vtables(d)))
for name in ("ScenarioScriptField1Excel", "8322306_01_02_forestriver_p01_d",
             "CharacterDialogFieldExcel", "FieldStoryStageExcel", "ScenarioScriptField1ExcelTable"):
    x = XOR(name, d)
    vts = vtables(x)
    print("XOR(%s): vtables=%d  head=%s" % (name, len(vts), x[:24].hex(" ")))
    if vts:
        print("   ", vts[:6])
