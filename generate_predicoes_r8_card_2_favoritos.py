"""
Card 2 — Top 4 Favoritos da Rodada 8
Convenção BR: mandante à esquerda, visitante à direita.
Indicador visual identifica qual time é o favorito.
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

FAVORITOS = [
    {"home": "Avaí", "home_id": 7315, "away": "Fortaleza", "away_id": 2020,
     "prob_home": 0.9041, "prob_draw": 0.0743, "prob_away": 0.0216},
    {"home": "Goiás", "home_id": 1960, "away": "Vila Nova FC", "away_id": 2021,
     "prob_home": 0.0166, "prob_draw": 0.1538, "prob_away": 0.8295},
    {"home": "Ceará", "home_id": 2001, "away": "Atlético Goianiense", "away_id": 7314,
     "prob_home": 0.0448, "prob_draw": 0.2697, "prob_away": 0.6855},
    {"home": "Athletic Club", "home_id": 342775, "away": "Cuiabá", "away_id": 49202,
     "prob_home": 0.0742, "prob_draw": 0.2550, "prob_away": 0.6708},
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
RANK_COLORS = ["#F5C400", "#E0B500", "#B8941F", "#8B7615"]


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


def create_favoritos_card():
    img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), color=DARK_BG)
    draw = ImageDraw.Draw(img)

    f_title = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 56)
    f_subtitle = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 28)
    f_team = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 28)
    f_tag = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 16)
    f_pct = ImageFont.truetype("C:/Windows/Fonts/impact.ttf", 110)
    f_pct_sign = ImageFont.truetype("C:/Windows/Fonts/impact.ttf", 36)
    f_rank = ImageFont.truetype("C:/Windows/Fonts/impact.ttf", 56)
    f_fav_label = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 18)
    f_footer = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 22)

    # ===== TOPO — Faixa amarela =====
    band_h = 110
    draw.rectangle([0, 0, CARD_WIDTH, band_h], fill=GOLD)
    title = "TOP 4 FAVORITOS // R8"
    bbox = draw.textbbox((0, 0), title, font=f_title)
    tx = (CARD_WIDTH - (bbox[2] - bbox[0])) // 2
    draw.text((tx, 28), title, fill="#0d0d0d", font=f_title)

    y = band_h + 25
    sub = "Maiores probabilidades de vitória  •  modelo ML"
    bbox = draw.textbbox((0, 0), sub, font=f_subtitle)
    sx = (CARD_WIDTH - (bbox[2] - bbox[0])) // 2
    draw.text((sx, y), sub, fill=TEXT_SECONDARY, font=f_subtitle)
    y += 60

    # ===== Cards de cada favorito =====
    card_h = 240
    card_gap = 20
    card_x = 40
    card_w = CARD_WIDTH - 80

    for idx, fav in enumerate(FAVORITOS):
        # Identifica favorito
        home_is_fav = fav["prob_home"] >= fav["prob_away"]
        if home_is_fav:
            fav_team = fav["home"]
            fav_pct = fav["prob_home"]
        else:
            fav_team = fav["away"]
            fav_pct = fav["prob_away"]

        cy = y
        # Painel
        draw.rounded_rectangle(
            [card_x, cy, card_x + card_w, cy + card_h],
            radius=18,
            fill=PANEL_BG,
        )

        # Stripe lateral colorida (rank)
        stripe_color = RANK_COLORS[idx]
        draw.rounded_rectangle(
            [card_x, cy, card_x + 12, cy + card_h],
            radius=6,
            fill=stripe_color,
        )

        # Rank #N (canto superior esquerdo)
        rank_text = f"#{idx+1}"
        draw.text((card_x + 32, cy + 14), rank_text, fill=stripe_color, font=f_rank)

        # === Confronto: mandante (esq) vs visitante (dir) ===
        logo_size = 96
        # área central reservada para nomes + percentual
        # layout: [rank ~80px] [logo M] [nomes M+V centrais] [%][logo V]
        # Mas vamos usar layout mais limpo:
        # logos nas extremidades, % gigante no meio, nomes acima dos logos
        confronto_top = cy + 30
        home_logo_x = card_x + 110
        # percentual no centro-direita
        # logo visitante mais à direita
        # vamos posicionar: home_logo (esq) + nomes embaixo logo, percentual GIGANTE direita central

        home_logo_x = card_x + 110
        away_logo_x = card_x + card_w - 110 - logo_size

        home_logo = load_logo(fav["home_id"], logo_size)
        away_logo = load_logo(fav["away_id"], logo_size)

        if home_logo:
            hx = home_logo_x + (logo_size - home_logo.width) // 2
            hy = confronto_top + (logo_size - home_logo.height) // 2
            img.paste(home_logo, (hx, hy), home_logo)
        if away_logo:
            ax = away_logo_x + (logo_size - away_logo.width) // 2
            ay = confronto_top + (logo_size - away_logo.height) // 2
            img.paste(away_logo, (ax, ay), away_logo)

        # Borda amarela ao redor do favorito (anel)
        ring_pad = 6
        if home_is_fav:
            draw.rounded_rectangle(
                [home_logo_x - ring_pad, confronto_top - ring_pad,
                 home_logo_x + logo_size + ring_pad, confronto_top + logo_size + ring_pad],
                radius=12, outline=GOLD, width=3,
            )
        else:
            draw.rounded_rectangle(
                [away_logo_x - ring_pad, confronto_top - ring_pad,
                 away_logo_x + logo_size + ring_pad, confronto_top + logo_size + ring_pad],
                radius=12, outline=GOLD, width=3,
            )

        # Nomes abaixo de cada logo
        name_y = confronto_top + logo_size + 8
        home_name = fav["home"].upper()
        away_name = fav["away"].upper()

        f_h = fit_text(draw, home_name, "C:/Windows/Fonts/arialbd.ttf", 26, logo_size + 80)
        bbox = draw.textbbox((0, 0), home_name, font=f_h)
        h_color = GOLD if home_is_fav else TEXT_PRIMARY
        draw.text((home_logo_x + (logo_size - (bbox[2]-bbox[0]))//2, name_y),
                  home_name, fill=h_color, font=f_h)

        f_a = fit_text(draw, away_name, "C:/Windows/Fonts/arialbd.ttf", 26, logo_size + 80)
        bbox = draw.textbbox((0, 0), away_name, font=f_a)
        a_color = GOLD if not home_is_fav else TEXT_PRIMARY
        draw.text((away_logo_x + (logo_size - (bbox[2]-bbox[0]))//2, name_y),
                  away_name, fill=a_color, font=f_a)

        # Tag (M)/(V) acima dos logos (pequeno)
        tag_y = confronto_top - 22
        bbox = draw.textbbox((0, 0), "MANDANTE", font=f_tag)
        draw.text((home_logo_x + (logo_size - (bbox[2]-bbox[0]))//2, tag_y),
                  "MANDANTE", fill=TEXT_SECONDARY, font=f_tag)
        bbox = draw.textbbox((0, 0), "VISITANTE", font=f_tag)
        draw.text((away_logo_x + (logo_size - (bbox[2]-bbox[0]))//2, tag_y),
                  "VISITANTE", fill=TEXT_SECONDARY, font=f_tag)

        # === Percentual GIGANTE no centro ===
        pct_text = f"{fav_pct*100:.0f}"
        bbox = draw.textbbox((0, 0), pct_text, font=f_pct)
        pct_w = bbox[2] - bbox[0]
        sign_bbox = draw.textbbox((0, 0), "%", font=f_pct_sign)
        sign_w = sign_bbox[2] - sign_bbox[0]
        total_w = pct_w + sign_w + 6

        center_x = (card_x + card_w) // 2 + (card_x + 12) // 4 - total_w // 2 + 30
        # cálculo simples: centralizar entre os dois logos
        gap_left = home_logo_x + logo_size
        gap_right = away_logo_x
        pct_x = gap_left + ((gap_right - gap_left) - total_w) // 2
        pct_y = confronto_top + 12
        draw.text((pct_x, pct_y), pct_text, fill=GOLD, font=f_pct)
        draw.text((pct_x + pct_w + 6, pct_y + 30), "%", fill=GOLD, font=f_pct_sign)

        # Label "FAVORITO" abaixo do %
        fav_label = "FAVORITO"
        bbox = draw.textbbox((0, 0), fav_label, font=f_fav_label)
        flbl_x = pct_x + (total_w - (bbox[2]-bbox[0])) // 2
        draw.text((flbl_x, pct_y + 130), fav_label, fill=TEXT_SECONDARY, font=f_fav_label)

        # === Mini barra de progresso na base do card ===
        bar_y = cy + card_h - 26
        bar_x_left = card_x + 110
        bar_w_total = (card_x + card_w - 110) - bar_x_left
        bar_h_pix = 10
        draw.rounded_rectangle(
            [bar_x_left, bar_y, bar_x_left + bar_w_total, bar_y + bar_h_pix],
            radius=5, fill="#2a2a2a",
        )
        fill_w = int(bar_w_total * fav_pct)
        if fill_w > 8:
            draw.rounded_rectangle(
                [bar_x_left, bar_y, bar_x_left + fill_w, bar_y + bar_h_pix],
                radius=5, fill=GOLD,
            )

        y = cy + card_h + card_gap

    # ===== RODAPÉ =====
    footer_y = CARD_HEIGHT - 50
    draw.line([(60, footer_y - 10), (CARD_WIDTH - 60, footer_y - 10)], fill=ACCENT_GRAY, width=2)
    footer = "@SportRecifeLab  •  Análise de Dados"
    bbox = draw.textbbox((0, 0), footer, font=f_footer)
    fx = (CARD_WIDTH - (bbox[2] - bbox[0])) // 2
    draw.text((fx, footer_y), footer, fill=TEXT_SECONDARY, font=f_footer)

    img.save("pending_posts/2026-05-08_predicoes-r8/card_2_favoritos.png", quality=95)
    print("[OK] Card 2 (Favoritos) salvo")


if __name__ == "__main__":
    import os
    os.makedirs("pending_posts/2026-05-08_predicoes-r8", exist_ok=True)
    create_favoritos_card()
