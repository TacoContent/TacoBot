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


def test_override_animation_defaults_to_50ms_capture(tmp_path, monkeypatch):
    ae.ASSETS_DIR = tmp_path

    jar_buf = io.BytesIO()
    with ZipFile(jar_buf, "w") as z:
        frame0 = {"textures": {"layer0": "minecraft:item/test0"}}
        frame1 = {"textures": {"layer0": "minecraft:item/test1"}}

        z.writestr("assets/minecraft/models/item/frame0.json", json.dumps(frame0))
        z.writestr("assets/minecraft/models/item/frame1.json", json.dumps(frame1))

        z.writestr("assets/minecraft/textures/item/test0.png", _make_png_bytes((10, 20, 30, 255)))
        z.writestr("assets/minecraft/textures/item/test1.png", _make_png_bytes((40, 50, 60, 255)))

    jar_buf.seek(0)

    captured = {}
    orig_save = Image.Image.save

    def fake_save(self, fp, format=None, **kwargs):
        # Capture duration when writing WEBP
        if format == "WEBP":
            captured['duration'] = kwargs.get('duration')
        return orig_save(self, fp, format=format, **kwargs)

    monkeypatch.setattr(Image.Image, "save", fake_save)

    with ZipFile(jar_buf, "r") as zf:
        model_data = {
            "overrides": [
                {"predicate": {"angle": 0.0}, "model": "item/frame0"},
                {"predicate": {"angle": 180.0}, "model": "item/frame1"},
            ]
        }

        filename, asset_b64, w, h = ae.AssetExtractor.render_model(
            zf, model_data, namespace="minecraft", item_id="minecraft:compass_test", include_asset=False, overwrite=True
        )

    assert filename.endswith('.webp')
    assert 'duration' in captured

    # Ensure durations were set to 50 ms per frame (20 FPS)
    assert all(int(d) == 50 for d in captured['duration'])
