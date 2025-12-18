import json
from pathlib import Path

OUTPUT = Path.cwd() / "scripts" / "minecraft" / "output" / "items.json"


def test_items_file_exists():
    assert OUTPUT.exists(), f"items.json not found at {OUTPUT}"


def test_all_items_have_model_key():
    data = json.load(open(OUTPUT, 'r', encoding='utf-8'))
    assert len(data) > 1700, f"Unexpected item count: {len(data)}"
    for item in data:
        assert 'model' in item, f"Item {item.get('id')} missing 'model' key"


def test_asset_is_string():
    data = json.load(open(OUTPUT, 'r', encoding='utf-8'))
    for item in data:
        assert 'asset' in item, f"Item {item.get('id')} missing 'asset'"
        assert isinstance(item['asset'], str), f"Item {item.get('id')} asset is not a string"