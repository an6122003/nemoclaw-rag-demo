"""Draw the workshop's desktop icon (the page's favicon) as a Windows .ico file.

    .venv/Scripts/python.exe windows/make_icon.py .run/workshop.ico

Pillow comes with matplotlib, so the workshop's Python environment has it.
"""

import sys

from PIL import Image, ImageDraw

im = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
d = ImageDraw.Draw(im)
d.rounded_rectangle((8, 8, 248, 248), radius=56, fill=(7, 18, 48, 255))
d.line([(52, 182), (100, 168), (136, 120), (168, 82), (206, 66)], fill=(118, 185, 0, 255), width=22, joint="curve")
d.line([(52, 214), (106, 198), (140, 160), (172, 128), (206, 116)], fill=(169, 201, 255, 190), width=14, joint="curve")
im.save(sys.argv[1], sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (256, 256)])
