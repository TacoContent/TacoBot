#!/usr/bin/env python3
"""
Minecraft Item Extractor
Extracts items and blocks from Minecraft JAR files.
"""
import sys
import argparse
from pathlib import Path
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

# Add the current directory to sys.path to ensure modules can be imported
current_dir = Path(__file__).parent.resolve()
sys.path.append(str(current_dir))

from modules.jar_scanner import JarScanner  # noqa: E402
from modules.logger import logger  # noqa: E402

def parse_arguments():
    parser = argparse.ArgumentParser(description="Extract items and blocks from Minecraft JAR files.")
    parser.add_argument("--mongodb", action="store_true", help="Enable writing item info to MongoDB.")
    parser.add_argument(
        "--collection", type=str, default="minecraft_items", help="MongoDB collection name (default: minecraft_items)."
    )
    parser.add_argument(
        "--include-asset",
        action="store_true",
        help="Enable base64-encoded asset data in metadata files and MongoDB (if enabled).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing items in metadata and MongoDB.",
    )

    return parser.parse_args()

def main():
    args = parse_arguments()

    logger.info("Starting Minecraft Item Extractor...")
    if args.mongodb:
        logger.info(f"MongoDB enabled. Collection: {args.collection}")
    if args.include_asset:
        logger.info("Including base64-encoded assets in metadata and MongoDB (if enabled).")
    if args.overwrite:
        logger.info("Overwrite enabled. Existing items will be updated.")

    scanner = JarScanner(
        use_mongodb=args.mongodb,
        collection_name=args.collection,
        include_asset=args.include_asset,
        overwrite=args.overwrite,
    )
    scanner.scan_jars()
    logger.info("Extraction complete.")

if __name__ == "__main__":
    main()
