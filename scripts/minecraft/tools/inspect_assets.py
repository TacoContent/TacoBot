from PIL import Image
import os
names=['minecraft_conduit.png','minecraft_scaffolding.png','minecraft_heavy_core.png','minecraft_black_quartz_brick_wall.png']
path=os.path.join(os.path.dirname(__file__), '..', 'output', 'assets')
for n in names:
    fp=os.path.join(path,n)
    if not os.path.exists(fp):
        print(n,'MISSING')
        continue
    im=Image.open(fp).convert('RGBA')
    w,h=im.size
    px=list(im.getdata())
    non_trans=[p for p in px if p[3]>0]
    avg=[sum(p[i] for p in non_trans)/len(non_trans) for i in range(3)] if non_trans else [0,0,0]
    print(n, 'size',w,h,'non_trans',len(non_trans),'avg_rgb',tuple(int(x) for x in avg))
