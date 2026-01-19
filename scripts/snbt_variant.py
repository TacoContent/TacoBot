#!/usr/bin/env python3
"""Small helper to compute Minecraft item variant IDs from SNBT or JSON NBT.

Usage examples:
    # compute default variant for single item unit
    python scripts/snbt_variant.py minecraft:stone

    # compute using an SNBT string
    python scripts/snbt_variant.py minecraft:stone --snbt '{display:{Name:"\"My Stone\""}}'

    # compute using a JSON NBT payload
    python scripts/snbt_variant.py minecraft:stone --nbt-json '{"display": {"Name": "{\"text\":\"My Stone\"}"}}'

This script uses the canonicalization helpers in `bot.lib.minecraft.item` so
the results match the project library's behavior.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# If this script is invoked directly (outside of test harness / package), make
# sure the repository root is on sys.path so `from bot...` imports work.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from bot.lib.minecraft.item import calculate_variant_id, calculate_variant_id_from_snbt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute Minecraft item variant ID (SHA-256 of canonical SNBT)")
    parser.add_argument("item_id", help="Item id, e.g. minecraft:stone")
    parser.add_argument("--snbt", help="SNBT string to normalize and hash (top-level count will be normalized)")
    parser.add_argument("--snbt-file", help="Path to a file containing an SNBT string")
    parser.add_argument("--nbt-json", help="NBT as JSON string (will be serialized to canonical SNBT) ")
    parser.add_argument("--nbt-json-file", help="Path to a file containing JSON for the NBT payload")
    parser.add_argument("--raw", action="store_true", help="Only print the hex digest (no extra text)")

    args = parser.parse_args(argv)

    item_id = args.item_id

    # SNBT takes precedence if provided
    snbt = None
    if args.snbt:
        snbt = args.snbt
    elif args.snbt_file:
        p = Path(args.snbt_file)
        if not p.exists():
            print(f"SNBT file not found: {args.snbt_file}", file=sys.stderr)
            return 2
        snbt = p.read_text(encoding="utf-8")

    if snbt is not None:
        digest = calculate_variant_id_from_snbt(item_id, snbt)
        if args.raw:
            print(digest)
        else:
            print(f"Variant ID for {item_id} (from SNBT): {digest}")
        return 0

    # Otherwise try JSON NBT
    nbt_json = None
    if args.nbt_json:
        nbt_json = args.nbt_json
    elif args.nbt_json_file:
        p = Path(args.nbt_json_file)
        if not p.exists():
            print(f"NBT JSON file not found: {args.nbt_json_file}", file=sys.stderr)
            return 2
        nbt_json = p.read_text(encoding="utf-8")

    if nbt_json is not None:
        try:
            nbt = json.loads(nbt_json)
        except Exception as ex:
            print(f"Failed to parse NBT JSON: {ex}", file=sys.stderr)
            return 2
        digest = calculate_variant_id(item_id, nbt)
        if args.raw:
            print(digest)
        else:
            print(f"Variant ID for {item_id} (from NBT JSON): {digest}")
        return 0

    # default, no NBT provided
    digest = calculate_variant_id(item_id, None)
    if args.raw:
        print(digest)
    else:
        print(f"Variant ID for {item_id}: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
