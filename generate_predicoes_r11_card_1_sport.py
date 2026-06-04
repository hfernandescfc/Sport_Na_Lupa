"""
Card 1 — Pré-Rodada R11 Série B 2026
Foco TOTAL no clássico Sport × Náutico. Mobile-first 4:5.
Narrativa: modelo vê EMPATE TÉCNICO — margem de 0.9pp entre empate (37.2%) e vitória Sport (36.3%).
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

SPORT_MATCH = {
    "home": "Sport Recife",
    "home_id": 1959,
    "away": "Náutico",
    "away_id": 2011,
    "prob_home": 0.3627,
    "prob_draw": 0.3723,
    "prob_away": 0.2649,
}

CARD_WIDTH = 1080
CARD_HEIGHT = 1200

DARK_BG = "#0d0d0d"
GOLD = "#F5C400"
GOLD_DARK = "#C9A100"
ACCENT_GRAY = "#1f1f1f"
PANEL_BG = "#161616"
TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#9a9a9a"
AWAY_COLOR = "#7a7a7a"
DRAW_COLOR = "#3d3d3d"


def load_logo(team_id: int, size: int):
    logo_path = Path(f"data/cache/logos/{team_id}.png")
    if not logo_path.exists():
        return None
    logo = Image.open(logo_path).convert("RGBA")
    logo.thumbnail((size, size), Image.Resampling.LANCZOS)
    return logo


def fit_text(draw, text, font, max_width):
    size = font.size
    while size > 12:
        f = ImageFont.truetype(font.path, size)
        bbox = draw.textbbox((0, 0), text, font=f)
        if bbox[2] - bbox[0] <= max_width:
            return f
        size -= 2
    return ImageFont.truetype(font.path, 12)


def create_sport_card():
    img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), color=DARK_BG)
    draw = ImageDraw.Draw(img)

    f_title = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 56)
    f_subtitle = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 30)
    f_team = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 36)
    f_vs = ImageFont.truetype("C:/Windows/Fonts/impact.ttf", 90)
    f_pct_label = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 30)
    f_pct = ImageFont.truetype("C:/Windows/Fonts/impact.ttf", 260)
    f_pct_small = ImageFont.truetype("C:/Windows/Fonts/impact.ttf", 50)
    f_bar_label = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 24)
    f_insight = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 26)
    f_footer = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 22)

    # ===== TOPO — Faixa amarela cheia =====
    band_h = 110
    draw.rectangle([0, 0, CARD_WIDTH, band_h], fill=GOLD)
    title = "PRÉ-RODADA 11 // SÉRIE B"
    bbox = draw.textbbox((0, 0), title, font=f_title)
    tx = (CARD_WIDTH - (bbox[2] - bbox[0])) // 2
    draw.text((tx, 28), title, fill="#0d0d0d", font=f_title)

    y = band_h + 28
    sub = "Modelo ML  •  18 features  •  base R1-R10"
    bbox = draw.textbbox((0, 0), sub, font=f_subtitle)
    sx = (CARD_WIDTH - (bbox[2] - bbox[0])) // 2
    draw.text((sx, y), sub, fill=TEXT_SECONDARY, font=f_subtitle)
    y += 60

    # ===== Confronto: logos + VS =====
    logo_size = 220
    logo_y = y
    home_logo = load_logo(SPORT_MATCH["home_id"], logo_size)
    away_logo = load_logo(SPORT_MATCH["away_id"], logo_size)

    home_x = 130
    away_x = CARD_WIDTH - 130 - logo_size

    if home_logo:
        hx = home_x + (logo_size - home_logo.width) // 2
        hy = logo_y + (logo_size - home_logo.height) // 2
        img.paste(home_logo, (hx, hy), home_logo)
    if away_logo:
        ax = away_x + (logo_size - away_logo.width) // 2
        ay = logo_y + (logo_size - away_logo.height) // 2
        img.paste(away_logo, (ax, ay), away_logo)

    vs_text = "VS"
    bbox = draw.textbbox((0, 0), vs_text, font=f_vs)
    vs_w = bbox[2] - bbox[0]
    vs_x = (CARD_WIDTH - vs_w) // 2
    vs_y = logo_y + (logo_size - (bbox[3] - bbox[1])) // 2 - 10
    draw.text((vs_x, vs_y), vs_text, fill=GOLD, font=f_vs)

    y = logo_y + logo_size + 12

    home_name = "SPORT RECIFE"
    away_name = "NÁUTICO"

    f_home = fit_text(draw, home_name, f_team, logo_size + 40)
    f_away = fit_text(draw, away_name, f_team, logo_size + 40)

    bbox = draw.textbbox((0, 0), home_name, font=f_home)
    hx = home_x + (logo_size - (bbox[2] - bbox[0])) // 2
    draw.text((hx, y), home_name, fill=TEXT_PRIMARY, font=f_home)

    bbox = draw.textbbox((0, 0), away_name, font=f_away)
    ax = away_x + (logo_size - (bbox[2] - bbox[0])) // 2
    draw.text((ax, y), away_name, fill=TEXT_PRIMARY, font=f_away)

    f_tag = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 18)
    tag_y = y + 48
    home_tag = "MANDANTE"
    away_tag = "VISITANTE"
    bbox = draw.textbbox((0, 0), home_tag, font=f_tag)
    hx_t = home_x + (logo_size - (bbox[2] - bbox[0])) // 2
    draw.text((hx_t, tag_y), home_tag, fill=TEXT_SECONDARY, font=f_tag)
    bbox = draw.textbbox((0, 0), away_tag, font=f_tag)
    ax_t = away_x + (logo_size - (bbox[2] - bbox[0])) // 2
    draw.text((ax_t, tag_y), away_tag, fill=TEXT_SECONDARY, font=f_tag)

    y = tag_y + 50

    # ===== PAINEL CENTRAL — Big % do empate (cenário mais provável) =====
    panel_h = 340
    panel_top = y
    draw.rounded_rectangle(
        [40, panel_top, CARD_WIDTH - 40, panel_top + panel_h],
        radius=24,
        fill=PANEL_BG,
        outline=GOLD_DARK,
        width=3,
    )

    lbl = "CLÁSSICO SEM FAVORITO — EMPATE LIDERA"
    bbox = draw.textbbox((0, 0), lbl, font=f_pct_label)
    lx = (CARD_WIDTH - (bbox[2] - bbox[0])) // 2
    draw.text((lx, panel_top + 26), lbl, fill=GOLD, font=f_pct_label)

    # Empate é o cenário mais provável (37.2%)
    pct_value = SPORT_MATCH['prob_draw'] * 100
    pct_text = f"{pct_value:.0f}"
    bbox = draw.textbbox((0, 0), pct_text, font=f_pct)
    pct_w = bbox[2] - bbox[0]

    sign = "%"
    bbox_s = draw.textbbox((0, 0), sign, font=f_pct_small)
    sign_w = bbox_s[2] - bbox_s[0]

    total_w = pct_w + sign_w + 14
    pct_x = (CARD_WIDTH - total_w) // 2
    pct_y = panel_top + 70
    draw.text((pct_x, pct_y), pct_text, fill=GOLD, font=f_pct)
    draw.text((pct_x + pct_w + 14, pct_y + 60), sign, fill=GOLD, font=f_pct_small)

    y = panel_top + panel_h + 40

    # ===== Barra de probabilidades 3-vias =====
    bar_label = "DISTRIBUIÇÃO COMPLETA"
    bbox = draw.textbbox((0, 0), bar_label, font=f_bar_label)
    blx = (CARD_WIDTH - (bbox[2] - bbox[0])) // 2
    draw.text((blx, y), bar_label, fill=TEXT_SECONDARY, font=f_bar_label)
    y += 38

    bar_x = 80
    bar_w = CARD_WIDTH - 160
    bar_h = 70

    home_w = int(bar_w * SPORT_MATCH["prob_home"])
    draw_w = int(bar_w * SPORT_MATCH["prob_draw"])
    away_w = bar_w - home_w - draw_w

    # Sport (mandante, GOLD) — empate (cinza médio) — Náutico (visitante, cinza claro)
    draw.rectangle([bar_x, y, bar_x + home_w, y + bar_h], fill=GOLD)
    draw.rectangle([bar_x + home_w, y, bar_x + home_w + draw_w, y + bar_h], fill=DRAW_COLOR)
    draw.rectangle([bar_x + home_w + draw_w, y, bar_x + bar_w, y + bar_h], fill=AWAY_COLOR)

    f_inbar = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 30)

    h_pct = f"{SPORT_MATCH['prob_home']*100:.0f}%"
    bbox = draw.textbbox((0, 0), h_pct, font=f_inbar)
    if home_w >= bbox[2] - bbox[0] + 20:
        draw.text((bar_x + (home_w - (bbox[2]-bbox[0]))//2, y + 18), h_pct, fill="#0d0d0d", font=f_inbar)
    d_pct = f"{SPORT_MATCH['prob_draw']*100:.0f}%"
    bbox = draw.textbbox((0, 0), d_pct, font=f_inbar)
    if draw_w >= bbox[2] - bbox[0] + 20:
        draw.text((bar_x + home_w + (draw_w - (bbox[2]-bbox[0]))//2, y + 18), d_pct, fill="#ffffff", font=f_inbar)
    a_pct = f"{SPORT_MATCH['prob_away']*100:.0f}%"
    bbox = draw.textbbox((0, 0), a_pct, font=f_inbar)
    if away_w >= bbox[2] - bbox[0] + 20:
        draw.text((bar_x + home_w + draw_w + (away_w - (bbox[2]-bbox[0]))//2, y + 18), a_pct, fill="#ffffff", font=f_inbar)

    y += bar_h + 18

    f_leg = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 22)
    leg_y = y
    legend_items = [
        ("SPORT", GOLD),
        ("EMPATE", DRAW_COLOR),
        ("NÁUTICO", AWAY_COLOR),
    ]
    parts = []
    for txt, col in legend_items:
        bbox = draw.textbbox((0, 0), txt, font=f_leg)
        parts.append((txt, col, bbox[2] - bbox[0]))
    total = sum(w for _, _, w in parts) + 24*3 + 40*(len(parts)-1)
    cx = (CARD_WIDTH - total) // 2
    for txt, col, w in parts:
        draw.rectangle([cx, leg_y + 4, cx + 18, leg_y + 22], fill=col)
        draw.text((cx + 24, leg_y), txt, fill=TEXT_SECONDARY, font=f_leg)
        cx += 24 + w + 40

    # ===== Insight final =====
    y += 35
    insight = "SPORT + EMPATE = 73% — só não perder na Ilha"
    f_ins_fit = fit_text(draw, insight, f_insight, CARD_WIDTH - 120)
    bbox = draw.textbbox((0, 0), insight, font=f_ins_fit)
    ix = (CARD_WIDTH - (bbox[2] - bbox[0])) // 2
    box_pad_x = 30
    box_pad_y = 12
    box_w = bbox[2] - bbox[0] + 2 * box_pad_x
    box_h = bbox[3] - bbox[1] + 2 * box_pad_y
    box_x = (CARD_WIDTH - box_w) // 2
    draw.rounded_rectangle([box_x, y, box_x + box_w, y + box_h], radius=8, fill=GOLD)
    draw.text((ix, y + box_pad_y - 4), insight, fill="#0d0d0d", font=f_ins_fit)

    # ===== RODAPÉ =====
    footer_y = CARD_HEIGHT - 50
    draw.line([(60, footer_y - 10), (CARD_WIDTH - 60, footer_y - 10)], fill=ACCENT_GRAY, width=2)
    footer = "@SportRecifeLab  •  Análise de Dados"
    bbox = draw.textbbox((0, 0), footer, font=f_footer)
    fx = (CARD_WIDTH - (bbox[2] - bbox[0])) // 2
    draw.text((fx, footer_y), footer, fill=TEXT_SECONDARY, font=f_footer)

    out_path = "pending_posts/2026-05-29_predicoes-r11/card_1_sport.png"
    img.save(out_path, quality=95)
    print(f"[OK] Card 1 (Sport x Nautico) salvo: {out_path}")


if __name__ == "__main__":
    import os
    os.makedirs("pending_posts/2026-05-29_predicoes-r11", exist_ok=True)
    create_sport_card()
