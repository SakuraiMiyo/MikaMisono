"""Recover FlatBuffers schema for BA Field* Excel tables from il2cpp metadata (v31)."""
import struct, json, os, sys, re

P = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\il2cpp_data\Metadata\global-metadata.dat"
OUT = r"C:\OneDrive\MikaMisono\docs\archive\_work"
data = open(P, "rb").read()

def hdr(i):
    return struct.unpack_from("<II", data, 8 + i * 8)

str_off, str_sz = hdr(2)
fields_off, fields_sz = hdr(11)
typedefs_off, typedefs_sz = hdr(19)
STRIDE = 0x58
NS, FI, FC = 4, 0x20, 0x44
n_types = typedefs_sz // STRIDE
n_fields = fields_sz // 16


def cstr(o):
    e = data.index(b"\x00", o)
    return data[o:e].decode("utf-8", "replace")


def name_at(token):
    o = str_off + token
    if not (str_off <= o < str_off + str_sz):
        return None
    try:
        return cstr(o)
    except ValueError:
        return None


TARGETS = sys.argv[1:] or [
    "ScenarioScriptField1Excel",
    "CharacterDialogFieldExcel",
    "FieldStoryStageExcel",
    "ScenarioScriptContentExcel",
    "ScenarioScriptMain1Excel",
    "ScenarioScriptFavor1Excel",
    "ScenarioScriptGroup1Excel",
    "ScenarioScriptEvent1Excel",
]

out = {}
for idx in range(n_types):
    base = typedefs_off + idx * STRIDE
    name_idx = struct.unpack_from("<I", data, base)[0]
    nm = name_at(name_idx) if name_idx else None
    if nm not in TARGETS:
        continue
    namespace_idx = struct.unpack_from("<I", data, base + NS)[0]
    field_start = struct.unpack_from("<i", data, base + FI)[0]
    field_count = struct.unpack_from("<H", data, base + FC)[0]
    fields = []
    for k in range(field_count):
        fi = field_start + k
        if fi < 0 or fi >= n_fields:
            continue
        fo = fields_off + fi * 16
        type_idx, fname_idx, ftoken = struct.unpack_from("<IIi", data, fo)
        fname = name_at(fname_idx) if fname_idx else None
        fields.append({"name": fname, "typeIndex": type_idx, "token": ftoken})
    out[nm] = {"typeIndex": idx, "namespace": name_at(namespace_idx) or "", "fields": fields}
    print("== %s (ns=%s) declared=%d resolved=%d" % (nm, out[nm]["namespace"], field_count, len(fields)))
    for k, f in enumerate(fields):
        print("   %2d %s" % (k, f["name"]))

# Also list every FlatData type whose name matches a *Field*Excel pattern plus
# pull the *Offset / Add* symbol groups from the string table.
print()
print("== string-table symbol groups for Field tables ==")
syms = {}
i = str_off
while i < str_off + str_sz:
    e = data.index(b"\x00", i)
    s = data[i:e].decode("utf-8", "replace")
    if "Field" in s and ("Excel" in s or "Offset" in s):
        syms[s] = i - str_off
    i = e + 1
for s in sorted(syms):
    print("   ", s)

json.dump(out, open(os.path.join(OUT, "il2cpp_field_schemas.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(syms, open(os.path.join(OUT, "il2cpp_field_symbols.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
