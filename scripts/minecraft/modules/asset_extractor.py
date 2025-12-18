import shutil
import base64
import io
from pathlib import Path
from zipfile import ZipFile
from typing import Optional, Tuple, Dict

from PIL import Image
from .constants import ASSETS_DIR
from .logger import logger


class AssetExtractor:
    @staticmethod
    def get_asset_filename(item_id: str) -> str:
        """Converts item ID (e.g., minecraft:acacia_boat) to filename (minecraft_acacia_boat.png)."""
        return item_id.replace(":", "_") + ".png"

    @staticmethod
    def create_placeholder_asset(item_id: str) -> str:
        """Create a visible placeholder PNG for items without an extracted asset and return the filename."""
        filename = AssetExtractor.get_asset_filename(item_id)
        dest = ASSETS_DIR / filename
        if dest.exists():
            return filename
        try:
            img = Image.new("RGBA", (32, 32), (255, 0, 255, 255))
            img.save(dest)
            return filename
        except Exception as e:
            logger.error(f"Failed to create placeholder asset for {item_id}: {e}")
            return filename

    @staticmethod
    def extract_asset(zip_file: ZipFile, zip_path: str, item_id: str, source_jar: str, include_asset: bool = False, tint: Optional[Tuple[int, int, int]] = None, overwrite: bool = False) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[int]]:
        """
        Extracts the asset from the zip file to the assets directory.
        If include_asset is True, also returns a base64-encoded string of the image data.
        Returns (filename, asset_b64, width, height) where values can be None on failure.
        """
        filename = AssetExtractor.get_asset_filename(item_id)
        destination_path = ASSETS_DIR / filename

        if destination_path.exists() and not overwrite:
            # If we need the base64 but it's not being returned because we're skipping,
            # we should still return the filename and base64 if requested.
            asset_b64 = None
            width, height = None, None
            if include_asset:
                try:
                    with open(destination_path, "rb") as f:
                        data = f.read()
                        asset_b64 = base64.b64encode(data).decode("ascii")
                        with Image.open(io.BytesIO(data)) as img:
                            width, height = img.size
                except Exception:
                    pass
            return filename, asset_b64, width, height

        try:
            with zip_file.open(zip_path) as source:
                data = source.read()

            # Load image to check size and apply tint if needed
            try:
                img = Image.open(io.BytesIO(data)).convert("RGBA")

                if tint:
                    r, g, b, a = img.split()
                    r = r.point(lambda p: int(p * tint[0] / 255))
                    g = g.point(lambda p: int(p * tint[1] / 255))
                    b = b.point(lambda p: int(p * tint[2] / 255))
                    img = Image.merge('RGBA', (r, g, b, a))

                    # Save tinted image back to bytes for writing
                    buffered = io.BytesIO()
                    img.save(buffered, format="PNG")
                    data = buffered.getvalue()

                width, height = img.size
            except Exception:
                width = None
                height = None

            # Save file to disk
            with open(destination_path, "wb") as target:
                target.write(data)

            asset_b64 = None
            if include_asset:
                asset_b64 = base64.b64encode(data).decode("ascii")

            return filename, asset_b64, width, height
        except Exception as e:
            logger.error(f"Failed to extract asset {zip_path} from {source_jar}: {e}")
            return None, None, None, None

    @staticmethod
    def render_3d_block(item_id: str, textures: Dict[str, bytes], source_jar: str, include_asset: bool = False, block_type: str = "block", tint: Optional[Tuple[int, int, int]] = None, overwrite: bool = False) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[int]]:
        """
        Renders a 3D isometric block from provided face textures.
        textures: Dict mapping face name ('up', 'left', 'right') to raw bytes.
        block_type: 'block', 'slab', 'stairs', 'wall', 'fence', 'fence_gate', 'cross'
        tint: Optional (r, g, b) tuple to tint the 'up' and 'overlay' textures (for grass).
        """
        filename = AssetExtractor.get_asset_filename(item_id)
        destination_path = ASSETS_DIR / filename

        if destination_path.exists() and not overwrite:
            # If we need the base64 but it's not being returned because we're skipping,
            # we should still return the filename and base64 if requested.
            asset_b64 = None
            width, height = None, None
            if include_asset:
                try:
                    with open(destination_path, "rb") as f:
                        data = f.read()
                        asset_b64 = base64.b64encode(data).decode("ascii")
                        with Image.open(io.BytesIO(data)) as img:
                            width, height = img.size
                except Exception:
                    pass
            return filename, asset_b64, width, height

        try:
            # Load textures (don't immediately force a fixed size)
            # For 'cross' type, we expect a single texture, usually passed as 'all' or 'cross' or just use the first one found
            if block_type in ["cross"]:
                # Use the first available texture
                tex_data = next(iter(textures.values()))
                raw_tex = Image.open(io.BytesIO(tex_data)).convert("RGBA")
                raw_up = raw_tex # Not used but keeps variables defined
                raw_left = raw_tex
                raw_right = raw_tex
            elif block_type in ["sprite_flat"]:
                # find the first texture in the sprite and use that as a 2d flat image
                # need to get the image, get the size. if the width > height, scale width to 32, else scale height to 32
                # then use that as the image
                tex_data = next(iter(textures.values()))
                raw_tex = Image.open(io.BytesIO(tex_data)).convert("RGBA")
                # Determine scaling
                w, h = raw_tex.size
                if w >= h:
                    new_w = 32
                    new_h = int(h * (32 / w))
                else:
                    new_h = 32
                    new_w = int(w * (32 / h))
                img = raw_tex.resize((new_w, new_h), resample=Image.LANCZOS)
                canvas = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
                offset_x = (32 - new_w) // 2
                offset_y = (32 - new_h) // 2
                canvas.paste(img, (offset_x, offset_y))
                raw_tex = canvas
                raw_up = raw_tex
                raw_left = raw_tex
                raw_right = raw_tex
            elif block_type == "mob_head":
                # Initialize with dummy images, will be overwritten later
                dummy = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
                raw_up = dummy
                raw_left = dummy
                raw_right = dummy
            else:
                raw_up = Image.open(io.BytesIO(textures['up'])).convert("RGBA")
                raw_left = Image.open(io.BytesIO(textures['left'])).convert("RGBA")
                raw_right = Image.open(io.BytesIO(textures['right'])).convert("RGBA")

            # Apply tint if provided
            if tint:
                # Helper to apply tint
                def apply_tint(img, color):
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    r, g, b, a = img.split()
                    # Multiply
                    r = r.point(lambda p: int(p * color[0] / 255))
                    g = g.point(lambda p: int(p * color[1] / 255))
                    b = b.point(lambda p: int(p * color[2] / 255))
                    return Image.merge('RGBA', (r, g, b, a))

                # Apply to UP face (grass top)
                if 'up' in textures: # Only if we actually loaded it
                     raw_up = apply_tint(raw_up, tint)

                # For grass block, side overlay might need tinting too, but we usually just get 'left'/'right' which are pre-composed or just side.
                # If the side texture is actually an overlay, we should tint it.
                # But usually 'grass_block_side' is the dirt+grass combo or just dirt.
                # If we are rendering a grass block, 'up' is the main one to tint.
                # If we have 'overlay' in textures, we might need to handle it, but find_block_textures usually resolves to up/left/right.
                # Let's assume for now only 'up' needs tinting for standard grass block top view.
                # Wait, in isometric view, we see Top, Left (South), Right (East).
                # Grass block top is tinted.
                # Grass block side has an overlay that is tinted.
                # If our texture extractor just grabbed 'grass_block_side.png', it's the dirt part.
                # The overlay is 'grass_block_side_overlay.png'.
                # If we want perfect grass, we need to compose them.
                # For now, let's just tint the Top face, as that's the most obvious one.
                pass

            # Decide output final size: always use 32x32 for 3D blocks to ensure quality
            # If textures are larger than 16px, we could potentially go larger, but 32x32 is standard for isometric view of 16x16 blocks.
            # The user requested "largest possible scale" and "32x32 where possible".
            # So we default to 32.
            final_size = 32

            logger.debug(f"Rendering 3D block for {item_id}: final_size={final_size}")

            # Our internal renderer expects 16x16 face tiles and produces a 32x32 canvas.
            # So normalize textures to 16x16 for the drawing step.
            img_up = raw_up.resize((16, 16), resample=Image.LANCZOS)
            img_left = raw_left.resize((16, 16), resample=Image.LANCZOS)
            img_right = raw_right.resize((16, 16), resample=Image.LANCZOS)

            # Apply shading
            def apply_shading(img, factor):
                if img.mode == 'RGBA':
                    r, g, b, a = img.split()
                    r = r.point(lambda p: int(p * factor))
                    g = g.point(lambda p: int(p * factor))
                    b = b.point(lambda p: int(p * factor))
                    return Image.merge('RGBA', (r, g, b, a))
                else:
                    return img.point(lambda p: int(p * factor))

            img_left = apply_shading(img_left, 0.8)
            img_right = apply_shading(img_right, 0.6)

            canvas = Image.new("RGBA", (32, 32), (0, 0, 0, 0))

            def draw_cuboid(e_off, s_off, u_off, w, d, h):
                # e_off, s_off, u_off: Origin (East, South, Up)
                # w, d, h: Dimensions (East, South, Up)

                # Top Face (at u_off + h)
                # Texture: x=East, y=South
                y_shift = 16 - (u_off + h)
                for s in range(s_off, s_off + d):
                    for e in range(e_off, e_off + w):
                        # Texture coords
                        tex_x = e
                        tex_y = s
                        # Screen coords
                        tx = 16 + e - s
                        ty = (e + s) // 2 + y_shift
                        if 0 <= tx < 32 and 0 <= ty < 32:
                            p = img_up.getpixel((tex_x, tex_y))
                            if p[3] > 0:
                                canvas.putpixel((tx, ty), p)

                # Left Face (South Face, at s_off + d)
                # Texture: x=East, y=Down (inverted Up)
                # Shift for South position
                south_shift = 16 - (s_off + d)
                tx_shift = south_shift
                ty_shift = -south_shift // 2

                for u in range(u_off, u_off + h):
                    for e in range(e_off, e_off + w):
                        # Texture coords
                        tex_x = e
                        tex_y = 15 - u

                        # Screen coords (Standard Left Face)
                        tx_base = e
                        ty_base = 8 + tex_y + e // 2

                        tx = tx_base + tx_shift
                        ty = ty_base + ty_shift

                        if 0 <= tx < 32 and 0 <= ty < 32:
                            p = img_left.getpixel((tex_x, tex_y))
                            if p[3] > 0:
                                canvas.putpixel((tx, ty), p)

                # Right Face (East Face, at e_off + w)
                # Texture: x=Inv South, y=Down
                # Shift for East position
                east_shift = 16 - (e_off + w)
                tx_shift = -east_shift
                ty_shift = -east_shift // 2

                for u in range(u_off, u_off + h):
                    for s in range(s_off, s_off + d):
                        # Texture coords
                        tex_x = 15 - s
                        tex_y = 15 - u

                        # Screen coords (Standard Right Face)
                        tx_base = 16 + tex_x
                        ty_base = 8 + tex_y + (15 - tex_x) // 2

                        tx = tx_base + tx_shift
                        ty = ty_base + ty_shift

                        if 0 <= tx < 32 and 0 <= ty < 32:
                            p = img_right.getpixel((tex_x, tex_y))
                            if p[3] > 0:
                                canvas.putpixel((tx, ty), p)

            # Render based on type
            if block_type == "block":
                draw_cuboid(0, 0, 0, 16, 16, 16)
            elif block_type == "slab":
                draw_cuboid(0, 0, 0, 16, 16, 8)
            elif block_type == "stairs":
                # Bottom Slab
                draw_cuboid(0, 0, 0, 16, 16, 8)
                # Top Step (Back/North half - South=0..8)
                draw_cuboid(0, 0, 8, 16, 8, 8)
            elif block_type == "fence":
                # Two posts connected by bars
                # Improved Fence Geometry
                # Post 1: x=6..10, z=6..10 (Centered) - No, inventory is two posts.
                # Vanilla inventory: Two posts at x=4 and x=12 (approx), connected by rails.
                # Post 1: x=2..6, z=6..10
                draw_cuboid(2, 6, 0, 4, 4, 16)
                # Post 2: x=10..14, z=6..10
                draw_cuboid(10, 6, 0, 4, 4, 16)
                # Top Bar: x=6..10, z=7..9, y=12..14
                draw_cuboid(6, 7, 12, 4, 2, 3)
                # Bottom Bar: x=6..10, z=7..9, y=6..9
                draw_cuboid(6, 7, 6, 4, 2, 3)
                # Wait, the previous code was exactly this.
                # Maybe the user wants the posts to be thicker or spaced differently?
                # Let's try to match the vanilla icon more closely.
                # Vanilla icon posts look like they are at x=5 and x=11?
                # Let's try:
                # Post 1: x=3..7
                # Post 2: x=9..13
                # Bar: x=7..9
                # This is tighter.
                # Let's stick to the previous one but maybe check the bar height.
                # Top bar y=12..15 (3 high)
                # Bottom bar y=6..9 (3 high)
                # This seems fine.
                # Maybe the issue is the texture mapping?
                # Fence uses "texture" which maps to "all".
                # So posts and bars get the same texture.
                # This is correct for wood fences.
                pass # Keep existing for now, maybe tweak later if specific feedback.

            elif block_type == "cross":
                # Render two intersecting planes at 45 degrees (which aligns them with X and Z axes in iso view)
                # Plane 2 (Z-aligned, East Face)
                # X=8, Z=0..16
                for u in range(16): # Height
                    for s in range(16): # South/Z
                        # Texture coords: x=15-s (inverted for Right face logic), y=15-u
                        tex_x = 15 - s
                        tex_y = 15 - u

                        x = 8
                        z = s
                        y = u

                        tx = 16 + x - z
                        ty = (x + z) // 2 + (16 - y)

                        if 0 <= tx < 32 and 0 <= ty < 32:
                            p = img_right.getpixel((tex_x, tex_y))
                            if p[3] > 0:
                                canvas.putpixel((tx, ty), p)

                # Plane 1 (X-aligned, South Face)
                # Z=8, X=0..16
                for u in range(16): # Height
                    for e in range(16): # East/X
                        # Texture coords: x=e, y=15-u
                        tex_x = e
                        tex_y = 15 - u

                        x = e
                        z = 8
                        y = u

                        tx = 16 + x - z
                        ty = (x + z) // 2 + (16 - y)

                        if 0 <= tx < 32 and 0 <= ty < 32:
                            p = img_left.getpixel((tex_x, tex_y))
                            if p[3] > 0:
                                canvas.putpixel((tx, ty), p)

            elif block_type == "fence_gate":
                # Improved Fence Gate
                # Standard icon: Closed gate.
                # Two posts (thinner?) and a central plank.
                # Post 1: x=6..8, z=7..9, y=5..15?
                # Actually, fence gate inventory is usually just the gate part, no posts?
                # No, it has the side posts.
                # Let's try:
                # Post 1: x=2..6, z=7..9
                draw_cuboid(2, 7, 4, 4, 2, 12)
                # Post 2: x=10..14, z=7..9
                draw_cuboid(10, 7, 4, 4, 2, 12)
                # Bar: x=6..10, z=7..9, y=12..14
                draw_cuboid(6, 7, 12, 4, 2, 3)
                # Bar: x=6..10, z=7..9, y=6..9
                draw_cuboid(6, 7, 6, 4, 2, 3)
                # Central Plank?
                # Usually fence gate has a central vertical piece?
                # Let's just draw the horizontal bars connecting the posts.

            elif block_type == "wall":
                # Two posts
                # Post 1: x=4..8, z=4..12
                draw_cuboid(4, 4, 0, 4, 8, 16)
                # Post 2: x=12..16, z=4..12
                # Wait, walls are usually thick posts.
                # Let's do a single thick post for wall? No, inventory is usually two.
                # Let's do:
                # Post 1: x=2..6, z=5..11
                draw_cuboid(2, 5, 0, 4, 6, 16)
                # Post 2: x=10..14, z=5..11
                draw_cuboid(10, 5, 0, 4, 6, 16)
                # Wall segment: x=6..10, z=6..10, y=0..14
                draw_cuboid(6, 6, 0, 4, 4, 14)
            elif block_type == "teleport_pad":
                # Teleport Pad (AllTheModium)
                # Slab-like, height 3
                draw_cuboid(0, 0, 0, 16, 16, 3)
            elif block_type == "trapdoor":
                # Flat block against side or bottom. Inventory is usually flat.
                draw_cuboid(0, 0, 0, 16, 16, 3)
            elif block_type == "pressure_plate":
                # Very thin slab
                draw_cuboid(1, 1, 0, 14, 14, 1)
            elif block_type == "button":
                # Small block
                draw_cuboid(5, 6, 6, 6, 4, 4)
            elif block_type == "carpet":
                # Thin layer
                draw_cuboid(0, 0, 0, 16, 16, 1)
            elif block_type == "pad":
                # Flat layer at the bottom, sides/top transparent
                draw_cuboid(0, 0, 0, 16, 16, 0)
            elif block_type == "sprite_flat":
                # Flat layer at the bottom, sides/top transparent
                # draw like 2d flat
                draw_cuboid(0, 0, 0, 16, 16, 0)
                # draw_cuboid(0, 7, 0, 16, 2, 16)?
            elif block_type == "snow":
                # Snow layer (height 2)
                draw_cuboid(0, 0, 0, 16, 16, 2)
            elif block_type == "pane":
                # Glass pane - cross or flat? Inventory is usually flat face.
                # Let's draw a thin sheet
                draw_cuboid(0, 7, 0, 16, 2, 16)
            elif block_type == "daylight_detector":
                # Slab-like
                draw_cuboid(0, 0, 0, 16, 16, 6)
            elif block_type == "hopper":
                # Funnel shape
                # Top rim (simplified as solid for now)
                draw_cuboid(0, 0, 10, 16, 16, 6)
                # Bottom spout
                draw_cuboid(6, 6, 0, 4, 4, 10)
            elif block_type == "cauldron":
                # Standard block size for now
                draw_cuboid(0, 0, 0, 16, 16, 16)
            elif block_type == "anvil":
                # Anvil Geometry
                # Base: x=2..14, z=2..14, y=0..4
                # Top/Bottom texture?
                # Let's assume standard orientation
                # Base (North-South): x=4..12, z=0..16, y=0..4?
                # Anvil base is wide on X or Z?
                # Base: 12x12?
                draw_cuboid(2, 2, 0, 12, 12, 4)
                # Neck: x=6..10, z=5..11, y=4..5
                draw_cuboid(6, 5, 4, 4, 6, 1)
                # Neck narrow: x=7..9, z=6..10, y=5..10
                draw_cuboid(7, 6, 5, 2, 4, 5)
                # Top: x=0..16, z=3..13, y=10..16
                draw_cuboid(0, 3, 10, 16, 10, 6)
            elif block_type == "chest":
                # Chest is 14x14x14 centered (simplified)
                draw_cuboid(1, 1, 0, 14, 14, 14)
            elif block_type == "lantern":
                # Lantern: x=5..11, z=5..11, y=0..7 + top
                draw_cuboid(5, 5, 0, 6, 6, 7)
                draw_cuboid(6, 6, 7, 4, 4, 2)
            elif block_type == "beacon":
                # Beacon: Inner glass + obsidian base
                # Base
                draw_cuboid(0, 0, 0, 16, 16, 3)
                # Glass
                draw_cuboid(2, 2, 3, 12, 12, 13)
            elif block_type == "dragon_egg":
                # Dragon Egg Geometry (7 layers)
                # Layer 7 (Bottom): 12x12, height 2
                draw_cuboid(2, 2, 0, 12, 12, 2)
                # Layer 6: 14x14, height 2
                draw_cuboid(1, 1, 2, 14, 14, 2)
                # Layer 5 (Middle/Widest): 16x16, height 3
                draw_cuboid(0, 0, 4, 16, 16, 3)
                # Layer 4: 14x14, height 3
                draw_cuboid(1, 1, 7, 14, 14, 3)
                # Layer 3: 12x12, height 2
                draw_cuboid(2, 2, 10, 12, 12, 2)
                # Layer 2: 8x8, height 2
                draw_cuboid(4, 4, 12, 8, 8, 2)
                # Layer 1 (Top): 6x6, height 2 (Button-like)
                draw_cuboid(5, 5, 14, 6, 6, 2)
            elif block_type == "mob_head":
                # Mob Head (8x8x8)
                # Expects 'skin' in textures
                if 'skin' in textures:
                    skin_data = textures['skin']
                    skin_img = Image.open(io.BytesIO(skin_data)).convert("RGBA")

                    # Crop faces from standard skin layout
                    # Top: (8, 0, 16, 8)
                    # Front: (8, 8, 16, 16)
                    # Right: (0, 8, 8, 16)

                    face_top = skin_img.crop((8, 0, 16, 8))
                    face_front = skin_img.crop((8, 8, 16, 16))
                    face_right = skin_img.crop((0, 8, 8, 16))

                    # Create 16x16 canvas for each face to align with draw_cuboid coordinate system
                    # Top: Centered at (4, 4)
                    new_up = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
                    new_up.paste(face_top, (4, 4))

                    # Left (Front): Centered horizontally (4), Bottom aligned (8) for y=0..8
                    new_left = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
                    new_left.paste(face_front, (4, 8))

                    # Right: Centered horizontally (4), Bottom aligned (8)
                    new_right = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
                    new_right.paste(face_right, (4, 8))

                    # Update images used by draw_cuboid
                    img_up = new_up
                    img_left = apply_shading(new_left, 0.8)
                    img_right = apply_shading(new_right, 0.6)

                    draw_cuboid(4, 4, 0, 8, 8, 8)
                else:
                    draw_cuboid(4, 4, 0, 8, 8, 8)
            elif block_type == "pad":
                # Pad: Draw only a thin top-facing plane (no sides/top transparency)
                # We draw the top face for a cuboid of height=1 (thin plane)
                y_shift = 16 - (0 + 1)
                for s in range(0, 1):
                    for e in range(0, 16):
                        tex_x = e
                        tex_y = s
                        tx = 16 + e - s
                        ty = (e + s) // 2 + y_shift
                        if 0 <= tx < 32 and 0 <= ty < 32:
                            p = img_up.getpixel((tex_x, tex_y))
                            if p[3] > 0:
                                canvas.putpixel((tx, ty), p)

            # If desired final size is 16x16, downscale the rendered canvas
            if final_size == 16:
                final_canvas = canvas.resize((16, 16), resample=Image.LANCZOS)
            else:
                final_canvas = canvas

            # Save to disk
            final_canvas.save(destination_path)

            asset_b64 = None
            if include_asset:
                buffered = io.BytesIO()
                final_canvas.save(buffered, format="PNG")
                asset_b64 = base64.b64encode(buffered.getvalue()).decode("ascii")

            width, height = final_canvas.size

            return filename, asset_b64, width, height

        except Exception as e:
            logger.error(f"Failed to render 3D block for {item_id}: {e}")
            return None, None, None, None
