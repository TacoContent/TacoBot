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

    @staticmethod
    def render_3d_block(item_id: str, textures: Dict[str, bytes], source_jar: str, include_asset: bool = False, block_type: str = "block") -> Tuple[Optional[str], Optional[str]]:
        """
        Renders a 3D isometric block from provided face textures.
        textures: Dict mapping face name ('up', 'left', 'right') to raw bytes.
        block_type: 'block', 'slab', 'stairs'
        """
        filename = AssetExtractor.get_asset_filename(item_id)
        destination_path = ASSETS_DIR / filename

        if destination_path.exists():
            logger.warning(f"Duplicate item asset found for ID: {item_id}. Target: {filename}. Source: {source_jar}. Skipping.")
            return None, None

        try:
            # Load textures
            img_up = Image.open(io.BytesIO(textures['up'])).convert("RGBA").resize((16, 16))
            img_left = Image.open(io.BytesIO(textures['left'])).convert("RGBA").resize((16, 16))
            img_right = Image.open(io.BytesIO(textures['right'])).convert("RGBA").resize((16, 16))

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
            if block_type == "slab":
                draw_cuboid(0, 0, 0, 16, 16, 8)
            elif block_type == "stairs":
                # Bottom Slab
                draw_cuboid(0, 0, 0, 16, 16, 8)
                # Top Step (Back/North half - South=0..8)
                draw_cuboid(0, 0, 8, 16, 8, 8)
            elif block_type == "fence":
                # Two posts connected by bars
                # Left Post (West side)
                draw_cuboid(6, 6, 0, 4, 4, 16)
                # Right Post (East side) - Actually, fence inventory is usually two posts
                # Let's do the standard inventory look: Two posts at x=4 and x=12?
                # Vanilla inventory model:
                # Post 1: x=6, z=6, w=4, d=4 (Centered) - Wait, that's a single post.
                # Inventory usually shows two posts connected.
                # Let's try:
                # Post 1: x=2..6, z=6..10
                draw_cuboid(2, 6, 0, 4, 4, 16)
                # Post 2: x=10..14, z=6..10
                draw_cuboid(10, 6, 0, 4, 4, 16)
                # Top Bar: x=6..10, z=7..9, y=12..14
                draw_cuboid(6, 7, 12, 4, 2, 3)
                # Bottom Bar: x=6..10, z=7..9, y=6..9
                draw_cuboid(6, 7, 6, 4, 2, 3)
            elif block_type == "fence_gate":
                # Central Gate part
                # Post 1
                draw_cuboid(6, 7, 5, 2, 2, 10) # Hinge?
                # Let's just draw a central block for now, fence gates are complex
                # Standard icon is the closed gate.
                # Plank: x=4..12, z=7..9, y=6..15
                draw_cuboid(4, 7, 6, 8, 2, 9)
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
            else:
                draw_cuboid(0, 0, 0, 16, 16, 16)

            # Save to disk
            canvas.save(destination_path)

            asset_b64 = None
            if include_asset:
                buffered = io.BytesIO()
                canvas.save(buffered, format="PNG")
                asset_b64 = base64.b64encode(buffered.getvalue()).decode("ascii")

            return filename, asset_b64

        except Exception as e:
            logger.error(f"Failed to render 3D block for {item_id}: {e}")
            return None, None
