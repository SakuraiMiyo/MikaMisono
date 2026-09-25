"""Find how disk bundle filenames (<u64>_<u32>) relate to catalog records."""
import struct, json, os, re, collections, zlib

P = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\MediaPatch\Catalog\MediaCatalog.bytes"
TB = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\TableBundles"
MP = r"C:\SoftWare\BlueArchivesJP\YostarGames\BlueArchive_JP\BlueArchive_Data\StreamingAssets\MediaPatch"
OUT = r"C:\OneDrive\MikaMisono\docs\archive\_work"
data = open(P, "rb").read()

disk_mp = set(f for f in os.listdir(MP) if os.path.isfile(os.path.join(MP, f)))
print("MediaPatch disk files:", len(disk_mp))

# 1) are the disk names present as ASCII digit strings in MediaCatalog?
hits = 0
sample = list(disk_mp)[:20]
found = {}
for fn in list(disk_mp):
    if fn.encode() in data:
        hits += 1
        found[fn] = data.find(fn.encode())
print("disk names literally present in MediaCatalog:", hits)

# 2) are the 32-bit halves present as uint32 anywhere? test a few
big = sample[0]
print("sample disk names:", sample[:5])

# 3) check: maybe MediaPatch disk name == CRC32-based. test hypotheses on the airi record
#    record: path audio/voc_jp/jp_airi/jp_airi, name GameData\Audio\VOC_JP\JP_Airi.zip, crc=3375441397, size=2143288
cands = {
 "JP_Airi.zip": 3375441397,
}
target = 3375441397
import itertools
names = ["JP_Airi.zip", "GameData\\Audio\\VOC_JP\\JP_Airi.zip", "audio/voc_jp/jp_airi/jp_airi",
         "GameData/Audio/VOC_JP/JP_Airi.zip", "JP_Airi", "jp_airi"]
for nm in names:
    b = nm.encode()
    print(nm, "crc32=", zlib.crc32(b) & 0xffffffff)

# 4) what 32-bit value would be at play? show the raw int triple region for first record properly
i = 9
for k in range(4):
    L = struct.unpack_from("<i", data, i)[0]
    s = data[i+4:i+4+L].decode("utf-8")
    print("off", i, "len", L, repr(s))
    i += 4 + L
tail = data[i-4:i+40]
print("after last string:", tail.hex())
print("ints:", struct.unpack_from("<QQQ", data, i))
