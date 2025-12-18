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
                    asset_w = None
                    asset_h = None
                    block_type = None
                    rendered_3d = False

                    # Experimental 3D rendering for blocks
                    if self.experimental:
                        block_textures, detected_block_type = self.find_block_textures(zip_ref, file_list, namespace, name_stem, item_def_path)
                        block_type = detected_block_type or block_type
                        if block_textures:
                            asset_filename, asset_b64, asset_w, asset_h = self.asset_extractor.render_3d_block(
                                item_id, block_textures, jar_path.name, include_asset=self.include_asset, block_type=block_type
                            )
                            if asset_filename:
                                rendered_3d = True

                    # Fallback to 2D extraction if not experimental or 3D failed
                    if not asset_filename:
                        texture_path = self.find_item_texture(zip_ref, file_list, namespace, name_stem, item_def_path)

                        if not texture_path:
                            logger.debug(f"No texture found for item {item_id} in {jar_path.name}.")
                            continue

                        # Infer block_type when texture is under block textures
                        if "/textures/block/" in texture_path or ("block/" in texture_path and "/textures/" in texture_path):
                            block_type = block_type or "block"

                        # Extract Asset (optionally include base64 in metadata)
                        asset_filename, asset_b64, asset_w, asset_h = self.asset_extractor.extract_asset(
                            zip_ref, texture_path, item_id, jar_path.name, include_asset=self.include_asset
                        )

                    if asset_filename:
                        # Determine Name
                        display_name = self.get_display_name(item_id, "item", lang_data)
                        # Add to metadata (pass base64 data, sizes, and block_type when available)
                        self.metadata_handler.add_item(item_id, asset_filename, display_name, jar_path.name, asset_b64=asset_b64, width=asset_w, height=asset_h, block_type=block_type, rendered_3d=rendered_3d)

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
        if name_stem == "chest":
            block_type = "chest"
        # Temporary watch list for debugging specific items that failed to render in 3D
        debug_watch = {"blast_furnace", "blackstone", "blackstone_wall", "black_wool", "black_terracotta", "black_concrete", "black_concrete_powder"}
        try:
            with zip_ref.open(item_def_path) as f:
                item_data = json.load(f)

            model_ref = None
            if "/items/" in item_def_path:
                if "model" in item_data and isinstance(item_data["model"], dict):
                    model_ref = item_data["model"].get("model")
            elif "/models/item/" in item_def_path:
                model_ref = item_data.get("parent")

            if name_stem in debug_watch:
                logger.info(f"[DEBUG-WATCH] find_block_textures for {namespace}:{name_stem} model_ref={model_ref}")

            if not model_ref:
                return None, block_type

            original_model_ref = model_ref
            # If the item model is a builtin entity (eg. chests), we may still be able
            # to render it as a block by falling back to a block model with the same
            # name (eg. minecraft:block/chest or minecraft:block/chest_inventory).
            if model_ref.startswith("builtin") or model_ref == "item/chest":
                # First, try direct block texture (assets/<ns>/textures/block/<name>.png).
                direct_block_tex = f"assets/{namespace}/textures/block/{name_stem}.png"
                if direct_block_tex in file_list:
                    # Treat this as a block that uses a single 'all' texture
                    # and continue with normal texture resolution below.
                    model_ref = f"{namespace}:block/{name_stem}"
                else:
                    # Try a few common block model candidates
                    candidates = [f"{namespace}:block/{name_stem}",
                                  f"{namespace}:block/{name_stem}_inventory",
                                  f"{namespace}:block/{name_stem}_single"]
                    for cand in candidates:
                        # If we can resolve textures from this candidate, use it
                        cand_textures = self._resolve_model_textures(zip_ref, file_list, cand, namespace)
                        if cand_textures:
                            model_ref = cand
                            break
                # If we still don't have resolved textures via _resolve_model_textures,
                # try a direct block model file and use its 'all' or 'particle' texture
                # as a simple fallback (read PNG bytes and return pictured faces).
                block_model_path = f"assets/{namespace}/models/block/{name_stem}.json"
                if block_model_path in file_list:
                    try:
                        with zip_ref.open(block_model_path) as bf:
                            bm = json.load(bf)
                        tex = bm.get('textures', {})
                        # prefer 'all' or 'particle'
                        tex_ref = tex.get('all') or tex.get('particle')
                        if tex_ref:
                            # normalize ref to ns:path
                            if ':' in tex_ref:
                                tex_ns, tex_path = tex_ref.split(':', 1)
                            else:
                                tex_ns = namespace
                                tex_path = tex_ref
                            tex_path = tex_path.lstrip('/')
                            png = f"assets/{tex_ns}/textures/{tex_path}.png"
                            if png in file_list:
                                with zip_ref.open(png) as pf:
                                    img_bytes = pf.read()
                                # Use same image for up/left/right.
                                return {"up": img_bytes, "left": img_bytes, "right": img_bytes}, block_type
                    except Exception:
                        pass

            # We allow "block/" models, or "item/generated" / "item/handheld" (checked later for block textures)
            # If it's neither, we might skip, but let's be permissive and rely on texture resolution.

            # Detect block type from model reference and any parent models.
            # Use a comprehensive mapping of parent models to block types.
            PARENT_TO_BLOCK_TYPE = {
                "minecraft:block/cube": "block",
                "minecraft:block/cube_all": "block",
                "minecraft:block/cube_column": "block",
                "minecraft:block/cube_bottom_top": "block",
                "minecraft:block/cube_mirrored_all": "block",
                "minecraft:block/leaves": "block",
                "minecraft:block/stairs": "stairs",
                "minecraft:block/slab": "slab",
                "minecraft:block/slab_top": "slab",
                "minecraft:block/wall_inventory": "wall",
                "minecraft:block/fence_inventory": "fence",
                "minecraft:block/fence_gate_closed": "fence_gate",
                "minecraft:block/trapdoor_bottom": "trapdoor",
                "minecraft:block/pressure_plate_up": "pressure_plate",
                "minecraft:block/button_inventory": "button",
                "minecraft:block/carpet": "carpet",
                "minecraft:block/thin_block": "pane",
                "minecraft:block/anvil": "anvil",
                "minecraft:block/template_anvil": "anvil",
                "minecraft:block/chest": "chest",
                "minecraft:block/chest_inventory": "chest",
                "minecraft:block/chest_single": "chest",
                "minecraft:block/ender_chest": "chest",
                "minecraft:block/ender_chest_inventory": "chest",
                "minecraft:block/trapped_chest": "chest",
                "minecraft:block/trapped_chest_inventory": "chest",
                "minecraft:block/template_glazed_terracotta": "block",
                "minecraft:block/orientable": "block",
                "minecraft:block/orientable_with_bottom": "block",
                "minecraft:block/hopper": "hopper",
                "minecraft:block/cauldron": "cauldron",
                "minecraft:block/daylight_detector": "daylight_detector",
                "minecraft:block/beacon": "beacon",
                "minecraft:block/lantern": "lantern",
            }

            # Check immediate model_ref
            # Normalize model_ref to full ID if possible
            full_model_ref = model_ref if ":" in model_ref else f"{namespace}:{model_ref}"
            if full_model_ref in PARENT_TO_BLOCK_TYPE:
                block_type = PARENT_TO_BLOCK_TYPE[full_model_ref]
            else:
                # Fallback to substring matching if not in exact map
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
                elif "trapdoor" in model_ref:
                    block_type = "trapdoor"
                elif "pressure_plate" in model_ref:
                    block_type = "pressure_plate"
                elif "button" in model_ref:
                    block_type = "button"
                elif "carpet" in model_ref:
                    block_type = "carpet"
                elif "pane" in model_ref:
                    block_type = "pane"
                elif "snow" in model_ref:
                    block_type = "snow"
                elif "hopper" in model_ref:
                    block_type = "hopper"
                elif "cauldron" in model_ref:
                    block_type = "cauldron"
                elif "daylight_detector" in model_ref:
                    block_type = "daylight_detector"
                elif "beacon" in model_ref:
                    block_type = "beacon"
                elif "anvil" in model_ref:
                    block_type = "anvil"
                elif "lantern" in model_ref:
                    block_type = "lantern"
                elif "teleport_pad" in model_ref:
                    block_type = "teleport_pad"
                elif "fire" in model_ref or "torch" in model_ref:
                    # Force 2D for fire and torches
                    return None, block_type

            # Override for chest if we detected it as a block but missed the type
            if (original_model_ref == "item/chest" or name_stem == "chest") and block_type == "block":
                block_type = "chest"

            # If we still have a 'block' type (or want to refine it), inspect the parent chain
            try:
                parent_chain = self._get_model_parent_chain(zip_ref, file_list, model_ref, namespace)
                for pref in parent_chain:
                    # Normalize pref
                    full_pref = pref if ":" in pref else f"{namespace}:{pref}"
                    if full_pref in PARENT_TO_BLOCK_TYPE:
                        block_type = PARENT_TO_BLOCK_TYPE[full_pref]
                        break

                    # Fallback substring checks on parents
                    if "slab" in pref:
                        block_type = "slab"
                        break
                    if "stairs" in pref:
                        block_type = "stairs"
                        break
                    if "fence" in pref:
                        block_type = "fence"
                        break
                    if "wall" in pref:
                        block_type = "wall"
                        break
                    if "trapdoor" in pref:
                        block_type = "trapdoor"
                        break
                    if "anvil" in pref:
                        block_type = "anvil"
                        break
            except Exception:
                # Be conservative: if anything goes wrong, keep default 'block'
                pass

            # Force 2D for saplings, clusters, and other cross models
            # Also force 2D for complex entities like beds, shulker boxes, banners, boats, rafts
            # Note: "raft" matches "minecraft", so use "_raft"
            exclusion_keywords = ["sapling", "cluster", "cross", "plant", "coral", "weed", "grass", "fern", "flower", "fungus", "roots", "sprouts", "bamboo", "cane", "kelp", "vine", "bars", "chain", "ladder", "rail", "bed", "shulker", "banner", "boat", "_raft", "shield", "trident"]

            matched_keyword = None
            for keyword in exclusion_keywords:
                if keyword in model_ref:
                    matched_keyword = keyword
                    break

            if matched_keyword:
                 # Exception: bamboo_planks, bamboo_mosaic, bamboo_block are blocks.
                 # The check "bamboo" in model_ref is too aggressive.
                 # We should only exclude "bamboo" if it's the plant, not the wood.
                 # "bamboo_stalk" or just "bamboo" (the item).
                 # But "bamboo_planks" contains "bamboo".

                 # Refined check:
                 is_blocky_bamboo = "planks" in model_ref or "mosaic" in model_ref or "bamboo_block" in model_ref or "stripped" in model_ref or "slab" in model_ref or "stairs" in model_ref or "fence" in model_ref or "door" in model_ref or "trapdoor" in model_ref or "button" in model_ref or "pressure_plate" in model_ref

                 if matched_keyword == "bamboo" and is_blocky_bamboo:
                     pass # Allow 3D rendering
                 elif matched_keyword == "grass" and "grass_block" in model_ref:
                     pass # Allow 3D rendering for grass_block
                 elif matched_keyword == "bed" and "bedrock" in model_ref:
                     pass # Allow 3D rendering for bedrock
                 else:
                     return None, block_type

            # Resolve the model to find textures
            textures = self._resolve_model_textures(zip_ref, file_list, model_ref, namespace)

            # Merge textures defined in the item definition itself (overrides)
            if "textures" in item_data:
                textures.update(item_data["textures"])

            # Special case for Ores/Items that use item/generated but point to a block texture
            # If layer0 is present (from item definition) and points to a block, treat as block.
            if "layer0" in textures:
                l0 = textures["layer0"]
                if "block/" in l0 or "blocks/" in l0:
                    textures["all"] = l0

            if not textures:
                return None, block_type

            # Map Minecraft face names to our 3D renderer faces
            # Minecraft faces: up, down, north, south, east, west
            # We want: up, left (north/west), right (east/south)

            # Special handling for Beacon (uses 'glass' and 'beacon')
            if block_type == "beacon" and "glass" in textures:
                textures["all"] = textures["glass"]

            # Special handling for Anvil (uses 'top', 'body' -> side?)
            if block_type == "anvil":
                # Anvil textures: top, body (base/neck?)
                # We map body to side (left/right)
                if "body" in textures:
                    textures["side"] = textures["body"]
                # If west/east/north/south exist, they override side

            # Special handling for Glazed Terracotta (uses 'pattern')
            if "pattern" in textures:
                textures["all"] = textures["pattern"]

            # Special handling for Carpet (uses 'wool')
            if block_type == "carpet" and "wool" in textures:
                textures["all"] = textures["wool"]

            # Special handling for Ores/Generated blocks (layer0 -> all)
            if "layer0" in textures:
                # Check if layer0 points to a block texture
                l0 = textures["layer0"]
                if "block/" in l0 or "blocks/" in l0:
                    textures["all"] = l0

            # Special handling for Wall models (often provide 'wall' -> block reference)
            if "wall" in textures and "all" not in textures:
                textures["all"] = textures["wall"]

            # Try to find the best matches
            # up: top face
            up_ref = textures.get("up") or textures.get("top") or textures.get("all") or textures.get("end") or textures.get("texture") or textures.get("particle")
            # left: front/north face
            left_ref = textures.get("north") or textures.get("front") or textures.get("west") or textures.get("side") or textures.get("all") or textures.get("texture")
            # right: side/east face
            right_ref = textures.get("east") or textures.get("side") or textures.get("south") or textures.get("back") or textures.get("all") or textures.get("texture")

            if not (up_ref and left_ref and right_ref):
                return None, block_type

            def get_tex_bytes(ref):
                # Resolve local texture references that start with '#'
                depth = 0
                while isinstance(ref, str) and ref.startswith('#') and depth < 10:
                    key = ref[1:]
                    ref = textures.get(key)
                    depth += 1

                if not isinstance(ref, str):
                    return None

                if ":" in ref:
                    ns, path = ref.split(":", 1)
                else:
                    ns = namespace
                    path = ref

                # Strip any leading '/' from path
                path = path.lstrip('/')

                tex_path = f"assets/{ns}/textures/{path}.png"
                if tex_path in file_list:
                    with zip_ref.open(tex_path) as tf:
                        return tf.read()
                logger.debug(f"Texture path not found for ref '{ref}' -> {tex_path}")
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
        if depth > 10:  # Prevent infinite recursion
            return {}

        # Normalize namespace and path
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

            textures = model_data.get("textures", {}) or {}

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

    def _get_model_parent_chain(self, zip_ref: ZipFile, file_list: set, model_ref: str, namespace: str, depth: int = 0) -> list:
        """Return a list of model reference strings starting with model_ref and including parent refs up the chain."""
        if depth > 10:
            return []

        chain = []
        if ":" in model_ref:
            ns, path = model_ref.split(":", 1)
        else:
            ns = namespace
            path = model_ref

        model_path = f"assets/{ns}/models/{path}.json"
        if model_path not in file_list:
            return chain

        try:
            with zip_ref.open(model_path) as f:
                model_data = json.load(f)

            chain.append(path)

            parent_ref = model_data.get("parent")
            if parent_ref:
                # Normalize parent ref to a simple path string when possible
                if ":" in parent_ref:
                    _, parent_path = parent_ref.split(":", 1)
                else:
                    parent_path = parent_ref
                chain.extend(self._get_model_parent_chain(zip_ref, file_list, parent_ref, ns, depth + 1))
        except Exception:
            pass

        return chain

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

        # Resolve all textures recursively using the existing helper
        textures = self._resolve_model_textures(zip_ref, file_list, model_ref, namespace)

        if textures:
            # Prefer "layer0" (standard for items), "particle", "north", then any
            texture_ref = textures.get("layer0") or textures.get("particle") or textures.get("north") or next(iter(textures.values()), None)

            if texture_ref:
                # Parse texture reference like "minecraft:block/crafting_table_front"
                if ":" in texture_ref:
                    tex_ns, tex_path = texture_ref.split(":", 1)
                else:
                    tex_ns = namespace
                    tex_path = texture_ref

                # Construct texture file path
                texture_file = f"assets/{tex_ns}/textures/{tex_path}.png"
                if texture_file in file_list:
                    return texture_file

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
