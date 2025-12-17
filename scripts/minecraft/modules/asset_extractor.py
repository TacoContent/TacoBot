import shutil
import base64
from pathlib import Path
from zipfile import ZipFile
from typing import Optional, Tuple

from .constants import ASSETS_DIR
from .logger import logger


class AssetExtractor:
    @staticmethod
    def get_asset_filename(item_id: str) -> str:
        """Converts item ID (e.g., minecraft:acacia_boat) to filename (minecraft_acacia_boat.png)."""
        return item_id.replace(":", "_") + ".png"

    @staticmethod
    def extract_asset(zip_file: ZipFile, zip_path: str, item_id: str, source_jar: str, include_asset: bool = False) -> Tuple[Optional[str], Optional[str]]:
        """
        Extracts the asset from the zip file to the assets directory.
        If include_asset is True, also returns a base64-encoded string of the image data.
        Returns (filename, asset_b64) where either can be None on failure.
        """
        filename = AssetExtractor.get_asset_filename(item_id)
        destination_path = ASSETS_DIR / filename

        if destination_path.exists():
            logger.warning(f"Duplicate item asset found for ID: {item_id}. Target: {filename}. Source: {source_jar}. Skipping.")
            return None, None

        try:
            with zip_file.open(zip_path) as source:
                data = source.read()

            # Save file to disk
            with open(destination_path, "wb") as target:
                target.write(data)

            asset_b64 = None
            if include_asset:
                asset_b64 = base64.b64encode(data).decode("ascii")

            return filename, asset_b64
        except Exception as e:
            logger.error(f"Failed to extract asset {zip_path} from {source_jar}: {e}")
            return None, None
