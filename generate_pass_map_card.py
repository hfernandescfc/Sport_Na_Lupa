"""
Gerador generico de card de distribuicao de passes por zona para @SportRecifeLab.
Fonte: SofaScore (stats por temporada + heatmap por partida)

Uso:
    from generate_pass_map_card import generate_pass_map_card
    generate_pass_map_card(
        heatmap_path="habraao_heatmap_per_match.json",
        own_half_accurate=352, own_half_total=381,
        opp_half_accurate=171, opp_half_total=234,
        final_third_accurate=55,
        long_balls_accurate=31, long_balls_pct=42.5,
        total_passes=611, pass_pct=85.4,
        player_name="HABRAAO",
        position="ZAGUEIRO",
        season_label="SERIE B 2025",
        matches=14,
        output_path="card_habraao_passes.png",
    )
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from mplsoccer import VerticalPitch
from PIL import Image
import numpy as np

# ─── Paleta ──────────────────────────────────────────────────────────────────
BG          = "#0d0d0d"
PITCH_COLOR = "#0e3d1f"
LINE_COLOR  = "#2a7a3a"
YELLOW      = "#F5C400"
GRAY        = "#555555"
LGRAY       = "#AAAAAA"
WHITE       = "#FFFFFF"
BLUE_ZONE   = "#1a3a5c"
RED_ZONE    = "#5c1a1a"

LOGO_PATH   = Path(__file__).parent / "sportrecifelab_avatar.png"


def _pct_label(accurate: int, total: int) -> str:
    return f"{accurate / total * 100:.1f}%" if total else "—"


def generate_pass_map_card(
    heatmap_path: str | Path,
    own_half_accurate: int,
    own_half_total: int,
    opp_half_accurate: int,
    opp_half_total: int,
    final_third_accurate: int,
    long_balls_accurate: int,
    long_balls_pct: float,
    total_passes: int,
    pass_pct: float,
    player_name: str,
    position: str,
    season_label: str,
    matches: int,
    output_path: str | Path,
    final_third_stat_label: str = "passes certeiros",
    heatmap_source: str = "per_match",
) -> Path:
    # ── Carrega heatmap (proxy do posicionamento nos passes) ──────────────────
    # per_match: x=lateral (0=esq), y=comprimento (0=gol proprio)
    # season:    x=comprimento, y=lateral invertido (100=esq, 0=dir)
    with open(heatmap_path, encoding="utf-8") as f:
        raw = json.load(f)
    points = raw.get("points", raw) if isinstance(raw, dict) else raw
    if heatmap_source == "season":
        xs = np.array([(100 - p["y"]) * 0.8 for p in points])
        ys = np.array([p["x"] * 1.2 for p in points])
    else:
        xs = np.array([p["x"] * 0.8 for p in points])
        ys = np.array([p["y"] * 1.2 for p in points])

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

    # ── Zonas coloridas ───────────────────────────────────────────────────────
    pitch_left  = pitch.dim.left    # 0
    pitch_right = pitch.dim.right   # 80
    pitch_w     = pitch_right - pitch_left

    def zone_rect(x0, x1, color, alpha):
        rect = mpatches.FancyBboxPatch(
            (pitch_left, x0), pitch_w, x1 - x0,
            boxstyle="square,pad=0",
            facecolor=color, edgecolor="none", alpha=alpha, zorder=2,
        )
        ax.add_patch(rect)

    zone_rect(0,  60,  "#0d2a4a", 0.55)   # campo próprio — azul escuro
    zone_rect(60, 80,  "#1a3d20", 0.40)   # meio campo adversário — verde médio
    zone_rect(80, 120, "#4a1a0d", 0.55)   # terço final — vermelho escuro

    # ── KDE suave por cima das zonas ─────────────────────────────────────────
    pitch.kdeplot(
        xs, ys, ax=ax,
        cmap="Blues",
        fill=True,
        alpha=0.22,
        levels=50,
        bw_adjust=0.7,
        zorder=3,
    )

    # ── Linhas divisórias de zona ─────────────────────────────────────────────
    for x_line, label in [(60, "MEIO-CAMPO"), (80, "TERCO FINAL")]:
        ax.plot(
            [pitch_left, pitch_right], [x_line, x_line],
            color=YELLOW, linewidth=1.0, linestyle="--", alpha=0.50, zorder=4,
        )
        ax.text(pitch_left + 1, x_line + 1.2, label,
                color=YELLOW, fontsize=5.5, fontfamily="Arial", fontweight="bold",
                alpha=0.70, va="bottom", zorder=5)

    # ── Labels das zonas (caixas com fundo escuro) ────────────────────────────
    cx = (pitch_left + pitch_right) / 2

    BBOX_STYLE = dict(
        boxstyle="round,pad=0.5",
        facecolor="#000000",
        edgecolor=YELLOW,
        alpha=0.78,
        linewidth=0.8,
    )

    def zone_label(x_center, title, acc, total, extra=""):
        pct = _pct_label(acc, total)
        lines = [title, f"{acc} passes  |  {pct} precisao"]
        if extra:
            lines.append(extra)
        text = "\n".join(lines)
        ax.text(cx, x_center, text,
                color=WHITE, fontsize=7.8, fontfamily="Franklin Gothic Heavy",
                ha="center", va="center", zorder=6,
                linespacing=1.6,
                bbox=BBOX_STYLE,
                multialignment="center")
        # linha amarela no título
        ax.text(cx, x_center + (3.0 if not extra else 4.0), title,
                color=YELLOW, fontsize=7.2, fontfamily="Franklin Gothic Heavy",
                fontweight="bold", ha="center", va="center", zorder=7,
                alpha=0.0)  # invisível — só para forçar bbox height

    # zona própria
    ax.text(cx, 30,
            f"CAMPO PROPRIO\n{own_half_accurate} de {own_half_total} passes  |  {_pct_label(own_half_accurate, own_half_total)} precisao",
            color=WHITE, fontsize=8, fontfamily="Franklin Gothic Heavy",
            ha="center", va="center", zorder=6,
            linespacing=1.7, multialignment="center",
            bbox=BBOX_STYLE)
    ax.text(cx, 30 + 5.5, "CAMPO PROPRIO",
            color=YELLOW, fontsize=7, fontfamily="Franklin Gothic Heavy",
            fontweight="bold", ha="center", va="center", zorder=7)

    # zona adversária
    ax.text(cx, 69,
            f"CAMPO ADVERSARIO\n{opp_half_accurate} de {opp_half_total} passes  |  {_pct_label(opp_half_accurate, opp_half_total)} precisao",
            color=WHITE, fontsize=8, fontfamily="Franklin Gothic Heavy",
            ha="center", va="center", zorder=6,
            linespacing=1.7, multialignment="center",
            bbox=BBOX_STYLE)
    ax.text(cx, 69 + 5.5, "CAMPO ADVERSARIO",
            color=YELLOW, fontsize=7, fontfamily="Franklin Gothic Heavy",
            fontweight="bold", ha="center", va="center", zorder=7)

    # terço final
    ax.text(cx, 100,
            f"TERCO FINAL\n{final_third_accurate} {final_third_stat_label}\nBolas longas: {long_balls_accurate} ({long_balls_pct:.1f}%)",
            color=WHITE, fontsize=7.5, fontfamily="Franklin Gothic Heavy",
            ha="center", va="center", zorder=6,
            linespacing=1.7, multialignment="center",
            bbox=BBOX_STYLE)
    ax.text(cx, 100 + 6.5, "TERCO FINAL",
            color=YELLOW, fontsize=7, fontfamily="Franklin Gothic Heavy",
            fontweight="bold", ha="center", va="center", zorder=7)

    # ── Resumo geral ──────────────────────────────────────────────────────────
    ax.text(cx, -6,
            f"TOTAL: {total_passes} passes  |  {pass_pct:.1f}% precisao geral",
            color=WHITE, fontsize=7.5, fontfamily="Franklin Gothic Heavy",
            ha="center", va="center", zorder=6,
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#000000",
                      edgecolor=GRAY, alpha=0.75, linewidth=0.6))

    # ── Header ────────────────────────────────────────────────────────────────
    fig.text(0.50, 0.965, f"SPORT RECIFE  \u00b7  {season_label.split()[-1]}",
             color=YELLOW, fontsize=8.5, fontweight="bold",
             fontfamily="Franklin Gothic Heavy", ha="center", va="center")

    fig.text(0.50, 0.940, player_name.upper(),
             color=WHITE, fontsize=28, fontweight="black",
             fontfamily="Franklin Gothic Heavy", ha="center", va="center",
             path_effects=[pe.withStroke(linewidth=2, foreground=BG)])

    fig.text(0.50, 0.918,
             f"PASSES POR ZONA DE ORIGEM  \u00b7  {position.upper()}  \u00b7  {season_label.upper()}  \u00b7  {matches}J",
             color=LGRAY, fontsize=7.5, fontfamily="Arial",
             ha="center", va="center")

    # ── Footer ────────────────────────────────────────────────────────────────
    if LOGO_PATH.exists():
        logo_arr = np.array(
            Image.open(LOGO_PATH).convert("RGBA").resize((46, 46), Image.LANCZOS)
        )
        ax.add_artist(AnnotationBbox(
            OffsetImage(logo_arr, zoom=1.0), (0.09, 0.028),
            xycoords="figure fraction", frameon=False, zorder=10,
        ))

    fig.text(0.175, 0.028, "@SportRecifeLab",
             color=YELLOW, fontsize=8.5, fontfamily="Franklin Gothic Heavy",
             fontweight="bold", ha="left", va="center")

    fig.text(0.97, 0.028, "Dados: SofaScore  \u00b7  mapa = posicionamento do jogador  \u00b7  zonas = de onde o passe partiu",
             color=GRAY, fontsize=6.2, fontfamily="Arial",
             ha="right", va="center")

    # ── Salvar ────────────────────────────────────────────────────────────────
    out = Path(output_path)
    plt.savefig(out, dpi=120, bbox_inches="tight",
                facecolor=BG, edgecolor="none")
    plt.close()
    return out


# ─── CLI / execução direta ───────────────────────────────────────────────────
if __name__ == "__main__":
    out = generate_pass_map_card(
        heatmap_path="habraao_heatmap_per_match.json",
        own_half_accurate=352, own_half_total=381,
        opp_half_accurate=171, opp_half_total=234,
        final_third_accurate=55,
        long_balls_accurate=31, long_balls_pct=42.47,
        total_passes=611, pass_pct=85.4,
        player_name="HABRAAO",
        position="ZAGUEIRO",
        season_label="SERIE B 2025",
        matches=14,
        output_path="card_habraao_passes.png",
    )
    print("Salvo:", out)
