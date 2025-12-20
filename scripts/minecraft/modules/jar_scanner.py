import json
import re
import tomllib
import base64
import io
from pathlib import Path
import typing
from zipfile import ZipFile
from typing import Dict, Optional, Tuple, Any
from PIL import Image

from .constants import JARS_DIR, ASSETS_DIR
from .logger import logger
from .metadata_handler import MetadataHandler
from .asset_extractor import AssetExtractor

class JarScanner:
    def __init__(self, use_mongodb: bool = False, collection_name: Optional[str] = None, include_asset: bool = False, overwrite: bool = False, experimental: bool = True):
        self.metadata_handler = MetadataHandler(use_mongodb=use_mongodb, collection_name=collection_name, overwrite=overwrite)
        self.asset_extractor = AssetExtractor()
        self.include_asset = include_asset
        self.overwrite = overwrite
        self.experimental = experimental

    def extract_mod_info(self, zip_ref: ZipFile) -> Optional[Dict[str, Any]]:
        """
        Extract mod information from META-INF/*.toml files.
        """
        for file_path in zip_ref.namelist():
            if file_path.startswith("META-INF/") and file_path.endswith(".toml"):
                try:
                    with zip_ref.open(file_path) as f:
                        data = tomllib.load(f)

                        # Check for 'mods' list which is common in mods.toml
                        if "mods" in data and isinstance(data["mods"], list) and len(data["mods"]) > 0:
                            mod = data["mods"][0] # Take the first mod
                            mod_info = {
                                "id": mod.get("modId", ""),
                                "version": mod.get("version", ""),
                                "name": mod.get("displayName", "")
                            }

                            logo_file = mod.get("logoFile")
                            if logo_file:
                                logo_path = logo_file.strip()
                                if logo_path in zip_ref.namelist():
                                    try:
                                        with zip_ref.open(logo_path) as logo_f:
                                            logo_content = logo_f.read()

                                            # Check size < 5KB
                                            if len(logo_content) < 5 * 1024:
                                                # Check dimensions
                                                with Image.open(io.BytesIO(logo_content)) as img:
                                                    if img.width == img.height:
                                                        # It's valid
                                                        b64_content = base64.b64encode(logo_content).decode('utf-8')
                                                        content_type = f"image/{img.format.lower()}"

                                                        mod_info["icon"] = {
                                                            "asset_b64": b64_content,
                                                            "content_type": content_type
                                                        }
                                    except Exception as e:
                                        logger.warning(f"Failed to process logo file {logo_path}: {e}")

                            return mod_info
                except Exception as e:
                    logger.warning(f"Failed to parse TOML file {file_path}: {e}")
        return None

    def scan_jars(self):
        jar_files = list(JARS_DIR.glob("*.jar"))
        if not jar_files:
            logger.warning(f"No .jar files found in {JARS_DIR}")
            return

        # Find Minecraft JAR (client or minecraft in name)
        minecraft_jar = next((j for j in jar_files if "client" in j.name.lower() or "minecraft" in j.name.lower()), None)

        # Sort so Minecraft is first
        if minecraft_jar:
            if minecraft_jar in jar_files:
                jar_files.remove(minecraft_jar)
            jar_files.insert(0, minecraft_jar)

        # Open Minecraft JAR for fallback
        fallback_zip = None
        if minecraft_jar:
             try:
                 fallback_zip = ZipFile(minecraft_jar, 'r')
                 logger.info(f"Using {minecraft_jar.name} as fallback asset source.")
             except Exception as e:
                 logger.warning(f"Failed to open fallback JAR {minecraft_jar.name}: {e}")

        for jar_path in jar_files:
            self.process_jar(jar_path, fallback_zip)

        if fallback_zip:
            fallback_zip.close()

        self.metadata_handler.save_metadata()
        self.metadata_handler.close()

    def get_spawn_egg_color(self, item_id: str) -> Tuple[int, int, int]:
        """Returns the primary color for a spawn egg."""
        # Map of mob names to their primary spawn egg color
        # This is a partial list; ideally this would be extracted from game code
        EGG_COLORS = {
            "allay": (0, 176, 255),
            "armadillo": (175, 108, 80),
            "axolotl": (247, 199, 218),
            "bat": (76, 62, 48),
            "bee": (237, 195, 67),
            "blaze": (246, 182, 1),
            "bogged": (138, 142, 109),
            "breeze": (174, 168, 210),
            "camel": (255, 204, 92),
            "cat": (239, 190, 104),
            "cave_spider": (12, 66, 62),
            "chicken": (161, 161, 161),
            "cod": (193, 161, 115),
            "cow": (68, 54, 38),
            "creeper": (13, 167, 2),
            "dolphin": (34, 165, 240),
            "donkey": (83, 69, 51),
            "drowned": (143, 241, 215),
            "elder_guardian": (206, 206, 206),
            "ender_dragon": (28, 28, 28),
            "enderman": (22, 22, 22),
            "endermite": (22, 22, 22),
            "evoker": (149, 155, 155),
            "fox": (213, 182, 153),
            "frog": (208, 116, 68),
            "ghast": (249, 249, 249),
            "glow_squid": (9, 86, 86),
            "goat": (166, 158, 149),
            "guardian": (90, 171, 165),
            "hoglin": (198, 109, 85),
            "horse": (192, 158, 125),
            "husk": (121, 112, 97),
            "iron_golem": (220, 210, 200),
            "llama": (192, 158, 125),
            "magma_cube": (52, 0, 0),
            "mooshroom": (160, 15, 16),
            "mule": (28, 18, 13),
            "ocelot": (239, 190, 104),
            "panda": (230, 230, 230),
            "parrot": (14, 167, 222),
            "phantom": (68, 84, 147),
            "pig": (240, 165, 162),
            "piglin": (153, 95, 64),
            "piglin_brute": (22, 14, 11),
            "pillager": (83, 49, 43),
            "polar_bear": (236, 236, 236),
            "pufferfish": (246, 182, 1),
            "rabbit": (153, 95, 64),
            "ravager": (117, 116, 112),
            "salmon": (160, 15, 16),
            "sheep": (231, 231, 231),
            "shulker": (148, 103, 148),
            "silverfish": (110, 110, 110),
            "skeleton": (193, 193, 193),
            "skeleton_horse": (104, 104, 104),
            "slime": (81, 160, 62),
            "sniffer": (137, 23, 23),
            "snow_golem": (255, 255, 255),
            "spider": (52, 45, 45),
            "squid": (34, 59, 77),
            "stray": (97, 118, 119),
            "strider": (156, 53, 49),
            "tadpole": (110, 108, 108),
            "trader_llama": (231, 192, 141),
            "tropical_fish": (239, 105, 119),
            "turtle": (231, 231, 231),
            "vex": (128, 152, 203),
            "villager": (86, 60, 51),
            "vindicator": (149, 155, 155),
            "wandering_trader": (69, 70, 138),
            "warden": (15, 70, 73),
            "witch": (52, 0, 0),
            "wither": (20, 20, 20),
            "wither_skeleton": (20, 20, 20),
            "wolf": (215, 211, 211),
            "zoglin": (198, 109, 85),
            "zombie": (0, 175, 175),
            "zombie_horse": (49, 82, 52),
            "zombie_villager": (86, 60, 51),
            "zombified_piglin": (234, 153, 153),
        }

        for mob, color in EGG_COLORS.items():
            if mob in item_id:
                return color

        return (255, 255, 255) # Default white

    def get_tint_for_item(self, item_id: str, name_stem: str) -> Optional[Tuple[int, int, int]]:
        """Returns a tint color (R, G, B) for specific items like grass or banners."""

        # Vegetation (Plains Biome Tint)
        # fern, large_fern, lily_pad, grass_block, short_grass, tall_grass, vine
        if item_id in [
            "minecraft:fern", "minecraft:large_fern", "minecraft:lily_pad",
            "minecraft:grass_block", "minecraft:short_grass", "minecraft:tall_grass",
            "minecraft:vine", "minecraft:sugar_cane"
        ] or "leaves" in name_stem:
             return (145, 189, 89)

        # Leather Armor (Default Brown)
        if item_id in [
            "minecraft:leather_boots", "minecraft:leather_chestplate",
            "minecraft:leather_helmet", "minecraft:leather_horse_armor",
            "minecraft:leather_leggings"
        ]:
            return (160, 101, 64)

        # Potion Colors (Basic approximation)
        if "potion" in name_stem:
             return (56, 93, 198) # Water color default

        # Spawn Eggs
        if "spawn_egg" in name_stem:
            return self.get_spawn_egg_color(item_id)

        if "grass" in name_stem:
            return (145, 189, 89)  # Standard grass color

        # Banner colors
        COLOR_MAP = {
            "white": (255, 255, 255),
            "orange": (216, 127, 51),
            "magenta": (178, 76, 216),
            "light_blue": (102, 153, 216),
            "yellow": (229, 229, 51),
            "lime": (127, 204, 25),
            "pink": (242, 127, 165),
            "gray": (76, 76, 76),
            "light_gray": (153, 153, 153),
            "cyan": (76, 127, 153),
            "purple": (127, 63, 178),
            "blue": (51, 76, 178),
            "brown": (102, 76, 51),
            "green": (102, 127, 51),
            "red": (153, 51, 51),
            "black": (25, 25, 25)
        }

        for color, rgb in COLOR_MAP.items():
            if color in name_stem:
                return rgb

        return None

    def process_jar(self, jar_path: Path, fallback_zip: Optional[ZipFile] = None):
        logger.info(f"Processing JAR: {jar_path.name}")
        try:
            with ZipFile(jar_path, 'r') as zip_ref:
                # Load language file
                lang_data = self.load_language_file(zip_ref)

                # Extract mod info
                mod_info = self.extract_mod_info(zip_ref)
                if mod_info:
                    logger.info(f"Found mod info: {mod_info.get('name')} ({mod_info.get('version')})")

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
                    # (If experimental mode is enabled, all items should be considered for experimental rendering.)

                    # Skip model variants that aren't actual inventory items
                    if self.is_model_variant(item_id):
                        logger.debug(f"Skipping model variant: {item_id}")
                        continue

                    # Skip if already exists in metadata
                    if self.metadata_handler.item_exists(item_id) and not self.overwrite:
                        logger.warning(f"Duplicate item ID found: {item_id} in {jar_path.name}. Skipping.")
                        continue

                    # Extract parent from model definition
                    parent = None
                    try:
                        with zip_ref.open(item_def_path) as f:
                            model_data = json.load(f)
                            parent = model_data.get("parent")
                    except Exception:
                        pass

                    # Determine the texture path for this item
                    namespace, name_stem = item_id.split(':')

                    # Skip items that are variants we don't want (e.g. _bottom leaves)
                    if name_stem.endswith("_bottom") and ("leaves" in name_stem or "log" in name_stem):
                        logger.info(f"Skipping variant item: {item_id}")
                        continue

                    asset_filename = None
                    asset_b64 = None
                    asset_w = None
                    asset_h = None
                    asset_model_path = None
                    asset_model_data = None
                    block_type = None
                    rendered_3d = False
                    mcmeta_data = None
                    content_type = "image/png"
                    tint_color = self.get_tint_for_item(item_id, name_stem)

                    # Check for special rendering overrides
                    force_2d = False
                    if "coral_fan" in name_stem:
                        force_2d = True
                    elif "coral" in name_stem and "coral_block" not in name_stem:
                        force_2d = True

                    fungus_include_list: typing.List[str] = ["mushroom", "fungus"]
                    fungus_ignore_list: typing.List[str] = ["block", "stem", "stew", "rice", "pizza", "basket", "wreath", "nether_wart", "burger" "stuffed", "cream", "lasagna", "omelette", "steak", "item", "cap", "food", "barrel", ]

                    crystals_include_list: typing.List[str] = ["amethyst", "bud", "cluster"]
                    crystals_ignore_list: typing.List[str] = ["block", "shard", "budding_amethyst"]
                    is_cross_crystal: bool = any(crystal in name_stem for crystal in crystals_include_list) and all(ign not in name_stem for ign in crystals_ignore_list)

                    # check if the name_stem includes any fungus terms, excluding ignore terms
                    is_cross_fungus: bool = any(fungus in name_stem for fungus in fungus_include_list) and all(ign not in name_stem for ign in fungus_ignore_list)

                    cross_include_list = ["sapling", "cobweb", "dead_bush"]
                    cross_exclude_list = ["block", "wall", "head", "skull", "item"]
                    is_cross_item = any(cross in name_stem for cross in cross_include_list) and all(ign not in name_stem for ign in cross_exclude_list)

                    # Check for Cross rendering
                    is_cross = False
                    if is_cross_item or \
                        is_cross_fungus or \
                        is_cross_crystal:
                        is_cross = True
                        block_type = "cross"

                    flower_include_list = [
                        "snowdrops",
                        "poppy",
                        "tulip",
                        "cornflower",
                        "dandelion",
                        "wither_rose",
                        "torchflower",
                        "rose_bush",
                        "oxeye_daisy",
                        "peony",
                        "eyeblossom",
                        "crimson_roots",
                        "warped_roots",
                        "hanging_roots",
                        "vines",
                        "fern",
                        "grass"
                        "snowdrops",
                        "snowbelle",
                    ]
                    flower_exclude_list = [
                        "block",
                        "wall",
                        "pot",
                    ]
                    is_flower: bool = any(flower in name_stem for flower in flower_include_list) and all(ign not in name_stem for ign in flower_exclude_list)
                    if is_flower:
                        force_2d = True
                        block_type = "flower"

                    # Check for Flower rendering (Force 2D)
                    # flower_items = [
                    #     "minecraft:poppy",
                    #     "minecraft:white_tulip",
                    #     "minecraft:orange_tulip",
                    #     "minecraft:pink_tulip",
                    #     "minecraft:red_tulip",
                    #     "minecraft:cornflower",
                    #     "minecraft:torchflower",
                    #     "minecraft:dandelion",
                    #     "minecraft:wither_rose",
                    #     "minecraft:rose_bush",
                    #     "minecraft:oxeye_daisy",
                    #     "minecraft:closed_eyeblossom",
                    #     "minecraft:open_eyeblossom",
                    #     "minecraft:peony",
                    #     "minecraft:crimson_roots",
                    #     "minecraft:hanging_roots",
                    #     "minecraft:warped_roots",
                    #     "minecraft:twisting_vines",
                    #     "minecraft:weeping_vines",
                    #     "minecraft:vine",
                    #     "minecraft:large_fern",
                    #     "minecraft:fern",
                    #     "minecraft:tall_grass",
                    #     "minecraft:short_grass"
                    # ]
                    # if item_id in flower_items:
                    #     force_2d = True
                    #     block_type = "flower"

                    # Check for Tinting (Grass Block, Ferns, Grass)
                    tint_items = ["minecraft:grass_block", "minecraft:fern", "minecraft:large_fern", "minecraft:tall_grass", "minecraft:short_grass", "minecraft:lily_pad"]
                    if item_id in tint_items:
                        # Plains biome color: #91BD59 -> (145, 189, 89)
                        tint_color = (145, 189, 89)

                    # Check for Lily Pad (render as pad: bottom has asset, sides/top transparent)
                    if item_id.endswith(":lily_pad") or item_id.endswith("_lily_pad") or item_id.endswith("_lily_pads"):
                        force_2d = False
                        block_type = "pad"

                    # Check for Sprite Flat (render as sprite_flat: flat on ground)
                    if item_id in []:
                        force_2d = True
                        block_type = "sprite_flat"

                    # Attempt to extract model JSON for ALL items (don't write to disk) so we can include
                    # the model information in metadata if present.
                    try:
                        model_info = self.extract_model_asset(zip_ref, file_list, namespace, name_stem, item_def_path)
                        if model_info:
                            asset_model_path, asset_model_data = model_info
                    except Exception:
                        # Non-fatal — continue without model info
                        asset_model_path = None
                        asset_model_data = None

                    # Experimental Model Rendering
                    # When experimental mode is enabled, prefer rendering using model definitions
                    # for all items (not just the watch list). Fall back to texture-based extraction
                    # when no model definition is available or rendering fails.
                    missing_textures = []
                    if self.experimental and not force_2d:
                        if asset_model_data and isinstance(asset_model_data, dict):
                            logger.info(f"Attempting experimental model rendering for {item_id}")
                            try:
                                asset_filename, asset_b64, asset_w, asset_h, missing_textures = self.asset_extractor.render_model(
                                    zip_ref, asset_model_data, namespace, item_id, self.include_asset, self.overwrite, tint=tint_color, fallback_zip=fallback_zip
                                )
                                if asset_filename:
                                    # Validate resulting image isn't fully transparent. If it is,
                                    # we'll fall back to texture extraction.
                                    try:
                                        from PIL import Image
                                        p = ASSETS_DIR / asset_filename
                                        if p.exists():
                                            with Image.open(p) as img:
                                                non_trans = sum(1 for px in img.getdata() if px[3] > 10)
                                            if non_trans == 0:
                                                logger.warning(f"Experimental render for {item_id} is fully transparent - falling back.")
                                                asset_filename = None
                                                asset_b64 = None
                                                asset_w = None
                                                asset_h = None
                                    except Exception:
                                        pass

                                if asset_filename:
                                    rendered_3d = True
                                    if asset_filename.endswith(".webp"):
                                        content_type = "image/webp"
                                    elif asset_filename.endswith(".gif"):
                                        content_type = "image/gif"
                            except Exception as e:
                                logger.exception(f"Experimental rendering failed for {item_id}: {e}")
                        else:
                            # No model JSON available; will fall back to texture extraction below
                            logger.debug(f"Experimental rendering requested but no model found for {item_id}")

                    # Ignore certain model parents/loaders that don't have asset support (pattern-based)
                    IGNORE_PARENT_SUBSTRINGS = ["neoforge:item/bucket_drip", "allthemodium:block/source_jar"]
                    IGNORE_LOADER_SUBSTRINGS = ["neoforge:item/bucket_drip"]
                    try:
                        if asset_model_data and isinstance(asset_model_data, dict):
                            parent_ref = asset_model_data.get("parent")
                            loader_ref = asset_model_data.get("loader")

                            def matches_ignore(ref: str, patterns: list) -> bool:
                                if not ref:
                                    return False
                                return any(pat in ref for pat in patterns)

                            if matches_ignore(parent_ref, IGNORE_PARENT_SUBSTRINGS) or matches_ignore(loader_ref, IGNORE_LOADER_SUBSTRINGS):
                                logger.info(f"Skipping item {item_id} because model parent/loader '{parent_ref or loader_ref}' matches ignore patterns (no assets available).")
                                continue
                    except Exception:
                        # Safe fallback — if anything goes wrong, don't block processing
                        pass

                    # Check for 3D Blocks (Force 3D)
                    if item_id in [
                        "minecraft:flowering_azalea_leaves",
                        "minecraft:dried_kelp_block",
                        "minecraft:brain_coral_block",
                        "minecraft:horn_coral_block",
                        "minecraft:dead_bubble_coral_block",
                        "minecraft:dead_brain_coral_block",
                        "minecraft:bubble_coral_block",
                        "minecraft:dead_tube_coral_block",
                        "minecraft:dead_fire_coral_block",
                        "minecraft:fire_coral_block",
                        "minecraft:dead_horn_coral_block",
                        "minecraft:tube_coral_block"
                    ]:
                        force_2d = False
                        block_type = "block"

                    # Check for Dragon Egg
                    if item_id == "minecraft:dragon_egg":
                        force_2d = False
                        block_type = "dragon_egg"

                    # force 2d
                    enforce_2d_include_list = ["torch", "wormhole_frame"]
                    enforce_2d_ignore_list = ["block", "wall"]
                    is_enforced_2d: bool = (any(term in name_stem for term in enforce_2d_include_list) and all(ign not in name_stem for ign in enforce_2d_ignore_list)) or item_id.startswith("additional_lights:")

                    if is_enforced_2d:
                        force_2d = True


                    # Try 3D rendering for blocks first (now default)
                    if not force_2d and not asset_filename:
                        # If it's a cross type, we need to find the texture differently?
                        # find_block_textures usually looks for 'up', 'left', 'right'.
                        # For cross, we just need one texture.
                        # Let's see if find_block_textures handles it or if we need to hack it.
                        # Usually cross models in json have "cross": "texture".
                        # find_block_textures might fail if it looks for cube faces.

                        block_textures = None
                        detected_block_type = None

                        mob_head_include_list = [
                            "player_head",
                            "zombie_head",
                            "creeper_head",
                            "skeleton_skull",
                            "wither_skeleton_skull",
                            "piglin_head",

                            # not specifically a mob head, but renders as 8x8x8
                            "conduit"
                        ]
                        mob_head_exclude_list = []
                        is_mob_head: bool = any(head in name_stem for head in mob_head_include_list) and all(ign not in name_stem for ign in mob_head_exclude_list)

                        # Check for Mob Heads (8x8x8)
                        head_textures_map = {
                            "minecraft:player_head": "assets/minecraft/textures/entity/steve.png",
                            "minecraft:zombie_head": "assets/minecraft/textures/entity/zombie/zombie.png",
                            "minecraft:creeper_head": "assets/minecraft/textures/entity/creeper/creeper.png",
                            "minecraft:skeleton_skull": "assets/minecraft/textures/entity/skeleton/skeleton.png",
                            "minecraft:wither_skeleton_skull": "assets/minecraft/textures/entity/skeleton/wither_skeleton.png",
                            "minecraft:piglin_head": "assets/minecraft/textures/entity/piglin/piglin.png"
                        }
                        # is_mob_head = item_id in head_textures_map

                        if is_cross:
                            # Special handling for cross textures
                            # We need to find the texture and populate 'up', 'left', 'right' with it so render_3d_block works
                            # Or just pass it.
                            # Let's try to find the texture using find_item_texture logic but keep it as bytes.
                            tex_path = self.find_item_texture(zip_ref, file_list, namespace, name_stem, item_def_path)
                            if tex_path:
                                try:
                                    with zip_ref.open(tex_path) as f:
                                        tex_data = f.read()
                                    block_textures = {'up': tex_data, 'left': tex_data, 'right': tex_data}
                                    detected_block_type = "cross"
                                except Exception:
                                    pass
                        elif is_mob_head and item_id in head_textures_map:
                            tex_path = head_textures_map[item_id]
                            if tex_path in file_list:
                                try:
                                    with zip_ref.open(tex_path) as f:
                                        tex_data = f.read()
                                    block_textures = {'skin': tex_data}
                                    detected_block_type = "mob_head"
                                except Exception:
                                    pass
                        else:
                            block_textures, detected_block_type = self.find_block_textures(zip_ref, file_list, namespace, name_stem, item_def_path)

                        # Special handling for sprite_flat if find_block_textures failed
                        if not block_textures and block_type == "sprite_flat":
                            tex_path = self.find_item_texture(zip_ref, file_list, namespace, name_stem, item_def_path)
                            if tex_path:
                                try:
                                    with zip_ref.open(tex_path) as f:
                                        tex_data = f.read()
                                    block_textures = {"all": tex_data}
                                except Exception:
                                    pass

                        # Only overwrite block_type if it's still the default 'block' or None
                        if block_type in ["block", None]:
                            block_type = detected_block_type or block_type

                        if block_textures:
                            asset_filename, asset_b64, asset_w, asset_h = self.asset_extractor.render_3d_block(
                                item_id, block_textures, jar_path.name, include_asset=self.include_asset, block_type=block_type, tint=tint_color, overwrite=self.overwrite
                            )
                            if asset_filename:
                                rendered_3d = True
                                # Validate resulting image isn't fully transparent. If it is,
                                # attempt one more render pass (overwrite) as a fallback.
                                try:
                                    from PIL import Image
                                    p = ASSETS_DIR / asset_filename
                                    if p.exists():
                                        with Image.open(p) as img:
                                            non_trans = sum(1 for px in img.getdata() if px[3] > 10)
                                        if non_trans == 0:
                                            logger.warning(f"Rendered asset for {item_id} is fully transparent - retrying render.")
                                            # Retry rendering (overwrite) - preserve tint/block_type
                                            asset_filename, asset_b64, asset_w, asset_h = self.asset_extractor.render_3d_block(
                                                item_id, block_textures, jar_path.name, include_asset=self.include_asset, block_type=block_type, tint=tint_color, overwrite=True
                                            )
                                            if asset_filename:
                                                rendered_3d = True
                                except Exception:
                                    # Non-fatal - continue
                                    pass

                    # Fallback to 2D extraction if 3D failed or not applicable
                    if not asset_filename:
                        texture_path = self.find_item_texture(zip_ref, file_list, namespace, name_stem, item_def_path)

                        if not texture_path:
                            logger.debug(f"No texture found for item {item_id} in {jar_path.name}.")

                            # If we have a model JSON available, try to infer a texture reference from the model
                            if asset_model_data and isinstance(asset_model_data, dict):
                                textures_map = asset_model_data.get("textures", {})
                                # Prefer 'layer0', 'particle', 'texture', 'all', 'north', then any
                                keys_to_try = ["layer0", "particle", "texture", "all", "north", "side", "top", "bottom"]
                                for k in keys_to_try:
                                    tex_ref = textures_map.get(k)
                                    if not tex_ref:
                                        continue
                                    if ":" in tex_ref:
                                        tex_ns, tex_path = tex_ref.split(":", 1)
                                    else:
                                        tex_ns = namespace
                                        tex_path = tex_ref
                                    candidate = f"assets/{tex_ns}/textures/{tex_path}.png"
                                    if candidate in file_list:
                                        texture_path = candidate
                                        logger.debug(f"Inferred texture for {item_id} from model: {texture_path}")
                                        break

                        mcmeta_data = None
                        content_type = "image/png"

                        if texture_path:
                            # Check for animated sprite (mcmeta)
                            mcmeta_path = texture_path + ".mcmeta"

                            if mcmeta_path in file_list:
                                try:
                                    with zip_ref.open(mcmeta_path) as f:
                                        mcmeta_data = json.load(f)

                                    if mcmeta_data and "animation" in mcmeta_data:
                                        block_type = "sprite_animated"
                                        content_type = "image/gif"

                                        with zip_ref.open(texture_path) as f:
                                            tex_data = f.read()

                                        asset_filename, asset_b64, asset_w, asset_h = self.asset_extractor.render_animated_sprite(
                                            item_id, tex_data, mcmeta_data, jar_path.name, include_asset=self.include_asset, overwrite=self.overwrite
                                        )
                                except Exception as e:
                                    logger.warning(f"Failed to process animated sprite for {item_id}: {e}")
                                    # Fallback to normal extraction if animation fails
                                    mcmeta_data = None
                                    block_type = block_type or "flat"
                                    content_type = "image/png"

                            # Infer block_type when texture is under block textures
                            if not mcmeta_data:
                                if "/textures/block/" in texture_path or ("block/" in texture_path and "/textures/" in texture_path):
                                    block_type = block_type or "block"

                                # If this is a sprite_flat, prefer rendering the final 32x32 asset directly
                                if block_type == "sprite_flat":
                                    try:
                                        with zip_ref.open(texture_path) as f:
                                            tex_data = f.read()
                                        # Render the sprite_flat and overwrite any existing asset
                                        asset_filename, asset_b64, asset_w, asset_h = self.asset_extractor.render_3d_block(
                                            item_id, {"all": tex_data}, jar_path.name, include_asset=self.include_asset, block_type=block_type, tint=tint_color, overwrite=True
                                        )
                                    except Exception:
                                        asset_filename = None
                                        asset_b64 = None
                                        asset_w = None
                                        asset_h = None
                                else:
                                    # Extract Asset (optionally include base64 in metadata)
                                    asset_filename, asset_b64, asset_w, asset_h = self.asset_extractor.extract_asset(
                                        zip_ref, texture_path, item_id, jar_path.name, include_asset=self.include_asset, tint=tint_color, overwrite=self.overwrite
                                    )

                            # If it's 2D and no specific block type is set, mark it as flat
                            if not block_type and (force_2d or is_enforced_2d):
                                block_type = "flat"
                                force_2d = True

                    # Always add the item to metadata even if asset or model are missing
                    display_name = self.get_display_name(item_id, "item", lang_data)

                    # Ensure lily pad specifically uses the 'pad' block type
                    if item_id.endswith(":lily_pad") or item_id.endswith("_lily_pad") or item_id.endswith("_lily_pads"):
                        block_type = "pad"

                    # Ensure sprite flat items use the 'sprite_flat' block type
                    if item_id in []:
                        block_type = "sprite_flat"

                    # If user requested base64 assets but none were generated, skip the item
                    if self.include_asset and not asset_b64:
                        logger.info(f"Skipping item {item_id} because include_asset is set but no base64 asset was available.")
                        continue

                    # Ensure asset field is a string (filename). If we didn't extract an asset, default to expected filename
                    if asset_filename:
                        final_asset_name = asset_filename
                    else:
                        # Create a placeholder visible asset so UIs don't render a blank/transparent PNG
                        final_asset_name = AssetExtractor.create_placeholder_asset(item_id)

                    # Build model object for metadata if we found it, otherwise None
                    model_obj = None
                    if asset_model_data:
                        # Extract full hierarchy
                        hierarchy = []
                        resolved_model = None
                        if asset_model_path:
                            # asset_model_path is like "assets/namespace/models/item/name.json"
                            # We need to convert it back to a model ref or just start the chain from the item ID's model
                            # Actually, asset_model_data comes from extract_model_asset which parses the item definition.
                            # Let's try to get the starting model ref from asset_model_data if possible, or infer it.

                            start_model_ref = None
                            if "parent" in asset_model_data:
                                start_model_ref = asset_model_data["parent"]

                            # If we have a starting ref (parent of the item model), get its chain
                            if start_model_ref:
                                hierarchy = self._get_model_parent_chain(zip_ref, file_list, start_model_ref, namespace)

                            # Resolve the full model data for metadata
                            try:
                                resolved_model = self.asset_extractor.resolve_model_data(zip_ref, asset_model_data, namespace, fallback_zip=fallback_zip)
                            except Exception:
                                pass

                        model_obj = {"path": asset_model_path, "hierarchy": hierarchy, "resolved": resolved_model, "missing_textures": missing_textures, **asset_model_data}

                    # Add to metadata (pass base64 data, sizes, block_type, rendered_3d, mod_info)
                    self.metadata_handler.add_item(
                        item_id,
                        final_asset_name,
                        display_name,
                        jar_path.name,
                        asset_b64=asset_b64,
                        width=asset_w,
                        height=asset_h,
                        block_type=block_type,
                        rendered_3d=rendered_3d,
                        mod_info=mod_info,
                        parent=parent,
                        model=model_obj,
                        mcmeta=mcmeta_data,
                        content_type=content_type
                    )

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
                "minecraft:block/cross": "cross",
                "block/block": "slab",
                "minecraft:block/template_torch": "flat",
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
                "minecraft:block/snow_height2": "snow",
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
                elif "stair" in model_ref:
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
                elif "coral_block" in model_ref:
                    block_type = "block"
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
                    if "stair" in pref:
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

            # Special-case detection for some known items where 3D geometry differs from default
            # Conduit is best rendered as a small centered cube with a subtle cyan tint
            if "conduit" in model_ref or "conduit" in name_stem:
                block_type = "conduit"

            # Scaffolding is a framed structure and benefits from a dedicated geometry
            if "scaffold" in model_ref or "scaffolding" in model_ref or "scaffold" in name_stem or "scaffolding" in name_stem:
                block_type = "scaffolding"

            # Force 2D for saplings, clusters, and other cross models
            # Also force 2D for complex entities like beds, shulker boxes, banners, boats, rafts, bundles, buckets
            # Note: "raft" matches "minecraft", so use "_raft"
            exclusion_keywords = ["sapling", "cluster", "cross", "plant", "coral", "weed", "grass", "fern", "flower", "fungus", "roots", "sprouts", "bamboo", "cane", "kelp", "vine", "bars", "chain", "ladder", "rail", "bed", "shulker", "banner", "boat", "_raft", "shield", "trident", "bundle", "bucket"]

            matched_keyword = None
            for keyword in exclusion_keywords:
                if keyword in model_ref or keyword in name_stem:
                    matched_keyword = keyword
                    break

            if matched_keyword:
                 # Exception: bamboo_planks, bamboo_mosaic, bamboo_block are blocks.
                 # The check "bamboo" in model_ref is too aggressive.
                 # We should only exclude "bamboo" if it's the plant, not the wood.
                 # "bamboo_stalk" or just "bamboo" (the item).
                 # But "bamboo_planks" contains "bamboo".

                 # Refined check:
                 is_blocky_bamboo = "planks" in model_ref or "mosaic" in model_ref or "bamboo_block" in model_ref or "stripped" in model_ref or "slab" in model_ref or "stair" in model_ref or "fence" in model_ref or "door" in model_ref or "trapdoor" in model_ref or "button" in model_ref or "pressure_plate" in model_ref

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
                # If we have no textures but we have a model_ref, try to find a direct block texture
                # as a last resort before giving up on 3D.
                direct_block_tex = f"assets/{namespace}/textures/block/{name_stem}.png"
                if direct_block_tex not in file_list:
                    direct_block_tex = f"assets/{namespace}/textures/blocks/{name_stem}.png"

                if direct_block_tex in file_list:
                    with zip_ref.open(direct_block_tex) as pf:
                        img_bytes = pf.read()
                    return {"up": img_bytes, "left": img_bytes, "right": img_bytes}, block_type

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
                # Prefer layer0 as the 'all' texture regardless of whether it references 'block/'
                # so that item/generated models that only define layer0 can still be rendered
                # as simple block textures (this allows the block fallback path to prefer a
                # larger block-level PNG if present).
                textures["all"] = textures["layer0"]

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
                # If the resolved textures are small (16) but there exists a block texture
                # with a larger size (e.g., 32 or 64), prefer the block texture so that
                # the rendered final asset can use the highest true resolution available.
                try:
                    import io as _io
                    from PIL import Image as _Image

                    up_img = _Image.open(_io.BytesIO(up_bytes))
                    left_img = _Image.open(_io.BytesIO(left_bytes))
                    right_img = _Image.open(_io.BytesIO(right_bytes))

                    current_max = max(up_img.width, up_img.height, left_img.width, left_img.height, right_img.width, right_img.height)
                except Exception:
                    current_max = 0

                # Check for a block-level single texture that may be higher resolution
                # Check both 'block/' and 'blocks/' (older mods)
                # Also try stripping 'block_' prefix
                candidates = [
                    f"assets/{namespace}/textures/block/{name_stem}.png",
                    f"assets/{namespace}/textures/blocks/{name_stem}.png",
                ]
                if name_stem.startswith("block_"):
                    stripped = name_stem[6:]
                    candidates.append(f"assets/{namespace}/textures/block/{stripped}.png")
                    candidates.append(f"assets/{namespace}/textures/blocks/{stripped}.png")

                for bp in candidates:
                    if bp in file_list:
                        try:
                            with zip_ref.open(bp) as bf:
                                block_bytes = bf.read()
                            block_img = _Image.open(_io.BytesIO(block_bytes))
                            block_max = max(block_img.width, block_img.height)
                            if block_max > current_max:
                                return {"up": block_bytes, "left": block_bytes, "right": block_bytes}, block_type
                        except Exception:
                            # On any error, fall back to the resolved textures
                            pass

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

            # Handle NeoForge fluid container
            if model_data.get("loader") == "neoforge:fluid_container":
                fluid_ref = model_data.get("fluid")
                if fluid_ref:
                    if ":" in fluid_ref:
                        f_ns, f_path = fluid_ref.split(":", 1)
                    else:
                        f_ns = ns
                        f_path = fluid_ref

                    # Try common fluid texture paths
                    # Strip 'molten_' prefix if present for texture matching
                    base_path = f_path.replace("molten_", "")

                    possible_tex_paths = [
                        f"block/fluid/{f_path}_still",
                        f"block/{f_path}_still",
                        f"block/fluid/{f_path}",
                        f"block/{f_path}",
                        f"block/fluid/{base_path}_still",
                        f"block/{base_path}_still",
                        f"block/fluid/{base_path}",
                        f"block/{base_path}",
                    ]

                    for p in possible_tex_paths:
                        full_path = f"assets/{f_ns}/textures/{p}.png"
                        if full_path in file_list:
                            return {"layer0": f"{f_ns}:{p}"}

                    # Fallback to just the fluid path
                    return {"layer0": f"{f_ns}:block/{f_path}"}

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

        # Try standard model path first
        model_path = f"assets/{ns}/models/{path}.json"

        # If not found, try item/ and block/ subdirectories if path doesn't already have them
        if model_path not in file_list:
             if "item/" not in path and "block/" not in path:
                 candidates = [
                     f"assets/{ns}/models/item/{path}.json",
                     f"assets/{ns}/models/block/{path}.json"
                 ]
                 for c in candidates:
                     if c in file_list:
                         model_path = c
                         break

        if model_path in file_list:
            chain.append(model_ref)
            try:
                with zip_ref.open(model_path) as f:
                    model_data = json.load(f)
                parent = model_data.get("parent")
                if parent:
                    chain.extend(self._get_model_parent_chain(zip_ref, file_list, parent, ns, depth + 1))
            except Exception:
                pass

        return chain
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
        for p in [f"assets/{namespace}/textures/item/{name_stem}.png", f"assets/{namespace}/textures/items/{name_stem}.png"]:
            if p in file_list:
                return p

        # Special case for banners
        if "banner" in name_stem:
            # Banners use a base texture that is tinted
            banner_tex = "assets/minecraft/textures/entity/banner/base.png"
            if banner_tex in file_list:
                return banner_tex

            # Fallback to color-specific texture if it exists
            color = name_stem.replace("_banner", "")
            banner_tex = f"assets/{namespace}/textures/entity/banner/{color}.png"
            if banner_tex in file_list:
                return banner_tex
            # Fallback to minecraft namespace for banners
            banner_tex_mc = f"assets/minecraft/textures/entity/banner/{color}.png"
            if banner_tex_mc in file_list:
                return banner_tex_mc

        # Try block texture
        for p in [f"assets/{namespace}/textures/block/{name_stem}.png", f"assets/{namespace}/textures/blocks/{name_stem}.png"]:
            if p in file_list:
                return p

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

    def extract_model_asset(self, zip_ref: ZipFile, file_list: set, namespace: str, name_stem: str, item_def_path: str) -> Optional[tuple]:
        """
        Attempt to locate and load the model JSON associated with an item (without writing it to disk).
        Returns a tuple (relative_path, model_json) on success.
        """
        # Prefer new format item definitions
        if "/items/" in item_def_path:
            try:
                with zip_ref.open(item_def_path) as f:
                    item_data = json.load(f)
                model_ref = item_data.get("model", {}).get("model", "")
                if not model_ref:
                    return None

                if ":" in model_ref:
                    model_ns, model_path = model_ref.split(":", 1)
                else:
                    model_ns = namespace
                    model_path = model_ref

                model_file_in_jar = f"assets/{model_ns}/models/{model_path}.json"
                if model_file_in_jar in file_list:
                    with zip_ref.open(model_file_in_jar) as mf:
                        model_json = json.load(mf)

                    # Return a path relative to the assets root and the model JSON (do not write to disk)
                    return f"assets/{model_ns}/models/{model_path}.json", model_json
            except Exception:
                return None

        # Old format: model file is likely the item_def_path itself under models/item/
        if "/models/item/" in item_def_path and item_def_path in file_list:
            try:
                with zip_ref.open(item_def_path) as mf:
                    model_json = json.load(mf)

                # Derive relative path for metadata but do not write to disk
                return f"assets/{namespace}/models/item/{name_stem}.json", model_json
            except Exception:
                return None

        # Fallback: try block model
        # Some items (like enchanting_table) use a block model directly or via a simple item model wrapper
        # If we haven't found a model yet, check if there is a block model with the same name
        model_file = f"assets/{namespace}/models/block/{name_stem}.json"
        if model_file in file_list:
            try:
                with zip_ref.open(model_file) as mf:
                    model_json = json.load(mf)
                return f"assets/{namespace}/models/block/{name_stem}.json", model_json
            except Exception:
                pass

        # Fallback: try item model if we started with a block definition or something else
        # This handles cases where we might be looking at a block but want the item model
        model_file = f"assets/{namespace}/models/item/{name_stem}.json"
        if model_file in file_list:
            try:
                with zip_ref.open(model_file) as mf:
                    model_json = json.load(mf)
                return f"assets/{namespace}/models/item/{name_stem}.json", model_json
            except Exception:
                pass

        return None

    def _find_texture_from_new_format(self, zip_ref: ZipFile, file_list: set, item_data: dict, namespace: str) -> Optional[str]:
        """Parse new format item definitions (1.21+) and find textures."""
        if "model" not in item_data or not isinstance(item_data["model"], dict):
            return None

        model_info = item_data["model"]

        # NeoForge fluid container loader (buckets)
        if model_info.get("loader") == "neoforge:fluid_container":
            fluid_ref = model_info.get("fluid")
            if fluid_ref:
                if ":" in fluid_ref:
                    f_ns, f_path = fluid_ref.split(":", 1)
                else:
                    f_ns = namespace
                    f_path = fluid_ref

                # Try common fluid texture paths
                candidates = [
                    f"assets/{f_ns}/textures/block/{f_path}.png",
                    f"assets/{f_ns}/textures/block/{f_path}_still.png",
                    f"assets/{f_ns}/textures/fluid/{f_path}.png",
                    f"assets/{f_ns}/textures/fluid/{f_path}_still.png",
                    f"assets/{f_ns}/textures/item/{f_path}_bucket.png",
                ]
                for cand in candidates:
                    if cand in file_list:
                        return cand

            # Fallback to standard bucket
            bucket_tex = "assets/minecraft/textures/item/bucket.png"
            if bucket_tex in file_list:
                return bucket_tex

        model_ref = model_info.get("model", "")
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
        # NeoForge fluid container loader (buckets)
        if model_data.get("loader") == "neoforge:fluid_container":
            fluid_ref = model_data.get("fluid")
            if fluid_ref:
                if ":" in fluid_ref:
                    f_ns, f_path = fluid_ref.split(":", 1)
                else:
                    f_ns = namespace
                    f_path = fluid_ref

                # Try common fluid texture paths
                candidates = [
                    f"assets/{f_ns}/textures/block/{f_path}.png",
                    f"assets/{f_ns}/textures/block/{f_path}_still.png",
                    f"assets/{f_ns}/textures/fluid/{f_path}.png",
                    f"assets/{f_ns}/textures/fluid/{f_path}_still.png",
                    f"assets/{f_ns}/textures/item/{f_path}_bucket.png",
                ]
                for cand in candidates:
                    if cand in file_list:
                        return cand

            # Fallback to standard bucket if fluid texture not found
            bucket_tex = "assets/minecraft/textures/item/bucket.png"
            if bucket_tex in file_list:
                return bucket_tex

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

        raw_name = None
        for key in keys_to_try:
            if key in lang_data:
                raw_name = lang_data[key]
                break

        if raw_name:
            if "%" in raw_name:
                return self.format_display_name(raw_name, namespace, name, lang_data)
            return raw_name

        # Fallback: format the name (acacia_boat -> Acacia Boat)
        return name.replace("_", " ").title()

    def format_display_name(self, raw_name: str, namespace: str, name_stem: str, lang_data: Dict[str, str]) -> str:
        """
        Handle dynamic name formatting (e.g. %1$s%2$s%3$s).
        Assumes pattern:
        1. Prefix (gui.<namespace>.prefix)
        2. Base Item Name (resolved from name_stem)
        3. Suffix (gui.<namespace>.suffix)
        """
        try:
            # Check if indexed (Java style %1$s)
            if re.search(r'%\d+\$s', raw_name):
                # Convert to Python format {0}, {1}, {2}
                python_format = re.sub(r'%(\d+)\$s', lambda m: f"{{{int(m.group(1))-1}}}", raw_name)

                prefix = lang_data.get(f"gui.{namespace}.prefix", "")
                suffix = lang_data.get(f"gui.{namespace}.suffix", "")
                base_name = self._resolve_base_name(name_stem, lang_data)

                return python_format.format(prefix, base_name, suffix)

            # Check if simple %s
            elif "%s" in raw_name:
                python_format = raw_name.replace("%s", "{0}")
                base_name = self._resolve_base_name(name_stem, lang_data)
                return python_format.format(base_name)

        except Exception as e:
            logger.debug(f"Failed to format display name '{raw_name}': {e}")

        return raw_name

    def _resolve_base_name(self, name_stem: str, lang_data: Dict[str, str]) -> str:
        """Resolve the display name of the base item (assuming minecraft namespace)."""
        keys = [
            f"block.minecraft.{name_stem}",
            f"item.minecraft.{name_stem}",
            f"entity.minecraft.{name_stem}"
        ]
        for key in keys:
            if key in lang_data:
                return lang_data[key]
        return name_stem.replace("_", " ").title()
