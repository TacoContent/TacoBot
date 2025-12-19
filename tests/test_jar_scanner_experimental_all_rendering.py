import io
import json
from pathlib import Path
from zipfile import ZipFile

from scripts.minecraft.modules import jar_scanner as js
from scripts.minecraft.modules import constants as consts


def _make_png_bytes(color=(255, 0, 255, 255), size=(16, 16)):
    from PIL import Image
    import io
    buf = io.BytesIO()
    img = Image.new("RGBA", size, color)
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_experimental_renders_all_items(tmp_path, monkeypatch):
    # Point JARS_DIR and ASSETS_DIR to temp dirs
    monkeypatch.setattr(consts, 'JARS_DIR', tmp_path)
    monkeypatch.setattr(consts, 'ASSETS_DIR', tmp_path / 'assets')
    (tmp_path / 'assets').mkdir()

    # Create a simple jar with one item definition and a corresponding model
    jar_path = tmp_path / 'test.jar'
    with ZipFile(jar_path, 'w') as z:
        # New-style item definition
        item_def = {"model": {"model": "item/test_item"}}
        z.writestr('assets/minecraft/items/test_item.json', json.dumps(item_def))

        # Model file with a layer0 texture
        model = {"textures": {"layer0": "minecraft:item/test_texture"}}
        z.writestr('assets/minecraft/models/item/test_item.json', json.dumps(model))

        # Texture
        z.writestr('assets/minecraft/textures/item/test_texture.png', _make_png_bytes())

    called = {'was_called': False, 'args': None}

    def fake_render_model(zip_ref, model_data, namespace, item_id, include_asset, overwrite):
        called['was_called'] = True
        called['args'] = (item_id, model_data.get('textures'))
        # Return a dummy asset filename
        return 'minecraft_test_item.png', None, 32, 32

    monkeypatch.setattr(js.AssetExtractor, 'render_model', staticmethod(fake_render_model))

    scanner = js.JarScanner(experimental=True)
    # Run processing on our test jar
    scanner.process_jar(jar_path)

    assert called['was_called'] is True
    assert 'minecraft:test_item' == called['args'][0]
