#!/usr/bin/env python3
"""
Download professional chess piece SVGs from GitHub (MuTsunTsai's skak-svg)
These are high-quality, elegant, and optimized for web use.
"""

import os
import urllib.request
import urllib.error

# Base URL for SVG pieces (MuTsunTsai's skak-svg - professional & elegant)
BASE_URL = "https://raw.githubusercontent.com/MuTsunTsai/skak-svg/main/svg"

# Piece names (white and black)
PIECES = ['wk', 'wq', 'wr', 'wb', 'wn', 'wp', 'bk', 'bq', 'br', 'bb', 'bn', 'bp']

# Output directory
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'app', 'static', 'img', 'pieces')

# Create directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Downloading professional chess piece SVGs from GitHub...")
print(f"Source: MuTsunTsai's skak-svg (https://github.com/MuTsunTsai/skak-svg)")
print(f"Destination: {OUTPUT_DIR}\n")

success_count = 0
failed_pieces = []

for piece in PIECES:
    url = f"{BASE_URL}/{piece}.svg"
    filepath = os.path.join(OUTPUT_DIR, f"{piece}.svg")
    
    try:
        print(f"Downloading {piece}...", end=" ", flush=True)
        urllib.request.urlretrieve(url, filepath)
        print("✓")
        success_count += 1
    except urllib.error.URLError as e:
        print(f"✗ Failed: {e}")
        failed_pieces.append((piece, str(e)))
    except Exception as e:
        print(f"✗ Error: {e}")
        failed_pieces.append((piece, str(e)))

print(f"\n{'='*50}")
print(f"Download complete!")
print(f"Successfully downloaded: {success_count}/{len(PIECES)} pieces")

if failed_pieces:
    print(f"\nFailed pieces:")
    for piece, error in failed_pieces:
        print(f"  - {piece}: {error}")
else:
    print("\n🎉 All pieces downloaded successfully!")

print(f"\nPieces are now available in: {OUTPUT_DIR}")
