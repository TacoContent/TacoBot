import sys, os
sys.path.append(os.path.abspath('.'))
from scripts.minecraft.modules.asset_extractor import AssetExtractor
from scripts.minecraft.modules.constants import ASSETS_DIR
from PIL import Image
import io

items = [
"actuallyadditions_chiseled_black_quartz_slab",
"actuallyadditions_chiseled_black_quartz_block",
"actuallyadditions_chiseled_black_quartz_stair",
"actuallyadditions_chiseled_black_quartz_wall",
"actuallyadditions_black_quartz_wall",
"actuallyadditions_black_quartz_stair",
"actuallyadditions_black_quartz_slab",
"actuallyadditions_black_quartz_pillar_wall",
"actuallyadditions_black_quartz_pillar_stair",
"actuallyadditions_black_quartz_pillar_slab",
"actuallyadditions_black_quartz_pillar_block",
"actuallyadditions_black_quartz_ore",
"actuallyadditions_black_quartz_brick_wall",
"actuallyadditions_black_quartz_brick_stair",
"actuallyadditions_black_quartz_brick_slab",
"actuallyadditions_black_quartz_brick_block",
"actuallyadditions_black_quartz_block",
]


def make_bytes(size, color=(128,128,128,255)):
    img = Image.new('RGBA', size, color)
    buf = io.BytesIO(); img.save(buf, format='PNG')
    return buf.getvalue()


def guess_type(name):
    if 'stair' in name:
        return 'stairs'
    if 'slab' in name:
        return 'slab'
    if 'wall' in name:
        return 'wall'
    if 'ore' in name:
        return 'block'
    return 'block'

print('ASSETS_DIR', ASSETS_DIR)
for item in items:
    bt = guess_type(item)
    print('\nItem:', item, 'type=', bt)

    # Render with 32px textures
    textures32 = {'up': make_bytes((32,32)), 'left': make_bytes((32,32)), 'right': make_bytes((32,32))}
    fn1,b64,w1,h1 = AssetExtractor.render_3d_block(item, textures32, 'test.jar', include_asset=True, block_type=bt, overwrite=True)
    print('  32px input =>', (w1,h1), 'file=', fn1)

    # Render with 64px textures
    textures64 = {'up': make_bytes((64,64)), 'left': make_bytes((64,64)), 'right': make_bytes((64,64))}
    fn2,b64,w2,h2 = AssetExtractor.render_3d_block(item, textures64, 'test.jar', include_asset=True, block_type=bt, overwrite=True)
    print('  64px input =>', (w2,h2), 'file=', fn2)

print('\nDone')
