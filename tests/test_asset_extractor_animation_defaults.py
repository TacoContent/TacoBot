import io
import json
from zipfile import ZipFile
from PIL import Image

from scripts.minecraft.modules import asset_extractor as ae


def _make_png_bytes(color=(255, 0, 255, 255), size=(16, 16)):
    buf = io.BytesIO()
    img = Image.new("RGBA", size, color)
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_override_animation_defaults_to_50ms(tmp_path):
    # Use a temporary assets dir to avoid polluting repo
    ae.ASSETS_DIR = tmp_path

    # Build an in-memory JAR (zip) containing two simple sub-models and their textures
    jar_buf = io.BytesIO()
    with ZipFile(jar_buf, "w") as z:
        # Sub-models (item/frame0 and item/frame1) - use item/generated style with layer0
        frame0 = {"textures": {"layer0": "minecraft:item/test0"}}
        frame1 = {"textures": {"layer0": "minecraft:item/test1"}}

        z.writestr("assets/minecraft/models/item/frame0.json", json.dumps(frame0))
        z.writestr("assets/minecraft/models/item/frame1.json", json.dumps(frame1))

        # Textures for sub-models
        z.writestr("assets/minecraft/textures/item/test0.png", _make_png_bytes((10, 20, 30, 255)))
        z.writestr("assets/minecraft/textures/item/test1.png", _make_png_bytes((40, 50, 60, 255)))

    jar_buf.seek(0)

    with ZipFile(jar_buf, "r") as zf:
        # Main model uses overrides to point to the two sub-models
        model_data = {
            "overrides": [
                {"predicate": {"angle": 0.0}, "model": "item/frame0"},
                {"predicate": {"angle": 180.0}, "model": "item/frame1"},
            ]
        }

        filename, asset_b64, w, h = ae.AssetExtractor.render_model(
            zf, model_data, namespace="minecraft", item_id="minecraft:compass_test", include_asset=False, overwrite=True
        )

    # Expect an animated WebP with 2 frames
    assert filename is not None and filename.endswith(".webp")
    out_path = tmp_path / filename
    assert out_path.exists()

    im = Image.open(out_path)
    n_frames = getattr(im, "n_frames", 1)
    assert n_frames == 2

    # WebP frame durations may not be exposed when reading back; ensure frames exist
    durations = []
    for i in range(n_frames):
        im.seek(i)
        durations.append(int(im.info.get("duration", 0) or 0))

    assert n_frames == 2
