import base64
import io
import os
from pathlib import Path

from PIL import Image

from scripts.minecraft.modules.asset_extractor import AssetExtractor
from scripts.minecraft.modules.constants import ASSETS_DIR


def make_color_png_bytes(size=(16, 16), color=(200, 100, 50, 255)):
    img = Image.new("RGBA", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def cleanup_file(name: str):
    p = ASSETS_DIR / name
    if p.exists():
        try:
            p.unlink()
        except PermissionError:
            # File may be held open by prior process; ignore for test cleanup
            pass


def test_render_3d_block_uses_16_final(tmp_path):
    item_id = "test:small_block"
    filename = AssetExtractor.get_asset_filename(item_id)
    cleanup_file(filename)

    textures = {
        "up": make_color_png_bytes((16, 16), (255, 0, 0, 255)),
        "left": make_color_png_bytes((16, 16), (0, 255, 0, 255)),
        "right": make_color_png_bytes((16, 16), (0, 0, 255, 255)),
    }

    fn, b64, w, h = AssetExtractor.render_3d_block(item_id, textures, source_jar="test.jar", include_asset=True)
    try:
        assert fn == filename
        assert b64 is not None
        p = ASSETS_DIR / fn
        assert p.exists()
        with Image.open(p) as img:
            assert img.size == (16, 16)
    finally:
        cleanup_file(filename)


def test_render_3d_block_prefers_32_when_supported():
    item_id = "test:big_block"
    filename = AssetExtractor.get_asset_filename(item_id)
    cleanup_file(filename)

    textures = {
        "up": make_color_png_bytes((32, 32), (10, 20, 30, 255)),
        "left": make_color_png_bytes((32, 32), (30, 20, 10, 255)),
        "right": make_color_png_bytes((32, 32), (100, 110, 120, 255)),
    }

    fn, b64, w, h = AssetExtractor.render_3d_block(item_id, textures, source_jar="test.jar", include_asset=True)
    try:
        assert fn == filename
        assert b64 is not None
        p = ASSETS_DIR / fn
        assert p.exists()
        with Image.open(p) as img:
            # Should prefer 32x32 final when textures support >=32
            assert img.size == (32, 32)
    finally:
        cleanup_file(filename)


def test_render_3d_block_prefers_64_when_supported():
    item_id = "test:huge_block"
    filename = AssetExtractor.get_asset_filename(item_id)
    cleanup_file(filename)

    textures = {
        "up": make_color_png_bytes((64, 64), (10, 20, 30, 255)),
        "left": make_color_png_bytes((64, 64), (30, 20, 10, 255)),
        "right": make_color_png_bytes((64, 64), (100, 110, 120, 255)),
    }

    fn, b64, w, h = AssetExtractor.render_3d_block(item_id, textures, source_jar="test.jar", include_asset=True)
    try:
        assert fn == filename
        assert b64 is not None
        p = ASSETS_DIR / fn
        assert p.exists()
        with Image.open(p) as img:
            # Should prefer 64x64 final when textures support >=64
            assert img.size == (64, 64)
    finally:
        cleanup_file(filename)


def test_render_3d_block_stairs_prefers_64_when_supported():
    item_id = "test:huge_stairs"
    filename = AssetExtractor.get_asset_filename(item_id)
    cleanup_file(filename)

    textures = {
        "up": make_color_png_bytes((64, 64), (10, 20, 30, 255)),
        "left": make_color_png_bytes((64, 64), (30, 20, 10, 255)),
        "right": make_color_png_bytes((64, 64), (100, 110, 120, 255)),
    }

    fn, b64, w, h = AssetExtractor.render_3d_block(item_id, textures, source_jar="test.jar", include_asset=True, block_type="stairs")
    try:
        assert fn == filename
        assert b64 is not None
        p = ASSETS_DIR / fn
        assert p.exists()
        with Image.open(p) as img:
            # Stairs should prefer 64x64 final when textures support >=64
            assert img.size == (64, 64)
    finally:
        cleanup_file(filename)


def test_render_3d_block_conduit_default_tint():
    item_id = "minecraft:conduit"
    filename = AssetExtractor.get_asset_filename(item_id)
    cleanup_file(filename)

    # Start with a warm (reddish) up texture so default cyan tint should visibly shift it
    textures = {
        "up": make_color_png_bytes((16, 16), (200, 100, 50, 255)),
        "left": make_color_png_bytes((16, 16), (80, 120, 150, 255)),
        "right": make_color_png_bytes((16, 16), (80, 120, 150, 255)),
    }

    fn, b64, w, h = AssetExtractor.render_3d_block(item_id, textures, source_jar="test.jar", include_asset=True, block_type="conduit")
    try:
        assert fn == filename
        assert b64 is not None
        p = ASSETS_DIR / fn
        assert p.exists()
        with Image.open(p) as img:
            # Textures passed were 16x16; expect 16x16 final output
            assert img.size == (16, 16)
            # Check that the resulting image has a bluish tint applied (blue > red)
            pixels = [px for px in img.getdata() if px[3] > 10]
            avg = tuple(sum(p[i] for p in pixels) / len(pixels) for i in range(3))
            assert avg[2] > avg[0]
    finally:
        cleanup_file(filename)


def test_render_3d_block_scaffolding_geometry():
    item_id = "test:scaffolding"
    filename = AssetExtractor.get_asset_filename(item_id)
    cleanup_file(filename)

    textures = {
        "up": make_color_png_bytes((16, 16), (200, 200, 150, 255)),
        "left": make_color_png_bytes((16, 16), (160, 120, 90, 255)),
        "right": make_color_png_bytes((16, 16), (160, 120, 90, 255)),
    }

    fn, b64, w, h = AssetExtractor.render_3d_block(item_id, textures, source_jar="test.jar", include_asset=True, block_type="scaffolding")
    try:
        assert fn == filename
        assert b64 is not None
        p = ASSETS_DIR / fn
        assert p.exists()
        with Image.open(p) as img:
            # Textures passed were 16x16; expect 16x16 final output
            assert img.size == (16, 16)
    finally:
        cleanup_file(filename)
