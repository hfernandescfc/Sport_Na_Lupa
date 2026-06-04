"""
Embed edson_lucas_foto.jpg and Sport Recife escudo into edson_card.svg,
replacing the placeholder elements with actual base64 <image> tags.
Output: edson_card_final.svg
"""
import base64, re
from pathlib import Path

SVG_IN   = "edson_card.svg"
SVG_OUT  = "edson_card_final.svg"
PHOTO    = "edson_lucas_foto.jpg"
LOGO     = "data/cache/logos/1959.png"
AVATAR   = "sportrecifelab_avatar.png"

# ── Encode images ─────────────────────────────────────────────────────────────
def b64(path, mime):
    data = Path(path).read_bytes()
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"

photo_uri  = b64(PHOTO,  "image/jpeg")
logo_uri   = b64(LOGO,   "image/png")
avatar_uri = b64(AVATAR, "image/png")

svg = Path(SVG_IN).read_text(encoding="utf-8")

# ── 1. Add clipPath defs ───────────────────────────────────────────────────────
# Photo: rounded rect x=100,y=200,w=320,h=320, rx=16 (matches the path corners)
# Escudo: circle cx=270,cy=820,r=70
new_defs = """
  <clipPath id="clipPhoto">
    <rect x="100" y="200" width="320" height="320" rx="16" ry="16"/>
  </clipPath>
  <clipPath id="clipLogo">
    <circle cx="270" cy="820" r="70"/>
  </clipPath>"""

# Insert into existing <defs> block (after first <defs>)
svg = svg.replace("<defs>", "<defs>" + new_defs, 1)

# ── 2. Replace photo placeholder path with <image> ────────────────────────────
# Placeholder: fill="#222222" followed by the rounded-rect path M404 200H116...
photo_placeholder_pat = re.compile(
    r'fill="#222222"/>\s*<path d="M404 200H116[^"]*"[^/]*/>'
)
photo_replacement = (
    'fill="#222222"/>\n'
    f'<image href="{photo_uri}" x="100" y="200" width="320" height="320" '
    'preserveAspectRatio="xMidYMid slice" clip-path="url(#clipPhoto)"/>'
)
svg, n_photo = re.subn(photo_placeholder_pat, photo_replacement, svg)
print(f"Photo placeholder replaced: {n_photo}")

# ── 3. Replace escudo placeholder circle path with <image> ───────────────────
# Placeholder: the circle path M270 890C...fill="#1A1A1A"
logo_placeholder_pat = re.compile(
    r'<path d="M270 890C308\.66 890 340 858\.66 340 820C340 781\.34 308\.66 750 270 750C231\.34 750 200 781\.34 200 820C200 858\.66 231\.34 890 270 890Z" fill="#1A1A1A"/>'
)
logo_replacement = (
    f'<image href="{logo_uri}" x="200" y="750" width="140" height="140" '
    'preserveAspectRatio="xMidYMid meet" clip-path="url(#clipLogo)"/>'
)
svg, n_logo = re.subn(logo_placeholder_pat, logo_replacement, svg)
print(f"Logo placeholder replaced: {n_logo}")

# ── 4. Remove "ESCUDO" placeholder text (single compound path, fill=#FFC700) ──
escudo_text_pat = re.compile(
    r'<path d="M231\.585 830V816\.909.*?fill="#FFC700"/>',
    re.DOTALL
)
svg, n_text = re.subn(escudo_text_pat, "", svg)
print(f"ESCUDO text removed: {n_text}")

# ── 5. Inject SportRecifeLab watermark in the footer ─────────────────────────
watermark = f"""
  <image href="{avatar_uri}" x="50" y="910" width="50" height="50" preserveAspectRatio="xMidYMid meet"/>
  <text x="112" y="942" font-family="Inter, Arial, sans-serif" font-size="26" font-weight="700" fill="#FFC700">@SportRecifeLab</text>
"""
# Insert inside the main clip-path group, before its closing </g>
# The main </g> is right before the second <defs> block
svg = svg.replace("</g>\n<defs>", watermark + "</g>\n<defs>", 1)
print("Watermark injected")

Path(SVG_OUT).write_text(svg, encoding="utf-8")
print(f"Saved: {SVG_OUT}  ({len(svg)//1024} KB)")
