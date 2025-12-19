import io
from PIL import Image

# Create frame 16x32 with green bottom half
frame = Image.new("RGBA", (16, 32), (0, 0, 0, 0))
for y in range(16, 32):
    for x in range(0, 16):
        frame.putpixel((x, y), (0, 255, 0, 255))

raw_tex = frame
w, h = raw_tex.size
print('raw size', w, h)
if w > h and w % h == 0:
    frames = w // h
    if frames > 1:
        f1 = raw_tex.crop((0,0,h,h))
        f2 = raw_tex.crop((h,0,2*h,h))
        print('compare frames equal?', list(f1.getdata())[:10] == list(f2.getdata())[:10])
        frame_crop = f1 if list(f1.getdata()) == list(f2.getdata()) else raw_tex
    else:
        frame_crop = raw_tex.crop((0,0,h,h))
elif h > w and h % w == 0:
    frames = h // w
    if frames > 1:
        f1 = raw_tex.crop((0,0,w,w))
        f2 = raw_tex.crop((0,w,w,2*w))
        print('compare frames equal?', list(f1.getdata())[:10] == list(f2.getdata())[:10])
        frame_crop = f1 if list(f1.getdata()) == list(f2.getdata()) else raw_tex
    else:
        frame_crop = raw_tex.crop((0,0,w,w))
else:
    frame_crop = raw_tex
print('frame_crop size', frame_crop.size)

min_side = min(frame_crop.width, frame_crop.height)
scale = 32.0 / float(min_side) if min_side else 1.0
new_w = max(1, int(round(frame_crop.width * scale)))
new_h = max(1, int(round(frame_crop.height * scale)))
print('resize to', new_w, new_h)
frame_resized = frame_crop.resize((new_w, new_h), resample=Image.LANCZOS)
canvas32 = Image.new('RGBA', (32,32), (0,0,0,0))
offset_x = (32 - new_w)//2
offset_y = 32 - new_h
print('offset', offset_x, offset_y)
canvas32.paste(frame_resized, (offset_x, offset_y), frame_resized)

print('bottom center pixel', canvas32.getpixel((16,31)))
canvas32.save('scripts/minecraft/output/debug_canvas32.png')
print('Wrote debug image scripts/minecraft/output/debug_canvas32.png')
