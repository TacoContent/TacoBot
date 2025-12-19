import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from scripts.minecraft.modules.asset_extractor import AssetExtractor
with open('scripts/minecraft/output/tmp_heavy_core.png','rb') as f:
    tex=f.read()
fn,b64,w,h=AssetExtractor.render_3d_block('test:heavy_core_extracted', {'up':tex,'left':tex,'right':tex}, 'client.jar', include_asset=False, block_type='block', tint=None, overwrite=True)
print('rendered',fn,w,h)
with open('scripts/minecraft/output/check_heavy_core.png','rb') as f:
    data=f.read()
print('output_size',len(data))
