"""
Render edson_card_final.svg → edson_card_final_preview.png at exactly 1080x1080.
Strategy: open SVG directly (no HTML wrapper), capture large window,
then use Pillow to detect and crop the card content area.
"""
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from PIL import Image
import os, time, io

options = Options()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--force-device-scale-factor=1")
driver = webdriver.Edge(options=options)

svg_path = os.path.abspath("edson_card_final.svg").replace("\\", "/")

# Build minimal HTML that renders the SVG at exactly 1080x1080 with no scrollbars
html = f"""<!DOCTYPE html>
<html><head><style>
*{{margin:0;padding:0}}
html,body{{width:1080px;height:1080px;overflow:hidden;background:#0a0a0a}}
</style></head>
<body>
<object type="image/svg+xml" data="file:///{svg_path}" width="1080" height="1080"
  style="display:block;width:1080px;height:1080px;overflow:hidden"></object>
</body></html>"""

import pathlib
wrapper = pathlib.Path("edson_card_wrapper.html")
wrapper.write_text(html, encoding="utf-8")

html_path = os.path.abspath(str(wrapper)).replace("\\", "/")
driver.get("file:///" + html_path)
time.sleep(2)

# Set window large enough to capture full card; we'll crop after
driver.set_window_size(2000, 2000)
time.sleep(0.5)
png_bytes = driver.get_screenshot_as_png()
driver.quit()

img = Image.open(io.BytesIO(png_bytes))
w, h = img.size
print(f"Raw screenshot: {w}x{h}")

# With --force-device-scale-factor=1: 1 CSS px = 1 device px.
# Body is exactly 1080x1080 CSS px, so card fills top-left 1080x1080 of screenshot.
card = img.crop((0, 0, 1080, 1080))
card.save("edson_card_final_preview.png")
print(f"Raw {w}x{h} -> cropped 1080x1080 saved")
