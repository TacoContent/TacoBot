from PIL import Image, ImageChops
p='tests/scripts/minecraft/assets/debug'
act=Image.open(p+'/actual_worm.png').convert('RGBA')
exp=Image.open(p+'/expected_worm.png').convert('RGBA')
diff=ImageChops.difference(act,exp)
h=diff.histogram()
# Compute sum of all diff channel values
s=sum(i*(h[i]) for i in range(len(h)))
print('diff total sum', s)
# Also print number of non-zero pixels
bbox=diff.getbbox()
print('bbox', bbox)
nonzero=0
for y in range(diff.size[1]):
    for x in range(diff.size[0]):
        if diff.getpixel((x,y)) != (0,0,0,0):
            nonzero+=1
print('nonzero pixels', nonzero)
