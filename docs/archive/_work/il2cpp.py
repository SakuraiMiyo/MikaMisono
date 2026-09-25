"""Minimal IL2CPP global-metadata.dat reader to recover a FlatBuffers table schema.

Only needs the string table + type definitions + fields, so it skips most
metadata structures. Read-only.
"""
import struct, sys, json

P = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\il2cpp_data\Metadata\global-metadata.dat"
data = open(P, "rb").read()
print("size", len(data), "magic", hex(struct.unpack_from("<I", data, 0)[0]))
version = struct.unpack_from("<i", data, 4)[0]
print("version", version)

# header is a sequence of int32/uint32 pairs: (offset, size) for each structure
def hdr(i):
    return struct.unpack_from("<II", data, 8 + i * 8)

names = [
    "stringLiteral", "stringLiteralData", "string", "events", "properties",
    "methods", "parameterDefaultValues", "fieldDefaultValues", "fieldAndParameterDefaultValueData",
    "fieldMarshaledSizes", "parameters", "fields", "genericParameters",
    "genericParameterConstraints", "genericContainers", "nestedTypes",
    "interfaces", "vtableMethods", "interfaceOffsets", "typeDefinitions",
    "images", "assemblies", "fieldRefs", "referencedAssemblies",
    "attributeData", "attributeDataRange", "unresolvedVirtualCallParameterTypes",
    "unresolvedVirtualCallParameterRanges", "windowsRuntimeTypeNames",
    "windowsRuntimeStrings", "exportedTypeDefinitions",
]
for i, nm in enumerate(names):
    off, sz = hdr(i)
    print("%2d %-42s off=%10d size=%10d" % (i, nm, off, sz))

str_off, str_sz = hdr(2)
fields_off, fields_sz = hdr(11)
typedefs_off, typedefs_sz = hdr(19)

print("string table bytes:", str_sz)
print("field defs:", fields_sz // (4 * 3))
print("type defs:", typedefs_sz // (4 * 22))

def read_cstr(o):
    e = data.index(b"\x00", o)
    return data[o:e].decode("utf-8", "replace")

t = data.find(b"ScenarioScriptField1Excel\x00")
print("ScenarioScriptField1Excel string at", t, "-> token", t - str_off)
t2 = data.find(b"TextJp\x00", str_off)
print("TextJp string at", t2, "-> token", t2 - str_off)
