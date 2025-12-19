import zipfile
path='scripts/minecraft/jars/client-1.21.1-20240808.144430-extra.jar'
with zipfile.ZipFile(path) as z:
    p='assets/minecraft/textures/block/heavy_core.png'
    if p in z.namelist():
        data=z.read(p)
        open('scripts/minecraft/output/tmp_heavy_core.png','wb').write(data)
        print('Wrote tmp image to output/tmp_heavy_core.png')
    else:
        print('Texture not found',p)
