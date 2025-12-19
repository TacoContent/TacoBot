import sys
import os
# Ensure project root on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.minecraft.modules.asset_extractor import AssetExtractor
from PIL import Image
import io

# create a 16x16 red texture
img=Image.new('RGBA',(16,16),(255,0,0,255))
buf=io.BytesIO()
img.save(buf,format='PNG')
tex=buf.getvalue()

fn,b64,w,h=AssetExtractor.render_3d_block('test:heavy_core', {'up':tex,'left':tex,'right':tex}, 'test.jar', include_asset=False, block_type='block', tint=None, overwrite=True)
print('rendered',fn,w,h)

fn,b64,w,h=AssetExtractor.render_3d_block('test:conduit', {'up':tex,'left':tex,'right':tex}, 'test.jar', include_asset=False, block_type='conduit', tint=None, overwrite=True)
print('rendered',fn,w,h)

fn,b64,w,h=AssetExtractor.render_3d_block('test:scaffolding', {'up':tex,'left':tex,'right':tex}, 'test.jar', include_asset=False, block_type='scaffolding', tint=None, overwrite=True)
print('rendered',fn,w,h)
