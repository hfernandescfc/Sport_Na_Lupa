"""
Card 3 — Demais jogos da Rodada 11
Mobile-first 4:5. Cinco partidas com barras de probabilidade.
R11 — todos os jogos mais equilibrados, vários abaixo de 40%.
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

DEMAIS = [
    {"home": "Ponte Preta", "home_id": 1969, "away": "Botafogo-SP", "away_id": 1979,
     "prob_home": 0.4043, "prob_draw": 0.3019, "prob_away": 0.2938, "result": "H"},
    {"home": "Atlético Goianiense", "home_id": 7314, "away": "Goiás", "away_id": 1960,
     "prob_home": 0.3582, "prob_draw": 0.3172, "prob_away": 0.3246, "result": "H"},
    {"home": "Athletic Club", "home_id": 342775, "away": "Fortaleza", "away_id": 2020,
     "prob_home": 0.3624, "prob_draw": 0.3033, "prob_away": 0.3344, "result": "H"},
    {"home": "Cuiabá", "home_id": 49202, "away": "CRB", "away_id": 22032,
     "prob_home": 0.3362, "prob_draw": 0.3695, "prob_away": 0.2942, "result": "D"},
    {"home": "Londrina", "home_id": 2022, "away": "Vila Nova FC", "away_id": 2021,
     "prob_home": 0.3401, "prob_draw": 0.3430, "prob_away": 0.3169, "result": "D"},
]

CARD_WIDTH = 1080
CARD_HEIGHT = 1350

DARK_BG = "#0d0d0d"
GOLD = "#F5C400"
GOLD_DARK = "#C9A100"
ACCENT_GRAY = "#1f1f1f"
PANEL_BG = "#161616"
TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#9a9a9a"

COLOR_HOME = "#ef4444"
COLOR_DRAW = "#6b7280"
COLOR_AWAY = "#3b82f6"


def load_logo(team_id: int, size: int):
    logo_path = Path(f"data/cache/logos/{team_id}.png")
    if not logo_path.exists():
        return None
    logo = Image.open(logo_path).convert("RGBA")
    logo.thumbnail((size, size), Image.Resampling.LANCZOS)
    return logo


def fit_text(draw, text, font_path, max_size, max_width):
    size = max_size
    while size > 12:
        f = ImageFont.truetype(font_path, size)
        bbox = draw.textbbox((0, 0), text, font=f)
        if bbox[2] - bbox[0] <= max_width:
            return f
        size -= 2
    return ImageFont.truetype(font_path, 12)


def result_label(result: str):
    if result == "H":
        return "MANDANTE", COLOR_HOME
    if result == "A":
        return "VISITANTE", COLOR_AWAY
    return "EMPATE", COLOR_DRAW


def create_demais_card():
    img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), color=DARK_BG)
    draw = ImageDraw.Draw(img)

    f_title = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 56)
    f_subtitle = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 28)
    f_team = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 24)
    f_label = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 18)
    f_pct = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 22)
    f_legend = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 16)
    f_footer = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 22)

    # ===== TOPO — Faixa amarela =====
    band_h = 110
    draw.rectangle([0, 0, CARD_WIDTH, band_h], fill=GOLD)
    title = "DEMAIS JOGOS // R11"
    bbox = draw.textbbox((0, 0), title, font=f_title)
    tx = (CARD_WIDTH - (bbox[2] - bbox[0])) // 2
    draw.text((tx, 28), title, fill="#0d0d0d", font=f_title)

    y = band_h + 25
    sub = "Cinco partidas restantes  •  jogos equilibrados"
    bbox = draw.textbbox((0, 0), sub, font=f_subtitle)
    sx = (CARD_WIDTH - (bbox[2] - bbox[0])) // 2
    draw.text((sx, y), sub, fill=TEXT_SECONDARY, font=f_subtitle)
    y += 56

    card_h = 198
    card_gap = 14
    card_x = 40
    card_w = CARD_WIDTH - 80

    for jogo in DEMAIS:
        cy = y
        label_text, accent_color = result_label(jogo["result"])

        draw.rounded_rectangle(
            [card_x, cy, card_x + card_w, cy + card_h],
            radius=16,
            fill=PANEL_BG,
            outline=accent_color,
            width=2,
        )

        # Selo do label
        bbox = draw.textbbox((0, 0), label_text, font=f_label)
        lbl_w = bbox[2] - bbox[0]
        lbl_h = bbox[3] - bbox[1]
        lbl_pad = 12
        lbl_x = card_x + 20
        lbl_y = cy + 14
        draw.rounded_rectangle(
            [lbl_x, lbl_y, lbl_x + lbl_w + 2*lbl_pad, lbl_y + lbl_h + 12],
            radius=6,
            fill=accent_color,
        )
        draw.text((lbl_x + lbl_pad, lbl_y + 4), label_text, fill="#0d0d0d", font=f_label)

        # Logos + nomes (linha)
        logo_size = 60
        logo_y = cy + 56
        home_x = card_x + 24
        away_x = card_x + card_w - 24 - logo_size

        home_logo = load_logo(jogo["home_id"], logo_size)
        away_logo = load_logo(jogo["away_id"], logo_size)

        if home_logo:
            hx = home_x + (logo_size - home_logo.width) // 2
            hy = logo_y + (logo_size - home_logo.height) // 2
            img.paste(home_logo, (hx, hy), home_logo)
        if away_logo:
            ax = away_x + (logo_size - away_logo.width) // 2
            ay = logo_y + (logo_size - away_logo.height) // 2
            img.paste(away_logo, (ax, ay), away_logo)

        home_name = jogo["home"].upper()
        away_name = jogo["away"].upper()
        text_w_max = (card_w - 2*24 - 2*logo_size - 40) // 2

        f_home_team = fit_text(draw, home_name, "C:/Windows/Fonts/arialbd.ttf", 24, text_w_max)
        bbox = draw.textbbox((0, 0), home_name, font=f_home_team)
        draw.text((home_x + logo_size + 14, logo_y + (logo_size - (bbox[3]-bbox[1]))//2 - 3),
                  home_name, fill=TEXT_PRIMARY, font=f_home_team)

        f_away_team = fit_text(draw, away_name, "C:/Windows/Fonts/arialbd.ttf", 24, text_w_max)
        bbox = draw.textbbox((0, 0), away_name, font=f_away_team)
        away_text_x = away_x - 14 - (bbox[2] - bbox[0])
        draw.text((away_text_x, logo_y + (logo_size - (bbox[3]-bbox[1]))//2 - 3),
                  away_name, fill=TEXT_PRIMARY, font=f_away_team)

        # Barras de probabilidade — compactas
        bars_top = cy + 128
        bar_h = 22
        bar_gap = 4

        bar_x_start = card_x + 24
        bar_total_w = card_w - 48
        pct_text_w = 80
        bar_w = bar_total_w - pct_text_w - 16

        bars = [
            ("MAND.", jogo["prob_home"], COLOR_HOME),
            ("EMP.", jogo["prob_draw"], COLOR_DRAW),
            ("VISIT.", jogo["prob_away"], COLOR_AWAY),
        ]
        max_prob = max(jogo["prob_home"], jogo["prob_draw"], jogo["prob_away"])

        for i, (lbl, prob, col) in enumerate(bars):
            by = bars_top + i * (bar_h + bar_gap)
            draw.rounded_rectangle(
                [bar_x_start, by, bar_x_start + bar_w, by + bar_h],
                radius=6,
                fill="#222222",
            )
            fill_w = int(bar_w * prob)
            if fill_w > 8:
                draw.rounded_rectangle(
                    [bar_x_start, by, bar_x_start + fill_w, by + bar_h],
                    radius=6,
                    fill=col,
                )
            draw.text((bar_x_start + 10, by + 3), lbl, fill="#ffffff", font=f_legend)

            pct_text = f"{prob*100:.0f}%"
            pct_x_pos = bar_x_start + bar_w + 18
            pct_color = GOLD if prob == max_prob else TEXT_SECONDARY
            draw.text((pct_x_pos, by + 1), pct_text, fill=pct_color, font=f_pct)

        y = cy + card_h + card_gap

    # ===== RODAPÉ =====
    footer_y = CARD_HEIGHT - 50
    draw.line([(60, footer_y - 10), (CARD_WIDTH - 60, footer_y - 10)], fill=ACCENT_GRAY, width=2)
    footer = "@SportRecifeLab  •  Análise de Dados"
    bbox = draw.textbbox((0, 0), footer, font=f_footer)
    fx = (CARD_WIDTH - (bbox[2] - bbox[0])) // 2
    draw.text((fx, footer_y), footer, fill=TEXT_SECONDARY, font=f_footer)

    out_path = "pending_posts/2026-05-29_predicoes-r11/card_3_demais.png"
    img.save(out_path, quality=95)
    print(f"[OK] Card 3 (Demais jogos) salvo: {out_path}")


if __name__ == "__main__":
    import os
    os.makedirs("pending_posts/2026-05-29_predicoes-r11", exist_ok=True)
    create_demais_card()
