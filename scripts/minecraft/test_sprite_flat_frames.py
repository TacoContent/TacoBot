import io
import base64
from PIL import Image
from pathlib import Path

from modules.asset_extractor import AssetExtractor


def make_sprite_bytes(frame_colors, frame_size=(16, 16), horizontal=True):
    # frame_colors: list of RGBA tuples
    frames = []
    for color in frame_colors:
        img = Image.new("RGBA", frame_size, color)
        frames.append(img)
    if horizontal:
        total_w = frame_size[0] * len(frames)
        total_h = frame_size[1]
        sprite = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
        x = 0
        for f in frames:
            sprite.paste(f, (x, 0))
            x += frame_size[0]
    else:
        total_w = frame_size[0]
        total_h = frame_size[1] * len(frames)
        sprite = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
        y = 0
        for f in frames:
            sprite.paste(f, (0, y))
            y += frame_size[1]

    buf = io.BytesIO()
    sprite.save(buf, format="PNG")
    return buf.getvalue()


def test_sprite_flat_first_frame_horizontal():
    # Create a horizontal sprite with two frames: red then blue
    sprite_bytes = make_sprite_bytes([(255, 0, 0, 255), (0, 0, 255, 255)], frame_size=(16, 16), horizontal=True)

    # Call render_3d_block directly
    filename, asset_b64, w, h = AssetExtractor.render_3d_block("test:horizontal_sprite", {"all": sprite_bytes}, "test.jar", include_asset=True, block_type="sprite_flat", overwrite=True)

    assert filename is not None
    assert asset_b64 is not None
    img_data = base64.b64decode(asset_b64)
    img = Image.open(io.BytesIO(img_data)).convert("RGBA")

    # Check center pixel — should come from the FIRST (red) frame
    px = img.getpixel((16, 16))
    # Allow for some shading/processing, but expect red to dominate
    assert px[0] > 200 and px[1] < 100 and px[2] < 100

    # Also check bottom center pixel to ensure the frame is bottom-aligned
    bottom_px = img.getpixel((16, 31))
    assert bottom_px[0] > 200 and bottom_px[1] < 100 and bottom_px[2] < 100


def test_sprite_flat_first_frame_vertical():
    # Create a vertical sprite with two frames: green then magenta
    sprite_bytes = make_sprite_bytes([(0, 255, 0, 255), (255, 0, 255, 255)], frame_size=(16, 16), horizontal=False)

    filename, asset_b64, w, h = AssetExtractor.render_3d_block("test:vertical_sprite", {"all": sprite_bytes}, "test.jar", include_asset=True, block_type="sprite_flat", overwrite=True)

    assert filename is not None
    assert asset_b64 is not None
    img_data = base64.b64decode(asset_b64)
    img = Image.open(io.BytesIO(img_data)).convert("RGBA")

    px = img.getpixel((16, 16))
    assert px[1] > 200 and px[0] < 100 and px[2] < 100

    # Also ensure bottom-center is green (bottom alignment)
    bottom_px = img.getpixel((16, 31))
    assert bottom_px[1] > 200 and bottom_px[0] < 100 and bottom_px[2] < 100


def test_sprite_flat_single_narrow_frame():
    # Create a single narrow tall frame (16x32) with green (bottom area)
    frame = Image.new("RGBA", (16, 32), (0, 0, 0, 0))
    # Draw green rectangle at bottom half
    for y in range(16, 32):
        for x in range(0, 16):
            frame.putpixel((x, y), (0, 255, 0, 255))
    buf = io.BytesIO()
    frame.save(buf, format="PNG")
    sprite_bytes = buf.getvalue()

    filename, asset_b64, w, h = AssetExtractor.render_3d_block("test:single_narrow", {"all": sprite_bytes}, "test.jar", include_asset=True, block_type="sprite_flat", overwrite=True)

    assert filename is not None
    assert asset_b64 is not None
    img_data = base64.b64decode(asset_b64)
    img = Image.open(io.BytesIO(img_data)).convert("RGBA")

    # Center pixel may be top of the visible sprite; bottom-center must be green
    bottom_px = img.getpixel((16, 31))
    assert bottom_px[1] > 200 and bottom_px[0] < 100 and bottom_px[2] < 100

    # The top-center should be transparent or not predominantly green
    top_px = img.getpixel((16, 0))
    assert top_px[1] < 200


if __name__ == "__main__":
    test_sprite_flat_first_frame_horizontal()
    print("Horizontal frame test passed")
    test_sprite_flat_first_frame_vertical()
    print("Vertical frame test passed")
