#!/usr/bin/env python3
"""
Blue Archive JP - Story/Scenario Data Extractor
Extracts all story-related table data from TableBundles without modifying game files.

Encryption mechanism:
1. ZIP password = base64(MersenneTwister(XXHash32(filename)).NextBytes(15))
2. Bytes XOR key = MersenneTwister(XXHash32(tablename)).NextBytes(data_length)
3. String encryption = base64 decode -> XOR -> UTF-16 decode
"""

import sys
import os
import json

# Add the JP-Downloader lib to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "Blue-Archive-JP-Downloader"))

from lib.TableService import TableZipFile
from lib.TableEncryptionService import XOR, CreateKey, ConvertString, ConvertLong, ConvertUInt, ConvertInt
from lib.XXHashService import CalculateHash
from lib.MersenneTwister import MersenneTwister
from base64 import b64encode
import flatbuffers

# FlatData imports
import FlatData as FlatData
from FlatData.dump import dump_table

# =========== CONFIGURATION ===========
GAME_DIR = r"D:\YostarGames\BlueArchive_JP"
TABLEBUNDLES_DIR = os.path.join(GAME_DIR, "BlueArchive_Data", "StreamingAssets", "TableBundles")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "Tables")

# Story-related table names to extract
STORY_TABLE_PATTERNS = [
    "scenarioscript",           # All scenario scripts (Main, Event, Favor, Group, etc.)
    "contentsscenario",         # Content scenarios
    "eventcontentscenario",     # Event content scenarios
    "characterdialog",          # Character dialogs
    "fieldstorystage",          # Field story stages
    "scenarioreplay",           # Scenario replay
    "scenarioresourceinfo",     # Scenario resource info
    "scenariobgeffect",         # Scenario BG effects
    "scenariobgname",           # Scenario BG names
    "scenariocharacter",        # Scenario character data
    "localizescenario",         # Localized scenario text
    "scenariotransition",       # Scenario transitions
    "tutorialcharacterdialog",  # Tutorial dialogs
    "eventcontentspinedialogoffset", # Event spine dialog offset
]

def is_story_table(filename: str) -> bool:
    """Check if a .bytes file is story-related"""
    lower = filename.lower()
    for pattern in STORY_TABLE_PATTERNS:
        if pattern in lower:
            return True
    # Also match story/scenario scene files
    if "_story" in lower or "_scenario" in lower:
        return True
    return False

def lower_name_to_module():
    """Build mapping from lowercase table name to FlatData module"""
    return {key.lower(): value for key, value in FlatData.__dict__.items()}

def main():
    print("=" * 60)
    print("Blue Archive JP - Story Data Extractor")
    print("=" * 60)
    print(f"Source: {TABLEBUNDLES_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    module_dict = lower_name_to_module()
    all_files = sorted(os.listdir(TABLEBUNDLES_DIR))
    total = len(all_files)

    story_extracted = {}
    processed = 0
    skipped = 0
    errors = 0

    for idx, filename in enumerate(all_files):
        filepath = os.path.join(TABLEBUNDLES_DIR, filename)

        # Skip directories and non-files
        if not os.path.isfile(filepath):
            continue

        # Try to open as ZIP with decryption
        try:
            tz = TableZipFile(filepath)
            inner_files = tz.namelist()
        except Exception as e:
            skipped += 1
            continue

        # Process each inner .bytes file
        for inner_name in inner_files:
            if not inner_name.endswith(".bytes"):
                continue

            # Check if this is a story-related table
            if not is_story_table(inner_name):
                continue

            # Get table name without .bytes extension
            table_name = inner_name[:-6]  # remove .bytes

            try:
                # Read encrypted data
                raw_data = tz.read(inner_name)

                # XOR decrypt using table name
                decrypted = XOR(table_name, raw_data)

                # Try to parse with FlatBuffers
                flatbuffer_cls = module_dict.get(table_name.lower())
                if flatbuffer_cls is None:
                    # Try with 'exceltable' suffix
                    flatbuffer_cls = module_dict.get((table_name + "exceltable").lower())

                if flatbuffer_cls is None:
                    # Record but can't parse
                    story_extracted[table_name] = {
                        "status": "no_schema",
                        "size": len(decrypted),
                        "first_bytes_hex": decrypted[:64].hex()
                    }
                    continue

                # Parse FlatBuffer and dump as dict
                flatbuffer = flatbuffer_cls.GetRootAs(decrypted)
                json_data = dump_table(flatbuffer)

                # Save to JSON
                out_name = table_name + ".json"
                out_path = os.path.join(OUTPUT_DIR, out_name)
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)

                entry_count = len(json_data) if isinstance(json_data, list) else 1
                story_extracted[table_name] = {
                    "status": "ok",
                    "entries": entry_count,
                    "file": out_name
                }

            except Exception as e:
                story_extracted[table_name] = {
                    "status": "error",
                    "error": str(e)[:200]
                }
                errors += 1

        tz.close()
        processed += 1

        # Progress indicator
        if (idx + 1) % 500 == 0:
            print(f"  Progress: {idx+1}/{total} bundles processed...")

    # =========== SUMMARY ===========
    print()
    print("=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)
    print(f"Total TableBundles: {total}")
    print(f"Processed: {processed}")
    print(f"Skipped (non-ZIP): {skipped}")
    print(f"Errors: {errors}")
    print(f"Story tables found: {len(story_extracted)}")
    print()

    # Group by status
    ok_tables = {k: v for k, v in story_extracted.items() if v["status"] == "ok"}
    no_schema = {k: v for k, v in story_extracted.items() if v["status"] == "no_schema"}
    error_tables = {k: v for k, v in story_extracted.items() if v["status"] == "error"}

    print(f"Successfully extracted: {len(ok_tables)}")
    for name, info in sorted(ok_tables.items()):
        print(f"  ✓ {name} ({info['entries']} entries) -> {info['file']}")

    if no_schema:
        print(f"\nNo FlatBuffer schema: {len(no_schema)}")
        for name, info in sorted(no_schema.items()):
            print(f"  ? {name} ({info['size']} bytes, hex: {info['first_bytes_hex'][:40]}...)")

    if error_tables:
        print(f"\nErrors: {len(error_tables)}")
        for name, info in sorted(error_tables.items()):
            print(f"  ✗ {name}: {info['error']}")

    # Save manifest
    manifest = {
        "ok": {k: v for k, v in ok_tables.items()},
        "no_schema": {k: v for k, v in no_schema.items()},
        "errors": {k: v for k, v in error_tables.items()},
    }
    manifest_path = os.path.join(OUTPUT_DIR, "_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\nManifest saved to: {manifest_path}")

    # Count total entries
    total_entries = sum(v.get("entries", 0) for v in ok_tables.values())
    print(f"\nTotal story entries extracted: {total_entries}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
