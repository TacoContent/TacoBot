import json
import base64
from PIL import Image
import io
import os

path = os.path.join(os.getcwd(), 'scripts', 'minecraft', 'output', 'items.json')
with open(path, 'r') as f:
    items = json.load(f)

target_ids = [
    'allthemodium:vibranium_block',
    'allthemodium:molten_allthemodium_bucket',
    'minecraft:white_banner',
    'allthemodium:ancient_leaves_bottom'
]

for item in items:
    if item['id'] in target_ids:
        print(f"ID: {item['id']}")
        if 'asset_b64' in item and item['asset_b64']:
            img_data = base64.b64decode(item['asset_b64'])
            img = Image.open(io.BytesIO(img_data))
            print(f"  Size: {img.size}")
        else:
            print("  No asset_b64")
