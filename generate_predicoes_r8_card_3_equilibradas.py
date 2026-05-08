"""
Card 3 — Jogos Imprevisíveis / Possíveis Zebras da R8
Mobile-first 4:5. Cada jogo com barras GRANDES coloridas e percentuais chamativos.
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

EQUILIBRADAS = [
    {"home": "Ponte Preta", "home_id": 1969, "away": "Sport Recife", "away_id": 1959,
     "prob_home": 0.2961, "prob_draw": 0.3519, "prob_away": 0.3520, "label": "JOGO ABERTO"},
    {"home": "CRB", "home_id": 22032, "away": "Operário-PR", "away_id": 39634,
     "prob_home": 0.2585, "prob_draw": 0.3395, "prob_away": 0.4021, "label": "TUDO POSSÍVEL"},
    {"home": "Grêmio Novorizontino", "home_id": 135514, "away": "Botafogo-SP", "away_id": 1979,
     "prob_home": 0.1799, "prob_draw": 0.2598, "prob_away": 0.5603, "label": "ALERTA DE ZEBRA"},
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
ALERT_RED = "#ff5555"

# Cores das barras de probabilidade
COLOR_AWAY = "#3b82f6"   # azul vibrante
COLOR_DRAW = "#6b7280"   # cinza
COLOR_HOME = "#ef4444"   # vermelho vibrante


def load_logo(team_id: int, size: int) -> Image.Image:
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


def create_equilibradas_card():
    img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), color=DARK_BG)
    draw = ImageDraw.Draw(img)

    f_title = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 56)
    f_subtitle = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 28)
    f_team = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 32)
    f_label = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 24)
    f_pct = ImageFont.truetype("C:/Windows/Fonts/impact.ttf", 44)
    f_legend = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 22)
    f_footer = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 22)

    # ===== TOPO — Faixa amarela =====
    band_h = 110
    draw.rectangle([0, 0, CARD_WIDTH, band_h], fill=GOLD)
    title = "JOGOS IMPREVISÍVEIS // R8"
    bbox = draw.textbbox((0, 0), title, font=f_title)
    tx = (CARD_WIDTH - (bbox[2] - bbox[0])) // 2
    draw.text((tx, 28), title, fill="#0d0d0d", font=f_title)

    y = band_h + 25
    sub = "Probabilidades equilibradas  •  sem favorito claro"
    bbox = draw.textbbox((0, 0), sub, font=f_subtitle)
    sx = (CARD_WIDTH - (bbox[2] - bbox[0])) // 2
    draw.text((sx, y), sub, fill=TEXT_SECONDARY, font=f_subtitle)
    y += 60

    # ===== Cards de cada jogo =====
    card_h = 340
    card_gap = 24
    card_x = 40
    card_w = CARD_WIDTH - 80

    for idx, jogo in enumerate(EQUILIBRADAS):
        cy = y
        is_alert = jogo["label"] == "ALERTA DE ZEBRA"
        accent_color = ALERT_RED if is_alert else GOLD

        # Painel
        draw.rounded_rectangle(
            [card_x, cy, card_x + card_w, cy + card_h],
            radius=18,
            fill=PANEL_BG,
            outline=accent_color,
            width=3,
        )

        # Selo do label (canto superior)
        label = jogo["label"]
        bbox = draw.textbbox((0, 0), label, font=f_label)
        lbl_w = bbox[2] - bbox[0]
        lbl_h = bbox[3] - bbox[1]
        lbl_pad = 14
        lbl_x = card_x + 24
        lbl_y = cy + 18
        draw.rounded_rectangle(
            [lbl_x, lbl_y, lbl_x + lbl_w + 2*lbl_pad, lbl_y + lbl_h + 16],
            radius=8,
            fill=accent_color,
        )
        draw.text((lbl_x + lbl_pad, lbl_y + 4), label, fill="#0d0d0d", font=f_label)

        # Logos + nomes (linha) — Convenção BR: mandante esquerda, visitante direita
        logo_size = 78
        logo_y = cy + 75
        home_x = card_x + 30                              # mandante à esquerda
        away_x = card_x + card_w - 30 - logo_size         # visitante à direita

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

        # Nomes ao lado dos logos
        home_name = jogo["home"].upper()
        away_name = jogo["away"].upper()
        # área disponível para cada nome
        text_w_max = (card_w - 2*30 - 2*logo_size - 60) // 2

        # Mandante: nome à direita do logo
        f_home_team = fit_text(draw, home_name, "C:/Windows/Fonts/arialbd.ttf", 32, text_w_max)
        bbox = draw.textbbox((0, 0), home_name, font=f_home_team)
        draw.text((home_x + logo_size + 18, logo_y + (logo_size - (bbox[3]-bbox[1]))//2 - 4),
                  home_name, fill=TEXT_PRIMARY, font=f_home_team)

        # Visitante: nome à esquerda do logo
        f_away_team = fit_text(draw, away_name, "C:/Windows/Fonts/arialbd.ttf", 32, text_w_max)
        bbox = draw.textbbox((0, 0), away_name, font=f_away_team)
        away_text_x = away_x - 18 - (bbox[2] - bbox[0])
        draw.text((away_text_x, logo_y + (logo_size - (bbox[3]-bbox[1]))//2 - 4),
                  away_name, fill=TEXT_PRIMARY, font=f_away_team)

        # ===== Barras de probabilidade GRANDES =====
        bars_top = cy + 175
        bar_h = 42
        bar_gap = 8

        bar_x_start = card_x + 30
        bar_total_w = card_w - 60
        # área para texto à direita
        pct_text_w = 100
        bar_w = bar_total_w - pct_text_w - 20

        # Ordem mandante → empate → visitante (top→bottom)
        bars = [
            ("MANDANTE", jogo["prob_home"], COLOR_HOME),
            ("EMPATE", jogo["prob_draw"], COLOR_DRAW),
            ("VISITANTE", jogo["prob_away"], COLOR_AWAY),
        ]
        # Marcar o maior
        max_prob = max(jogo["prob_home"], jogo["prob_draw"], jogo["prob_away"])

        for i, (lbl, prob, col) in enumerate(bars):
            by = bars_top + i * (bar_h + bar_gap)
            # fundo da barra
            draw.rounded_rectangle(
                [bar_x_start, by, bar_x_start + bar_w, by + bar_h],
                radius=8,
                fill="#222222",
            )
            # preenchimento
            fill_w = int(bar_w * prob)
            if fill_w > 8:
                draw.rounded_rectangle(
                    [bar_x_start, by, bar_x_start + fill_w, by + bar_h],
                    radius=8,
                    fill=col,
                )
            # label dentro da barra (esquerda)
            draw.text((bar_x_start + 14, by + 9), lbl, fill="#ffffff", font=f_legend)

            # Percentual à direita
            pct_text = f"{prob*100:.0f}%"
            bbox = draw.textbbox((0, 0), pct_text, font=f_pct)
            pct_w = bbox[2] - bbox[0]
            pct_x_pos = bar_x_start + bar_w + 20
            pct_color = GOLD if prob == max_prob else TEXT_SECONDARY
            draw.text((pct_x_pos, by - 2), pct_text, fill=pct_color, font=f_pct)

        y = cy + card_h + card_gap

    # ===== RODAPÉ =====
    footer_y = CARD_HEIGHT - 50
    draw.line([(60, footer_y - 10), (CARD_WIDTH - 60, footer_y - 10)], fill=ACCENT_GRAY, width=2)
    footer = "@SportRecifeLab  •  Análise de Dados"
    bbox = draw.textbbox((0, 0), footer, font=f_footer)
    fx = (CARD_WIDTH - (bbox[2] - bbox[0])) // 2
    draw.text((fx, footer_y), footer, fill=TEXT_SECONDARY, font=f_footer)

    img.save("pending_posts/2026-05-08_predicoes-r8/card_3_equilibradas.png", quality=95)
    print("[OK] Card 3 (Equilibradas) salvo")


if __name__ == "__main__":
    import os
    os.makedirs("pending_posts/2026-05-08_predicoes-r8", exist_ok=True)
    create_equilibradas_card()
