import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from zipfile import ZipFile
from scripts.minecraft.modules.jar_scanner import JarScanner
from scripts.minecraft.modules.asset_extractor import AssetExtractor

jar='scripts/minecraft/jars/client-1.21.1-20240808.144430-extra.jar'
js=JarScanner()
with ZipFile(jar) as z:
    for name in ['heavy_core','conduit']:
        texs, btype = js.find_block_textures(z, set(z.namelist()), 'minecraft', name, f'assets/minecraft/models/item/{name}.json')
        print('found block_textures for',name,'keys', list(texs.keys()) if texs else None, 'block_type', btype)
        if texs:
            fn,b64,w,h = AssetExtractor.render_3d_block(f'minecraft:{name}', texs, 'client.jar', include_asset=True, block_type=btype, tint=None, overwrite=True)
            print('wrote',fn,w,h)
        else:
            print('No textures found for',name,', skipping')
