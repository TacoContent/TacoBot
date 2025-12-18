import json
import tempfile
from zipfile import ZipFile
from pathlib import Path

from scripts.minecraft.modules.jar_scanner import JarScanner


def _write_zip(path: Path, files: dict):
    with ZipFile(path, 'w') as z:
        for name, data in files.items():
            if isinstance(data, bytes):
                z.writestr(name, data)
            else:
                z.writestr(name, json.dumps(data))


def test_builtin_entity_falls_back_to_block_model(tmp_path):
    # Create a minimal zip with an item model using builtin/entity and a block model
    zpath = tmp_path / 'test.jar'
    files = {}
    # item model referencing builtin entity
    files['assets/minecraft/models/item/chest.json'] = {"parent": "builtin/entity"}
    # block model for chest with textures
    files['assets/minecraft/models/block/chest.json'] = {"textures": {"all": "minecraft:block/stone"}}
    # add the texture file
    from PIL import Image

    img = Image.new('RGBA', (16, 16), (255, 0, 0, 255))
    b = tempfile.NamedTemporaryFile(delete=False)
    img.save(b.name, 'PNG')
    with open(b.name, 'rb') as fh:
        files['assets/minecraft/textures/block/stone.png'] = fh.read()

    _write_zip(zpath, files)

    js = JarScanner(experimental=True)
    with ZipFile(zpath, 'r') as z:
        file_list = set(z.namelist())
        print('zip contains:', sorted(list(file_list)))
        # Check resolved textures for the candidate model directly
        cand = 'minecraft:block/chest'
        import inspect
        print('function:', js._resolve_model_textures)
        try:
            print('source:\n', inspect.getsource(js._resolve_model_textures))
        except Exception as e:
            print('could not get source', e)
        resolved = js._resolve_model_textures(z, file_list, cand, 'minecraft')
        resolved2 = js._resolve_model_textures(z, file_list, 'block/chest', 'minecraft')
        print('resolved textures for candidate repr:', repr(resolved), 'type:', type(resolved))
        print('resolved textures for block/chest repr:', repr(resolved2), 'type:', type(resolved2))
        # show raw file and manual resolution
        with z.open('assets/minecraft/models/block/chest.json') as rf:
            raw = rf.read()
            print('raw model:', raw)
            import json as _json
            md = _json.loads(raw)
            print('manual textures from file:', md.get('textures'))

        textures, btype = js.find_block_textures(z, file_list, 'minecraft', 'chest', 'assets/minecraft/models/item/chest.json')
        print('find_block_textures ->', textures, btype)

    assert textures is not None
    assert 'up' in textures and 'left' in textures and 'right' in textures


def test_parent_chain_detects_stairs(tmp_path):
    zpath = tmp_path / 'test2.jar'
    files = {}
    # item model directly references block with parent that includes 'stairs'
    files['assets/minecraft/models/item/example.json'] = {"parent": "minecraft:block/custom_stairs_item"}
    files['assets/minecraft/models/block/custom_stairs_item.json'] = {"parent": "minecraft:block/stone_stairs", "textures": {"all": "minecraft:block/stone"}}

    from PIL import Image
    img = Image.new('RGBA', (16, 16), (0, 255, 0, 255))
    b = tempfile.NamedTemporaryFile(delete=False)
    img.save(b.name, 'PNG')
    with open(b.name, 'rb') as fh:
        files['assets/minecraft/textures/block/stone.png'] = fh.read()

    _write_zip(zpath, files)

    js = JarScanner(experimental=True)
    with ZipFile(zpath, 'r') as z:
        file_list = set(z.namelist())
        print('zip contains:', sorted(list(file_list)))
        resolved = js._resolve_model_textures(z, file_list, 'minecraft:block/custom_stairs_item', 'minecraft')
        print('resolved textures for custom_stairs_item:', resolved)
        chain = js._get_model_parent_chain(z, file_list, 'minecraft:block/custom_stairs_item', 'minecraft')
        print('parent chain:', chain)
        textures, btype = js.find_block_textures(z, file_list, 'minecraft', 'example', 'assets/minecraft/models/item/example.json')
        print('find_block_textures ->', textures, btype)

    assert textures is not None
    assert btype == 'stairs'
