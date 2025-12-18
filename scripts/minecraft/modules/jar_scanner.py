import json
import re
from pathlib import Path
from zipfile import ZipFile
from typing import Dict, Optional, Tuple

from .constants import JARS_DIR
from .logger import logger
from .metadata_handler import MetadataHandler
from .asset_extractor import AssetExtractor

class JarScanner:
    def __init__(self, use_mongodb: bool = False, collection_name: Optional[str] = None, include_asset: bool = False, experimental: bool = False):
        self.metadata_handler = MetadataHandler(use_mongodb=use_mongodb, collection_name=collection_name)
        self.asset_extractor = AssetExtractor()
        self.include_asset = include_asset
        self.experimental = experimental

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

                # List all files once (for membership tests)
                file_list = set(zip_ref.namelist())

                # Find all item definitions
                # Support both formats:
                # - New (1.21+): assets/<namespace>/items/<name>.json
                # - Old/Mods: assets/<namespace>/models/item/<name>.json
                item_definitions = {}
                for file_path in file_list:
                    if not file_path.endswith(".json"):
                        continue
                    parts = file_path.split('/')

                    # New format: assets/<namespace>/items/<name>.json
                    if len(parts) >= 4 and parts[0] == 'assets' and parts[2] == 'items':
                        namespace = parts[1]
                        name_stem = parts[-1][:-5]  # remove .json
                        item_id = f"{namespace}:{name_stem}"
                        item_definitions[item_id] = file_path

                    # Old format: assets/<namespace>/models/item/<name>.json
                    elif len(parts) >= 5 and parts[0] == 'assets' and parts[2] == 'models' and parts[3] == 'item':
                        namespace = parts[1]
                        name_stem = parts[-1][:-5]  # remove .json
                        item_id = f"{namespace}:{name_stem}"
                        # Don't overwrite if new format already exists
                        if item_id not in item_definitions:
                            item_definitions[item_id] = file_path

                logger.info(f"Found {len(item_definitions)} item definitions in {jar_path.name}")

                # Process each item definition
                for item_id, item_def_path in item_definitions.items():
                    # Skip model variants that aren't actual inventory items
                    if self.is_model_variant(item_id):
                        logger.debug(f"Skipping model variant: {item_id}")
                        continue

                    # Skip if already exists in metadata
                    if self.metadata_handler.item_exists(item_id):
                        logger.warning(f"Duplicate item ID found: {item_id} in {jar_path.name}. Skipping.")
                        continue

                    # Determine the texture path for this item
                    namespace, name_stem = item_id.split(':')

                    asset_filename = None
                    asset_b64 = None

                    # Experimental 3D rendering for blocks
                    if self.experimental:
                        block_textures, block_type = self.find_block_textures(zip_ref, file_list, namespace, name_stem, item_def_path)
                        if block_textures:
                            asset_filename, asset_b64 = self.asset_extractor.render_3d_block(
                                item_id, block_textures, jar_path.name, include_asset=self.include_asset, block_type=block_type
                            )

                    # Fallback to 2D extraction if not experimental or 3D failed
                    if not asset_filename:
                        texture_path = self.find_item_texture(zip_ref, file_list, namespace, name_stem, item_def_path)

                        if not texture_path:
                            logger.debug(f"No texture found for item {item_id} in {jar_path.name}.")
                            continue

                        # Extract Asset (optionally include base64 in metadata)
                        asset_filename, asset_b64 = self.asset_extractor.extract_asset(
                            zip_ref, texture_path, item_id, jar_path.name, include_asset=self.include_asset
                        )

                    if asset_filename:
                        # Determine Name
                        display_name = self.get_display_name(item_id, "item", lang_data)
                        # Add to metadata (pass base64 data when available)
                        self.metadata_handler.add_item(item_id, asset_filename, display_name, jar_path.name, asset_b64=asset_b64)

        except Exception as e:
            logger.error(f"Error processing JAR {jar_path.name}: {e}")

    def is_model_variant(self, item_id: str) -> bool:
        """
        Check if an item is a model variant (not an actual inventory item).
        These are typically animation frames or trim variants that reference the base item.

        Examples to exclude:
        - minecraft:diamond_chestplate_amethyst_trim (armor trim variant)
        - minecraft:bow_pulling_0 (bow animation frame)
        - minecraft:trident_throwing (trident animation frame)
        - minecraft:fishing_rod_cast (fishing rod animation frame)
        """
        variant_patterns = [
            '_trim',        # Armor trim variants (e.g., diamond_chestplate_amethyst_trim)
            '_pulling',     # Bow pulling animation frames
            '_throwing',    # Trident/spear throwing animation
            '_in_hand',     # Item held in hand variant models
            '_cast',        # Fishing rod cast animation
        ]

        # Check if the item ID ends with any variant pattern
        item_name = item_id.split(':', 1)[1] if ':' in item_id else item_id
        return any(item_name.endswith(pattern) or pattern + '_' in item_name for pattern in variant_patterns)

    def find_block_textures(self, zip_ref: ZipFile, file_list: set, namespace: str, name_stem: str, item_def_path: str) -> Tuple[Optional[Dict[str, bytes]], str]:
        """
        Finds textures for 3D rendering (up, left, right).
        Returns (textures, block_type).
        block_type can be 'block', 'slab', 'stairs'.
        """
        block_type = "block"
        try:
            with zip_ref.open(item_def_path) as f:
                item_data = json.load(f)

            model_ref = None
            if "/items/" in item_def_path:
                if "model" in item_data and isinstance(item_data["model"], dict):
                    model_ref = item_data["model"].get("model")
            elif "/models/item/" in item_def_path:
                model_ref = item_data.get("parent")

            if not model_ref or "block/" not in model_ref:
                return None, block_type

            # Detect block type from model reference
            if "slab" in model_ref:
                block_type = "slab"
            elif "stairs" in model_ref:
                block_type = "stairs"
            elif "fence_gate" in model_ref:
                block_type = "fence_gate"
            elif "fence" in model_ref:
                block_type = "fence"
            elif "wall" in model_ref:
                block_type = "wall"

            # Resolve the model to find textures
            textures = self._resolve_model_textures(zip_ref, file_list, model_ref, namespace)
            if not textures:
                return None, block_type

            # Map Minecraft face names to our 3D renderer faces
            # Minecraft faces: up, down, north, south, east, west
            # We want: up, left (north/west), right (east/south)

            # Try to find the best matches
            up_ref = textures.get("up") or textures.get("top") or textures.get("all") or textures.get("end")
            left_ref = textures.get("north") or textures.get("west") or textures.get("side") or textures.get("all")
            right_ref = textures.get("east") or textures.get("south") or textures.get("side") or textures.get("all")

            if not (up_ref and left_ref and right_ref):
                return None, block_type

            def get_tex_bytes(ref):
                if ":" in ref:
                    ns, path = ref.split(":", 1)
                else:
                    ns = namespace
                    path = ref
                tex_path = f"assets/{ns}/textures/{path}.png"
                if tex_path in file_list:
                    with zip_ref.open(tex_path) as tf:
                        return tf.read()
                return None

            up_bytes = get_tex_bytes(up_ref)
            left_bytes = get_tex_bytes(left_ref)
            right_bytes = get_tex_bytes(right_ref)

            if up_bytes and left_bytes and right_bytes:
                return {"up": up_bytes, "left": left_bytes, "right": right_bytes}, block_type

        except Exception as e:
            logger.debug(f"Failed to find block textures for {namespace}:{name_stem}: {e}")

        return None, block_type

    def _resolve_model_textures(self, zip_ref: ZipFile, file_list: set, model_ref: str, namespace: str, depth: int = 0) -> Dict[str, str]:
        """Recursively resolve model textures, following parents."""
        if depth > 10: # Prevent infinite recursion
            return {}

        if ":" in model_ref:
            ns, path = model_ref.split(":", 1)
        else:
            ns = namespace
            path = model_ref

        model_path = f"assets/{ns}/models/{path}.json"
        if model_path not in file_list:
            return {}

        try:
            with zip_ref.open(model_path) as f:
                model_data = json.load(f)

            textures = model_data.get("textures", {})

            # If there's a parent, merge its textures (child overrides parent)
            parent_ref = model_data.get("parent")
            if parent_ref:
                parent_textures = self._resolve_model_textures(zip_ref, file_list, parent_ref, ns, depth + 1)
                # Merge: child textures override parent textures
                merged = parent_textures.copy()
                merged.update(textures)
                return merged

            return textures
        except Exception:
            return {}

    def find_item_texture(self, zip_ref: ZipFile, file_list: set, namespace: str, name_stem: str, item_def_path: str) -> Optional[str]:
        """
        Find the texture path for an item by checking:
        1. Item texture: assets/<namespace>/textures/item/<name>.png
        2. Block texture: assets/<namespace>/textures/block/<name>.png
        3. Parse item definition/model and follow texture references

        Supports both old (models/item/) and new (items/) formats.
        """
        # Try direct item texture first
        item_texture = f"assets/{namespace}/textures/item/{name_stem}.png"
        if item_texture in file_list:
            return item_texture

        # Try block texture
        block_texture = f"assets/{namespace}/textures/block/{name_stem}.png"
        if block_texture in file_list:
            return block_texture

        # Parse the item definition/model to find texture references
        try:
            with zip_ref.open(item_def_path) as f:
                item_data = json.load(f)

            # Handle new format (assets/<ns>/items/<name>.json)
            if "/items/" in item_def_path:
                return self._find_texture_from_new_format(zip_ref, file_list, item_data, namespace)

            # Handle old format (assets/<ns>/models/item/<name>.json)
            elif "/models/item/" in item_def_path:
                return self._find_texture_from_old_format(zip_ref, file_list, item_data, namespace)

        except Exception as e:
            logger.debug(f"Failed to parse item definition for {namespace}:{name_stem}: {e}")

        return None

    def _find_texture_from_new_format(self, zip_ref: ZipFile, file_list: set, item_data: dict, namespace: str) -> Optional[str]:
        """Parse new format item definitions (1.21+) and find textures."""
        if "model" not in item_data or not isinstance(item_data["model"], dict):
            return None

        model_ref = item_data["model"].get("model", "")
        if not model_ref:
            return None

        # Parse model reference like "minecraft:block/crafting_table"
        if ":" in model_ref:
            model_ns, model_path = model_ref.split(":", 1)
        else:
            model_ns = namespace
            model_path = model_ref

        # Construct path to the model file
        model_file_path = f"assets/{model_ns}/models/{model_path}.json"

        if model_file_path not in file_list:
            return None

        # Load the model and extract texture references
        try:
            with zip_ref.open(model_file_path) as mf:
                model_data = json.load(mf)

            if "textures" in model_data:
                textures = model_data["textures"]
                # Prefer "particle" texture (used as item icon), then "north", then any texture
                texture_ref = textures.get("particle") or textures.get("north") or textures.get("layer0") or next(iter(textures.values()), None)

                if texture_ref:
                    # Parse texture reference like "minecraft:block/crafting_table_front"
                    if ":" in texture_ref:
                        tex_ns, tex_path = texture_ref.split(":", 1)
                    else:
                        tex_ns = model_ns
                        tex_path = texture_ref

                    # Construct texture file path
                    texture_file = f"assets/{tex_ns}/textures/{tex_path}.png"
                    if texture_file in file_list:
                        return texture_file
        except Exception as e:
            logger.debug(f"Failed to parse model {model_file_path}: {e}")

        return None

    def _find_texture_from_old_format(self, zip_ref: ZipFile, file_list: set, model_data: dict, namespace: str) -> Optional[str]:
        """Parse old format item models (pre-1.21, mods) and find textures."""
        # Old format models have textures directly in the model JSON
        if "textures" in model_data:
            textures = model_data["textures"]
            # Prefer "layer0" for items, "particle" for blocks, then any texture
            texture_ref = textures.get("layer0") or textures.get("particle") or textures.get("north") or next(iter(textures.values()), None)

            if texture_ref:
                # Parse texture reference
                if ":" in texture_ref:
                    tex_ns, tex_path = texture_ref.split(":", 1)
                else:
                    tex_ns = namespace
                    tex_path = texture_ref

                # Construct texture file path
                texture_file = f"assets/{tex_ns}/textures/{tex_path}.png"
                if texture_file in file_list:
                    return texture_file

        # Check for parent model reference
        if "parent" in model_data:
            parent_ref = model_data["parent"]
            if ":" in parent_ref:
                parent_ns, parent_path = parent_ref.split(":", 1)
            else:
                parent_ns = namespace
                parent_path = parent_ref

            parent_file = f"assets/{parent_ns}/models/{parent_path}.json"
            if parent_file in file_list:
                try:
                    with zip_ref.open(parent_file) as pf:
                        parent_data = json.load(pf)
                    # Recursively check parent
                    return self._find_texture_from_old_format(zip_ref, file_list, parent_data, parent_ns)
                except Exception:
                    pass

        return None

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
