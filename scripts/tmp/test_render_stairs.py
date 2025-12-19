import sys, os
sys.path.append(os.path.abspath('.'))
from scripts.minecraft.modules.asset_extractor import AssetExtractor
from PIL import Image
import io

def make_bytes(size, color):
    img=Image.new("RGBA", size, color)
    buf=io.BytesIO(); img.save(buf, format='PNG')
    return buf.getvalue()

textures = {
    'up': make_bytes((64,64),(255,0,0,255)),
    'left': make_bytes((64,64),(0,255,0,255)),
    'right': make_bytes((64,64),(0,0,255,255))
}
fn,b64,w,h = AssetExtractor.render_3d_block('test:stairs', textures, 'test.jar', include_asset=True, block_type='stairs', overwrite=True)
print(fn, w, h)
from pathlib import Path
from scripts.minecraft.modules.constants import ASSETS_DIR
print('ASSETS_DIR', ASSETS_DIR)
p = ASSETS_DIR / fn
print('exists', p.exists())
if p.exists():
    from PIL import Image
    with Image.open(p) as img:
        print('img size', img.size)
        img.save('scripts/tmp/test_render_stairs_out.png')
        print('wrote scripts/tmp/test_render_stairs_out.png')
