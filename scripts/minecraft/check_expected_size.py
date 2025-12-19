from PIL import Image
from pathlib import Path
p = Path('tests/scripts/minecraft/assets/expected_worm.png')
if not p.exists():
    print('Expected file missing')
else:
    img = Image.open(p)
    print('expected_worm.png size:', img.size)
    # Also print worm_sprite size
p2 = Path('tests/scripts/minecraft/assets/worm_sprite.png')
if not p2.exists():
    print('Worm sprite missing')
else:
    img2 = Image.open(p2)
    print('worm_sprite.png size:', img2.size)
