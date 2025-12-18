import json
import base64
from PIL import Image
import io
import os

def check_items():
    json_path = os.path.join(os.getcwd(), 'scripts', 'minecraft', 'output', 'items.json')
    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        return

    with open(json_path, 'r') as f:
        items = json.load(f)

    target_ids = [
        "allthemodium:vibranium_block",
        "allthemodium:molten_allthemodium_bucket",
        "allthemodium:ancient_cavevines",
        "minecraft:bundle",
        "minecraft:white_banner",
        "allthemodium:ancient_leaves_bottom"
    ]

    for item_id in target_ids:
        item = next((i for i in items if i['id'] == item_id), None)
        if not item:
            print(f"Item {item_id} not found.")
            continue

        asset = item.get('asset_b64')
        if not asset:
            print(f"Item {item_id} has no asset_b64.")
            continue

        # Decode base64
        try:
            image_data = base64.b64decode(asset)
            img = Image.open(io.BytesIO(image_data))
            width, height = img.size

            # Check if it's the pink placeholder (32x32, mostly pink)
            is_placeholder = False
            if width == 32 and height == 32:
                # Check a few pixels
                pixels = img.convert('RGB')
                p1 = pixels.getpixel((0, 0))
                p2 = pixels.getpixel((16, 16))
                if p1 == (255, 0, 255) and p2 == (255, 0, 255):
                    is_placeholder = True

            print(f"Item: {item_id}")
            print(f"  Size: {width}x{height}")
            print(f"  Placeholder: {is_placeholder}")

        except Exception as e:
            print(f"Error processing {item_id}: {e}")

if __name__ == "__main__":
    check_items()
