from PIL import Image
p='tests/scripts/minecraft/assets/debug'
act=Image.open(p+'/actual_worm.png').convert('RGBA')
exp=Image.open(p+'/expected_worm.png').convert('RGBA')
df=Image.open(p+'/diff_worm.png').convert('RGBA')
print('sizes', act.size, exp.size)
print('bbox diff nonzero region sample pixels:')
for y in range(2,6):
    print(y, [act.getpixel((12,y)), exp.getpixel((12,y)), df.getpixel((12,y))])
print('center area some pixels:')
for x in range(9,14):
    for y in [5,10,20,30]:
        print('pixel',x,y, act.getpixel((x,y)), exp.getpixel((x,y)))
