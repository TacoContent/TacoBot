import json
import re
from pathlib import Path
from zipfile import ZipFile
from typing import Dict, Optional

from .constants import JARS_DIR
from .logger import logger
from .metadata_handler import MetadataHandler
from .asset_extractor import AssetExtractor

class JarScanner:
    def __init__(self, use_mongodb: bool = False, collection_name: Optional[str] = None, include_asset: bool = False):
        self.metadata_handler = MetadataHandler(use_mongodb=use_mongodb, collection_name=collection_name)
        self.asset_extractor = AssetExtractor()
        self.include_asset = include_asset

    def scan_jars(self):
        jar_files = list(JARS_DIR.glob("*.jar"))
        if not jar_files:
            logger.warning(f"No .jar files found in {JARS_DIR}")
            return

        for jar_path in jar_files:
            self.process_jar(jar_path)

        self.metadata_handler.save_metadata()
        self.metadata_handler.close()

    def process_jar(self, jar_path: Path):
        logger.info(f"Processing JAR: {jar_path.name}")
        try:
            with ZipFile(jar_path, 'r') as zip_ref:
                # Load language file
                lang_data = self.load_language_file(zip_ref)

                # List all files
                file_list = zip_ref.namelist()

                # Filter for textures
                for file_path in file_list:
                    if not file_path.endswith(".png"):
                        continue

                    # Check if it is an item or block texture
                    # Expected format: assets/<namespace>/textures/item/<name>.png
                    # or assets/<namespace>/textures/block/<name>.png
                    parts = file_path.split('/')
                    if len(parts) < 5 or parts[0] != 'assets' or parts[2] != 'textures':
                        continue

                    category = parts[3] # item or block
                    if category not in ['item', 'block']:
                        continue

                    namespace = parts[1]
                    filename = parts[-1]
                    name_stem = filename[:-4] # remove .png

                    item_id = f"{namespace}:{name_stem}"

                    # Skip if already exists in metadata (optimization to avoid extraction check if not needed)
                    if self.metadata_handler.item_exists(item_id):
                        logger.warning(f"Duplicate item ID found: {item_id} in {jar_path.name}. Skipping.")
                        continue

                    # Determine Name
                    display_name = self.get_display_name(item_id, category, lang_data)

                    # Extract Asset (optionally include base64 in metadata)
                    asset_filename, asset_b64 = self.asset_extractor.extract_asset(
                        zip_ref, file_path, item_id, jar_path.name, include_asset=self.include_asset
                    )

                    if asset_filename:
                        # Add to metadata (pass base64 data when available)
                        self.metadata_handler.add_item(item_id, asset_filename, display_name, jar_path.name, asset_b64=asset_b64)

        except Exception as e:
            logger.error(f"Error processing JAR {jar_path.name}: {e}")

    def load_language_file(self, zip_ref: ZipFile) -> Dict[str, str]:
        # Try to find en_us.json
        # Standard path: assets/minecraft/lang/en_us.json
        # But we might have other namespaces.
        # For simplicity, we look for assets/minecraft/lang/en_us.json first.
        # If we are processing a mod, we might need to look for assets/<modid>/lang/en_us.json
        # But usually we want the main language file.

        # Let's try to load all en_us.json files we find and merge them?
        # Or just stick to minecraft for now as per user example.
        # User example: minecraft:acacia_boat.

        lang_data = {}

        for file_path in zip_ref.namelist():
            if file_path.endswith("lang/en_us.json"):
                try:
                    with zip_ref.open(file_path) as f:
                        data = json.load(f)
                        lang_data.update(data)
                except Exception as e:
                    logger.warning(f"Failed to load language file {file_path}: {e}")

        return lang_data

    def get_display_name(self, item_id: str, category: str, lang_data: Dict[str, str]) -> str:
        namespace, name = item_id.split(':')

        # Try keys
        keys_to_try = [
            f"item.{namespace}.{name}",
            f"block.{namespace}.{name}",
            f"{category}.{namespace}.{name}"
        ]

        for key in keys_to_try:
            if key in lang_data:
                return lang_data[key]

        # Fallback: format the name (acacia_boat -> Acacia Boat)
        return name.replace("_", " ").title()
