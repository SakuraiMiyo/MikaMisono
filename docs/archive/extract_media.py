#!/usr/bin/env python3
"""
Blue Archive JP - MediaPatch Story Asset Extractor
Extracts story-related media files (images, audio, video) from MediaPatch.
MediaPatch files are unencrypted (JPEG, PNG, OGG, MP4).
"""

import sys
import os
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = r"D:\YostarGames\BlueArchive_JP"
MEDIAPATCH_DIR = os.path.join(GAME_DIR, "BlueArchive_Data", "StreamingAssets", "MediaPatch")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "Media")

# File type signatures
SIGNATURES = {
    b'\xff\xd8': '.jpg',
    b'\x89PNG': '.png',
    b'OggS': '.ogg',
    b'\x00\x00\x00\x1c': '.mp4',
    b'PK\x03\x04': '.zip',
}

def detect_type(filepath):
    """Detect file type from magic bytes"""
    with open(filepath, 'rb') as f:
        header = f.read(8)
    for sig, ext in SIGNATURES.items():
        if header.startswith(sig):
            return ext
    return '.bin'

def main():
    print("=" * 60)
    print("Blue Archive JP - MediaPatch Asset Extractor")
    print("=" * 60)

    if not os.path.exists(MEDIAPATCH_DIR):
        print(f"MediaPatch directory not found: {MEDIAPATCH_DIR}")
        return 1

    files = os.listdir(MEDIAPATCH_DIR)
    total = len(files)
    print(f"Total MediaPatch files: {total}")

    # Create categorized output directories
    categories = {
        '.jpg': 'Images',
        '.png': 'Images',
        '.ogg': 'Audio',
        '.mp4': 'Video',
        '.zip': 'Archives',
        '.bin': 'Unknown',
    }

    for cat in set(categories.values()):
        os.makedirs(os.path.join(OUTPUT_DIR, cat), exist_ok=True)

    stats = {cat: 0 for cat in set(categories.values())}

    for idx, filename in enumerate(sorted(files)):
        filepath = os.path.join(MEDIAPATCH_DIR, filename)
        if not os.path.isfile(filepath):
            continue

        # Detect type
        ext = detect_type(filepath)
        cat = categories.get(ext, 'Unknown')

        # Copy to appropriate directory
        out_name = filename + ext
        out_path = os.path.join(OUTPUT_DIR, cat, out_name)

        shutil.copy2(filepath, out_path)
        stats[cat] += 1

        if (idx + 1) % 1000 == 0:
            print(f"  Progress: {idx+1}/{total}...")

    print()
    print("=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)
    for cat, count in stats.items():
        print(f"  {cat}: {count} files")
    print(f"  Total: {sum(stats.values())} files")
    print(f"\nOutput: {OUTPUT_DIR}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
