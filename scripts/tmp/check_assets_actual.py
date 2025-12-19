import sys, os
sys.path.append(os.path.abspath('.'))
from scripts.minecraft.modules.constants import ASSETS_DIR
from PIL import Image
from pathlib import Path
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
for it in items:
    p = ASSETS_DIR / (it + '.png')
    if p.exists():
        with Image.open(p) as im:
            print(it, im.size, p)
    else:
        print(it, 'MISSING')
