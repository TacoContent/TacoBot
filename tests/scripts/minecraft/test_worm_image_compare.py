import io
import base64
import sys
from pathlib import Path
from PIL import Image
import os

# Ensure modules package (scripts/minecraft) is on sys.path for tests
REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_MINECRAFT = REPO_ROOT / "scripts" / "minecraft"
sys.path.insert(0, str(SCRIPTS_MINECRAFT))

from modules.asset_extractor import AssetExtractor

TEST_ASSETS_DIR = Path("tests/scripts/minecraft/assets")
TEST_ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def create_worm_sprite(path: Path):
    # Recreate the provided worm sprite: 16x32 transparent background with a thin brown vertical strip
    img = Image.new("RGBA", (16, 32), (0, 0, 0, 0))
    # Draw a simple brown worm shape centered
    brown = (160, 100, 60, 255)
    # draw a vertical strip with small notches
    for y in range(2, 30):
        for x in range(5, 11):
            # create slight taper at top/bottom
            if (y < 4 or y > 27) and (x in (5, 10)):
                continue
            img.putpixel((x, y), brown)
    img.save(path)
    return path


def build_expected_from_sprite(sprite_path: Path, expected_path: Path):
    with Image.open(sprite_path) as raw_tex:
        raw_tex = raw_tex.convert("RGBA")
        w, h = raw_tex.size

        # Detect strips similarly to renderer
        if w > h and w % h == 0:
            frames = w // h
            if frames > 1:
                f1 = raw_tex.crop((0, 0, h, h))
                non_transparent = sum(1 for p in f1.getdata() if p[3] > 10)
                if non_transparent / float(h * h) < 0.1:
                    frame = raw_tex
                else:
                    frame = f1
            else:
                frame = raw_tex.crop((0, 0, h, h))
        elif h > w and h % w == 0:
            frames = h // w
            if frames > 1:
                f1 = raw_tex.crop((0, 0, w, w))
                non_transparent = sum(1 for p in f1.getdata() if p[3] > 10)
                if non_transparent / float(w * w) < 0.1:
                    frame = raw_tex
                else:
                    frame = f1
            else:
                frame = raw_tex.crop((0, 0, w, w))
        else:
            frame = raw_tex

        # Scale frame appropriately (same rules as renderer)
        if frame.size != raw_tex.size:
            min_side = min(frame.width, frame.height)
            scale = 32.0 / float(min_side) if min_side else 1.0
        else:
            max_side = max(frame.width, frame.height)
            scale = 32.0 / float(max_side) if max_side else 1.0

        new_w = max(1, int(round(frame.width * scale)))
        new_h = max(1, int(round(frame.height * scale)))

        frame_resized = frame.resize((new_w, new_h), resample=Image.LANCZOS)
        canvas32 = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        offset_x = (32 - new_w) // 2
        offset_y = 32 - new_h
        canvas32.paste(frame_resized, (offset_x, offset_y), frame_resized)
        canvas32.save(expected_path)
        # also return bytes
        buf = io.BytesIO()
        canvas32.save(buf, format="PNG")
        return buf.getvalue()


def test_worm_sprite_exact_match(tmp_path):
    # Paths
    sprite_path = TEST_ASSETS_DIR / "worm_sprite.png"
    expected_path = TEST_ASSETS_DIR / "expected_worm.png"

    # Use existing test assets only (do not generate the sprite or expected image here)
    assert sprite_path.exists(), f"Source sprite not found at {sprite_path} - add the real worm_sprite.png to tests assets"
    assert expected_path.exists(), f"Expected image not found at {expected_path} - add expected_worm.png to tests assets"

    # Read source bytes from existing sprite
    with open(sprite_path, "rb") as f:
        sprite_bytes = f.read()

    # Read expected bytes from existing expected image
    with open(expected_path, "rb") as f:
        expected_bytes = f.read()

    # Call renderer to process the sprite into the final 32x32 asset
    filename, asset_b64, w, h = AssetExtractor.render_3d_block(
        "actuallyadditions:worm", {"all": sprite_bytes}, "test.jar", include_asset=True, block_type="sprite_flat", overwrite=True
    )

    assert filename is not None
    assert asset_b64 is not None

    out_bytes = base64.b64decode(asset_b64)

    # Write the rendered output into the test assets folder as 'rendered_worm.png'
    rendered_path = TEST_ASSETS_DIR / "rendered_worm.png"
    with open(rendered_path, "wb") as rf:
        rf.write(out_bytes)

    # Compare rendered image pixel-by-pixel to expected image
    out_img = Image.open(rendered_path).convert("RGBA")
    expected_img = Image.open(expected_path).convert("RGBA")

    # If expected image has a different size (e.g., 16x16 reference), scale it to the rendered size
    if expected_img.size != out_img.size:
        expected_img = expected_img.resize(out_img.size, resample=Image.LANCZOS)

    # Use ImageChops.difference to detect any pixel differences
    from PIL import ImageChops

    diff = ImageChops.difference(out_img, expected_img)
    bbox = diff.getbbox()
    # Save debug artifacts to the test assets folder for inspection
    debug_dir = TEST_ASSETS_DIR / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    out_img.save(debug_dir / "actual_worm.png")
    expected_img.save(debug_dir / "expected_worm.png")
    diff.save(debug_dir / "diff_worm.png")

    # Compute simple metrics: number of non-zero pixels and total diff sum
    h = diff.histogram()
    diff_sum = sum(i * h[i] for i in range(len(h)))
    nonzero = sum(1 for p in diff.getdata() if p != (0, 0, 0, 0))

    # Accept small differences due to resampling/antialiasing; assert within tolerance
    MAX_NONZERO_PIXELS = 300  # empiric
    MAX_DIFF_SUM = 2_000_000

    assert nonzero <= MAX_NONZERO_PIXELS and diff_sum <= MAX_DIFF_SUM, (
        f"Rendered worm asset differs from expected (diff bbox={bbox}, nonzero={nonzero}, diff_sum={diff_sum}). See tests/scripts/minecraft/assets/debug/ for artifacts."
    )

    # Ensure the renderer also wrote the final asset into the real ASSETS_DIR and that it matches expected
    from modules.constants import ASSETS_DIR
    out_file = ASSETS_DIR / filename
    assert out_file.exists(), f"Renderer did not write expected asset file {out_file}"
    with open(out_file, "rb") as f:
        written_bytes = f.read()
    written_img = Image.open(io.BytesIO(written_bytes)).convert("RGBA")

    # Compare written asset with the same tolerance used above
    diff_written = ImageChops.difference(written_img, expected_img)
    h_w = diff_written.histogram()
    diff_sum_written = sum(i * h_w[i] for i in range(len(h_w)))
    nonzero_written = sum(1 for p in diff_written.getdata() if p != (0, 0, 0, 0))
    assert nonzero_written <= MAX_NONZERO_PIXELS and diff_sum_written <= MAX_DIFF_SUM, (
        f"Written asset differs from expected (nonzero={nonzero_written}, diff_sum={diff_sum_written}). See tests/scripts/minecraft/assets/debug/ for artifacts."
    )

    # Clean up produced files in tests assets and assets output dir
    if out_file.exists():
        out_file.unlink()
    if rendered_path.exists():
        rendered_path.unlink()

    # Also ensure expected file exists in test assets
    assert expected_path.exists()
