"""
Gerador generico de card de heatmap para @SportRecifeLab.

Uso:
    python generate_heatmap_card.py \
        --heatmap habraao_heatmap_serie_b_2025.json \
        --name "HABRAAO" \
        --position "ZAGUEIRO" \
        --season "SERIE B 2025" \
        --matches 14 \
        --output card_habraao_heatmap.png

    # ou via Python:
    from generate_heatmap_card import generate_heatmap_card
    generate_heatmap_card(
        heatmap_path="habraao_heatmap_serie_b_2025.json",
        player_name="HABRAAO",
        position="ZAGUEIRO",
        season_label="SERIE B 2025",
        matches=14,
        output_path="card_habraao_heatmap.png",
    )
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from mplsoccer import VerticalPitch
from PIL import Image
import numpy as np

# ─── Paleta ──────────────────────────────────────────────────────────────────
BG           = "#0d0d0d"
PITCH_COLOR  = "#0e3d1f"
LINE_COLOR   = "#2a7a3a"
YELLOW       = "#F5C400"
GRAY         = "#666666"
LGRAY        = "#AAAAAA"
WHITE        = "#FFFFFF"

LOGO_PATH    = Path(__file__).parent / "sportrecifelab_avatar.png"


def generate_heatmap_card(
    heatmap_path: str | Path,
    player_name: str,
    position: str,
    season_label: str,
    matches: int,
    output_path: str | Path,
    heatmap_source: str = "per_match",
) -> Path:
    """Gera e salva o card de heatmap. Retorna o Path do arquivo salvo.

    heatmap_source:
      'per_match' — endpoint /event/{id}/player/{id}/heatmap: x=lateral, y=comprimento
      'season'    — endpoint /player/{id}/unique-tournament/.../heatmap: x=comprimento,
                    y=lateral invertido (100=esq, 0=dir)
    """

    # ── Carrega dados ─────────────────────────────────────────────────────────
    with open(heatmap_path, encoding="utf-8") as f:
        raw = json.load(f)

    # suporta tanto o JSON bruto do SofaScore quanto o salvo pelo extractor
    points = raw.get("points", raw) if isinstance(raw, dict) else raw

    if heatmap_source == "season":
        xs = np.array([(100 - p["y"]) * 0.8 for p in points])
        ys = np.array([p["x"] * 1.2 for p in points])
    else:
        xs = np.array([p["x"] * 0.8 for p in points])
        ys = np.array([p["y"] * 1.2 for p in points])
    counts = np.array([p.get("count", 1) for p in points], dtype=float)

    xs_exp = np.repeat(xs, counts.astype(int))
    ys_exp = np.repeat(ys, counts.astype(int))

    # ── Figura ────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(6.0, 8.5), dpi=120)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    pitch = VerticalPitch(
        pitch_type="statsbomb",
        pitch_color=PITCH_COLOR,
        line_color=LINE_COLOR,
        linewidth=1.0,
        goal_type="box",
        corner_arcs=True,
    )
    pitch.draw(ax=ax)
    ax.set_position([0.04, 0.07, 0.92, 0.80])

    pitch.kdeplot(
        xs_exp, ys_exp, ax=ax,
        cmap="YlOrRd",
        fill=True,
        alpha=0.62,
        levels=100,
        bw_adjust=1.4,
        zorder=2,
    )

    # ── Header ────────────────────────────────────────────────────────────────
    fig.text(0.50, 0.965, f"SPORT RECIFE  \u00b7  {season_label.split()[-1]}",
             color=YELLOW, fontsize=8.5, fontweight="bold",
             fontfamily="Franklin Gothic Heavy",
             ha="center", va="center")

    fig.text(0.50, 0.940, player_name.upper(),
             color=WHITE, fontsize=28, fontweight="black",
             fontfamily="Franklin Gothic Heavy",
             ha="center", va="center",
             path_effects=[pe.withStroke(linewidth=2, foreground=BG)])

    subtitle = f"MAPA DE CALOR  \u00b7  {position.upper()}  \u00b7  {season_label.upper()}  \u00b7  {matches}J"
    fig.text(0.50, 0.918, subtitle,
             color=LGRAY, fontsize=7.5, fontfamily="Arial",
             ha="center", va="center")

    # ── Footer ────────────────────────────────────────────────────────────────
    if LOGO_PATH.exists():
        logo_arr = np.array(
            Image.open(LOGO_PATH).convert("RGBA").resize((46, 46), Image.LANCZOS)
        )
        logo_ab = AnnotationBbox(
            OffsetImage(logo_arr, zoom=1.0),
            (0.09, 0.028),
            xycoords="figure fraction",
            frameon=False, zorder=10,
        )
        ax.add_artist(logo_ab)

    fig.text(0.175, 0.028, "@SportRecifeLab",
             color=YELLOW, fontsize=8.5, fontfamily="Franklin Gothic Heavy",
             fontweight="bold", ha="left", va="center")

    fig.text(0.97, 0.028, "Dados: SofaScore",
             color=GRAY, fontsize=7.2, fontfamily="Arial",
             ha="right", va="center")

    # ── Salvar ────────────────────────────────────────────────────────────────
    out = Path(output_path)
    plt.savefig(out, dpi=120, bbox_inches="tight",
                facecolor=BG, edgecolor="none")
    plt.close()
    return out


# ─── CLI ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera card de heatmap")
    parser.add_argument("--heatmap",  required=True, help="JSON com points do SofaScore")
    parser.add_argument("--name",     required=True, help="Nome do jogador (ex: HABRAAO)")
    parser.add_argument("--position", required=True, help="Posicao (ex: ZAGUEIRO)")
    parser.add_argument("--season",   required=True, help="Label da temporada (ex: SERIE B 2025)")
    parser.add_argument("--matches",  required=True, type=int, help="Numero de jogos")
    parser.add_argument("--output",   required=True, help="Caminho do PNG de saida")
    args = parser.parse_args()

    out = generate_heatmap_card(
        heatmap_path=args.heatmap,
        player_name=args.name,
        position=args.position,
        season_label=args.season,
        matches=args.matches,
        output_path=args.output,
    )
    print("Salvo:", out)
