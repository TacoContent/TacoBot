import tempfile
from zipfile import ZipFile
from pathlib import Path
import tomllib
import base64
import json

from scripts.minecraft.modules.jar_scanner import JarScanner
from PIL import Image
import io


def _write_zip(path: Path, files: dict):
    with ZipFile(path, 'w') as z:
        for name, data in files.items():
            if isinstance(data, bytes):
                z.writestr(name, data)
            else:
                z.writestr(name, data)


def test_extract_mod_info_from_neoforge_mods_toml_valid_logo(tmp_path):
    zpath = tmp_path / 'mod_with_logo.jar'
    files = {}

    # Create a small square PNG (32x32) < 5KB
    img = Image.new('RGBA', (32, 32), (10, 20, 30, 255))
    b = tempfile.NamedTemporaryFile(delete=False)
    img.save(b.name, 'PNG')
    with open(b.name, 'rb') as fh:
        img_bytes = fh.read()

    # Create a neoforge style mods toml
    toml_content = (
        '[[mods]]\n'
        'modId = "testmod"\n'
        'version = "1.0"\n'
        'displayName = "Test Mod"\n'
        'logoFile = "assets/testmod/icon.png"\n'
    )

    files['META-INF/neoforge.mods.toml'] = toml_content
    files['assets/testmod/icon.png'] = img_bytes

    _write_zip(zpath, files)

    js = JarScanner()
    with ZipFile(zpath, 'r') as z:
        mod_info = js.extract_mod_info(z)

    assert mod_info is not None
    assert mod_info.get('id') == 'testmod'
    assert 'icon' in mod_info
    icon = mod_info['icon']
    assert 'asset_b64' in icon and 'content_type' in icon
    decoded = base64.b64decode(icon['asset_b64'])
    assert decoded == img_bytes
    assert icon['content_type'].startswith('image/')


def test_extract_mod_info_rejects_large_or_non_square_logo(tmp_path):
    zpath = tmp_path / 'mod_with_bad_logo.jar'
    files = {}

    # Create a non-square image (32x16) which should be rejected
    img_ns = Image.new('RGBA', (32, 16), (10, 20, 30, 255))
    b_ns = tempfile.NamedTemporaryFile(delete=False)
    img_ns.save(b_ns.name, 'PNG')
    with open(b_ns.name, 'rb') as fh:
        img_ns_bytes = fh.read()

    # Create a large square image (~300x300) which should exceed 5KB
    img_large = Image.new('RGBA', (300, 300), (50, 60, 70, 255))
    b_l = tempfile.NamedTemporaryFile(delete=False)
    img_large.save(b_l.name, 'PNG')
    with open(b_l.name, 'rb') as fh:
        img_large_bytes = fh.read()

    toml_content_ns = (
        '[[mods]]\n'
        'modId = "testmodns"\n'
        'version = "1.1"\n'
        'displayName = "NonSquare Mod"\n'
        'logoFile = "assets/testmodns/icon_ns.png"\n'
    )

    toml_content_large = (
        '[[mods]]\n'
        'modId = "testmodbig"\n'
        'version = "2.0"\n'
        'displayName = "BigLogo Mod"\n'
        'logoFile = "assets/testmodbig/icon_big.png"\n'
    )

    files['META-INF/neoforge.mods.toml'] = toml_content_ns + '\n' + toml_content_large
    files['assets/testmodns/icon_ns.png'] = img_ns_bytes
    files['assets/testmodbig/icon_big.png'] = img_large_bytes

    _write_zip(zpath, files)

    js = JarScanner()
    with ZipFile(zpath, 'r') as z:
        # The function returns the first mod entry; ensure it still returns mod info but without icon
        mod_info = js.extract_mod_info(z)

    assert mod_info is not None
    assert mod_info.get('id') in ('testmodns', 'testmodbig')
    assert 'icon' not in mod_info
