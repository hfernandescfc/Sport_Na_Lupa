#!/usr/bin/env python3
"""
Extract Alex Bruno career data.

To use this script:

1. Visit https://www.sofascore.com/search?q=alex+bruno
2. Find "Alex Bruno" from ASA-AL in the results
3. Click on his profile - the URL will be: https://www.sofascore.com/pt/player/alex-bruno/[PLAYER_ID]
4. Copy the PLAYER_ID number
5. Run: python extract_alex_bruno.py --player-id XXXXX

Example:
  python extract_alex_bruno.py --player-id 2315723

Or just run with the ID directly in the code below:
"""

import argparse
import sys
from extract_player_career_dom import extract_by_id

def main():
    parser = argparse.ArgumentParser(description="Extract Alex Bruno career data")
    parser.add_argument("--player-id", type=int, help="SofaScore player ID for Alex Bruno")

    args = parser.parse_args()

    if not args.player_id:
        print(__doc__)
        print("\nExample player IDs (these may vary):")
        print("  - Search on https://www.sofascore.com/search?q=alex+bruno")
        print("  - Click on Alex Bruno (ASA-AL)")
        print("  - Copy the number from the URL")
        print("")
        print("Then run: python extract_alex_bruno.py --player-id XXXXX")
        sys.exit(1)

    extract_by_id(player_id=args.player_id, player_name="Alex Bruno")

if __name__ == "__main__":
    main()
