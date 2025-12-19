from PIL import Image
img=Image.open('scripts/minecraft/output/tmp_heavy_core.png').convert('RGBA')
print('size',img.size,'non_trans',sum(1 for p in img.getdata() if p[3]>0),'avg',tuple(sum(p[i] for p in img.getdata() if p[3]>0)//max(1,sum(1 for p in img.getdata() if p[3]>0)) for i in range(3)))
