"""xG por Estado de Jogo — Série B 2026.

Para cada chute no shotmap, reconstrói o placar vigente naquele minuto
usando os incidentes de gol. Classifica o estado do time que chutou:
  - vencendo  → team_score > opp_score
  - empatando → team_score == opp_score
  - perdendo  → team_score < opp_score

Sem argumentos: gera card "xG em Situação Neutra" (foco em empatando).
--all-states: gera card com as 3 situações empilhadas.
"""

from __future__ import annotations

import argparse
import json
import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
import numpy as np
import pandas as pd
from PIL import Image

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent
SHOTMAP_PATH  = ROOT / "data/processed/2026/shotmaps/serie_b_shotmaps.json"
INCIDENT_B    = ROOT / "data/processed/2026/incidents/serie_b_incidents.json"
INCIDENT_SPT  = ROOT / "data/processed/2026/incidents/sport_incidents.json"
STRENGTH_PATH = ROOT / "data/processed/2026/matches/serie_b_2026_team_strength.csv"
LOGO_CACHE    = ROOT / "data/cache/logos"
AVATAR_PATH   = ROOT / "sportrecifelab_avatar.png"
OUT_PATH      = ROOT / "pending_posts"

# ---------------------------------------------------------------------------
# Paleta SportRecifeLab
# ---------------------------------------------------------------------------
BG           = "#0d0d0d"
GOLD         = "#F5C400"
GOLD_LEVEL   = "#c9a800"
GOLD_DARK    = "#7a6200"
GREEN_WIN    = "#2d8a4e"
RED_LOSS     = "#c0392b"
TEXT_COLOR   = "#e8e8e8"
SUBTEXT      = "#888888"
ROW_ALT      = "#131313"

# ---------------------------------------------------------------------------
# Mapeamento time → sofascore_team_id
# ---------------------------------------------------------------------------
def _load_team_ids() -> dict[str, int]:
    if not STRENGTH_PATH.exists():
        return {}
    df = pd.read_csv(STRENGTH_PATH)
    return {row["team_key"]: int(row["sofascore_team_id"]) for _, row in df.iterrows()}

TEAM_IDS: dict[str, int] = {}  # preenchido em main()

# ---------------------------------------------------------------------------
# Mapeamento nome raw → team_key (mesma lógica de normalize)
# ---------------------------------------------------------------------------
_NAME_TO_KEY = {
    "América Mineiro":       "america-mg",
    "Athletic Club":         "athletic-club",
    "Atlético Goianiense":   "atletico-go",
    "Avaí":                  "avai",
    "Botafogo-SP":           "botafogo-sp",
    "CRB":                   "crb",
    "Ceará":                 "ceara",
    "Criciúma":              "criciuma",
    "Cuiabá":                "cuiaba",
    "Fortaleza":             "fortaleza",
    "Goiás":                 "goias",
    "Grêmio Novorizontino":  "novorizontino",
    "Juventude":             "juventude",
    "Londrina":              "londrina",
    "Náutico":               "nautico",
    "Operário-PR":           "operario-pr",
    "Ponte Preta":           "ponte-preta",
    "Sport Recife":          "sport",
    "São Bernardo":          "sao-bernardo",
    "Vila Nova FC":          "vila-nova",
}

_KEY_DISPLAY = {
    "america-mg":    "América Mineiro",
    "athletic-club": "Athletic Club",
    "atletico-go":   "Atlético-GO",
    "avai":          "Avaí",
    "botafogo-sp":   "Botafogo-SP",
    "crb":           "CRB",
    "ceara":         "Ceará",
    "criciuma":      "Criciúma",
    "cuiaba":        "Cuiabá",
    "fortaleza":     "Fortaleza",
    "goias":         "Goiás",
    "novorizontino": "Novorizontino",
    "juventude":     "Juventude",
    "londrina":      "Londrina",
    "nautico":       "Náutico",
    "operario-pr":   "Operário-PR",
    "ponte-preta":   "Ponte Preta",
    "sport":         "Sport Recife",
    "sao-bernardo":  "São Bernardo",
    "vila-nova":     "Vila Nova FC",
}


# ---------------------------------------------------------------------------
# Logo helpers
# ---------------------------------------------------------------------------
def _remove_bg_floodfill(img: Image.Image, thresh: int = 30) -> Image.Image:
    img = img.convert("RGBA")
    data = np.array(img)
    h, w = data.shape[:2]
    visited = np.zeros((h, w), dtype=bool)
    queue: list[tuple[int, int]] = []
    for x in range(w):
        queue += [(0, x), (h - 1, x)]
    for y in range(h):
        queue += [(y, 0), (y, w - 1)]
    while queue:
        y, x = queue.pop()
        if visited[y, x]:
            continue
        visited[y, x] = True
        r, g, b, a = data[y, x]
        if a < 10 or (r > 255 - thresh and g > 255 - thresh and b > 255 - thresh):
            data[y, x, 3] = 0
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx]:
                    queue.append((ny, nx))
    return Image.fromarray(data)


def _get_logo(team_key: str, size: int = 48) -> np.ndarray | None:
    team_id = TEAM_IDS.get(team_key)
    if not team_id:
        return None
    path = LOGO_CACHE / f"{team_id}.png"
    if not path.exists():
        return None
    try:
        img = Image.open(path).convert("RGBA")
        img = _remove_bg_floodfill(img)
        img = img.resize((size, size), Image.LANCZOS)
        return np.array(img)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 1. Carregar timelines de gol
# ---------------------------------------------------------------------------
def load_goal_timelines() -> dict[int, list[tuple[int, int, int]]]:
    timelines: dict[int, list[tuple[int, int, int]]] = {}

    def _process(path: Path) -> None:
        if not path.exists():
            return
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        for match in raw.get("matches", []):
            eid = int(match["event_id"])
            goals = []
            for inc in match.get("incidents", []):
                if inc.get("incidentType") != "goal":
                    continue
                if inc.get("incidentClass") in ("goalNotAwarded",):
                    continue
                goals.append((
                    int(inc.get("time", 0) or 0),
                    int(inc.get("homeScore", 0) or 0),
                    int(inc.get("awayScore", 0) or 0),
                ))
            goals.sort(key=lambda x: x[0])
            if eid not in timelines or len(goals) > len(timelines[eid]):
                timelines[eid] = goals

    _process(INCIDENT_B)
    _process(INCIDENT_SPT)
    return timelines


# ---------------------------------------------------------------------------
# 2. Estado de jogo por chute
# ---------------------------------------------------------------------------
def game_state_at(minute: int, is_home: bool,
                  timeline: list[tuple[int, int, int]]) -> str:
    h, a = 0, 0
    for (g_min, h_s, a_s) in timeline:
        if g_min < minute:
            h, a = h_s, a_s
        else:
            break
    team, opp = (h, a) if is_home else (a, h)
    if team > opp:
        return "vencendo"
    elif team < opp:
        return "perdendo"
    return "empatando"


# ---------------------------------------------------------------------------
# 3. Agregar xG
# ---------------------------------------------------------------------------
def build_xg_by_state(shotmap: list[dict],
                      timelines: dict[int, list]) -> pd.DataFrame:
    records = []
    for shot in shotmap:
        xg = shot.get("xg") or 0.0
        if xg <= 0:
            continue
        eid      = int(shot["event_id"])
        minute   = int(shot.get("minute") or 0)
        is_home  = bool(shot.get("is_home"))
        team_raw = shot.get("team_name", "Unknown")
        team_key = _NAME_TO_KEY.get(team_raw, team_raw.lower().replace(" ", "-"))
        records.append({"team_key": team_key, "state": game_state_at(minute, is_home, timelines.get(eid, [])), "xg": xg})

    df = pd.DataFrame(records)
    if df.empty:
        return df

    pivot = df.groupby(["team_key", "state"])["xg"].sum().unstack(fill_value=0.0)
    for col in ["vencendo", "empatando", "perdendo"]:
        if col not in pivot.columns:
            pivot[col] = 0.0
    pivot["total"] = pivot[["vencendo", "empatando", "perdendo"]].sum(axis=1)
    pivot["pct_neutro"] = (pivot["empatando"] / pivot["total"] * 100).round(1)
    return pivot.reset_index()


# ---------------------------------------------------------------------------
# 4a. Card "xG em Situação Neutra" (foco em empatando)
# ---------------------------------------------------------------------------
def generate_neutral_card(pivot: pd.DataFrame, round_label: str,
                           out_file: Path) -> None:
    df = pivot.sort_values("empatando", ascending=False).reset_index(drop=True)
    n  = len(df)

    # Dimensões: margem esquerda larga para rank + logo + nome
    fig_w   = 11.0
    row_h   = 0.60          # altura por linha em polegadas
    pad_top = 1.2           # espaço para título
    pad_bot = 0.9           # espaço para eixo X + rodapé
    fig_h   = n * row_h + pad_top + pad_bot

    fig = plt.figure(figsize=(fig_w, fig_h), facecolor=BG)

    # Margens em fração da figura
    ml = 0.28               # espaço para rank + logo + nome
    mr = 0.02
    mb = pad_bot / fig_h
    mt = pad_top / fig_h
    ax = fig.add_axes([ml, mb, 1 - ml - mr, 1 - mt - mb])
    ax.set_facecolor(BG)

    bar_h  = 0.52
    y_pos  = np.arange(n - 1, -1, -1, dtype=float)  # 19 → 0
    max_xg = df["empatando"].max()
    x_max  = max_xg * 1.22   # espaço para valor + pct à direita

    # ── Limites do eixo ──────────────────────────────────────────────────
    ax.set_xlim(0, x_max)
    ax.set_ylim(y_pos[-1] - 0.6, y_pos[0] + 0.6)

    # ── Grade vertical sutil ──────────────────────────────────────────────
    for gv in np.arange(1.0, max_xg + 0.5, 1.0):
        ax.axvline(gv, color="#1c1c1c", lw=0.8, zorder=0)

    # ── Faixas alternadas ─────────────────────────────────────────────────
    for i, y in enumerate(y_pos):
        if i % 2 == 1:
            ax.barh(y, x_max, height=1.0, left=0,
                    color="#0f0f0f", zorder=0, linewidth=0)

    # ── Barras + anotações ───────────────────────────────────────────────
    for i, row in df.iterrows():
        y      = y_pos[i]
        xg_val = row["empatando"]
        pct    = row["pct_neutro"]
        key    = row["team_key"]
        is_spt = key == "sport"

        rank_frac = 1.0 - i / max(n - 1, 1)
        bar_color = GOLD if is_spt else _gold_shade(rank_frac)

        if is_spt:
            ax.barh(y, xg_val, height=bar_h + 0.22,
                    color=GOLD, alpha=0.10, zorder=1, linewidth=0)

        ax.barh(y, xg_val, height=bar_h, color=bar_color,
                zorder=2, linewidth=0)

        if is_spt:
            ax.add_patch(FancyBboxPatch(
                (0, y - bar_h / 2 - 0.08), xg_val, bar_h + 0.16,
                boxstyle="square,pad=0.0",
                linewidth=1.8, edgecolor=GOLD,
                facecolor="none", zorder=6,
            ))

        # Valor xG
        ax.text(xg_val + max_xg * 0.016, y,
                f"{xg_val:.2f}",
                va="center", ha="left", fontsize=9,
                color=GOLD if is_spt else TEXT_COLOR,
                fontweight="bold" if is_spt else "normal", zorder=7)

        # % do total
        ax.text(xg_val + max_xg * 0.115, y,
                f"{pct:.0f}%",
                va="center", ha="left", fontsize=7.5,
                color=SUBTEXT, zorder=7)

    # ── Cabeçalhos de colunas (no topo do eixo de dados) ─────────────────
    top_y = y_pos[0] + 0.58
    ax.text(max_xg * 0.062, top_y, "xG",
            va="bottom", ha="left", fontsize=7.5, color=SUBTEXT)
    ax.text(max_xg * 0.158, top_y, "% total",
            va="bottom", ha="left", fontsize=7.5, color=SUBTEXT)

    ax.set_yticks([])
    ax.tick_params(axis="x", colors=SUBTEXT, labelsize=8, length=3)
    ax.set_xlabel("xG acumulado (placar neutro)", fontsize=8.5,
                  color=SUBTEXT, labelpad=6)
    for sp in ["top", "right", "left"]:
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color("#2a2a2a")

    # ── Rank + Logo + Nome na margem esquerda ─────────────────────────────
    # Convertemos y de dados → fração da figura
    ylim_lo = y_pos[-1] - 0.6
    ylim_hi = y_pos[0]  + 0.6
    ax_h_fig = 1 - mt - mb

    def _row_fig_y(y_data: float) -> float:
        frac = (y_data - ylim_lo) / (ylim_hi - ylim_lo)
        return mb + frac * ax_h_fig

    # Posições X (em fração figura) para cada coluna da margem
    X_RANK = 0.015
    X_LOGO = 0.065   # centro do logo (36px ≈ 0.036 frac em 11in@150dpi)
    X_NAME = 0.115   # início do nome

    logo_size_frac = 0.034  # altura em fração figura (~36px @ fig_h)
    logo_w_frac    = logo_size_frac * (fig_h / fig_w)

    for i, row in df.iterrows():
        y      = y_pos[i]
        key    = row["team_key"]
        name   = _KEY_DISPLAY.get(key, key)
        is_spt = key == "sport"
        rank   = i + 1
        fy     = _row_fig_y(y)

        # Ranking
        fig.text(X_RANK, fy, f"{rank}",
                 ha="left", va="center",
                 fontsize=8, color=GOLD if is_spt else SUBTEXT,
                 fontweight="bold" if is_spt else "normal")

        # Escudo
        logo_arr = _get_logo(key, size=56)
        if logo_arr is not None:
            lax = fig.add_axes([
                X_LOGO - logo_w_frac / 2,
                fy - logo_size_frac / 2,
                logo_w_frac,
                logo_size_frac,
            ])
            lax.imshow(logo_arr)
            lax.axis("off")

        # Nome
        fig.text(X_NAME, fy, name,
                 ha="left", va="center",
                 fontsize=9 if is_spt else 8.5,
                 color=GOLD if is_spt else TEXT_COLOR,
                 fontweight="bold" if is_spt else "normal")

    # ── Separador vertical (linha divisória margem / barras) ─────────────
    fig.add_artist(plt.Line2D([ml - 0.004, ml - 0.004],
                              [mb, 1 - mt],
                              transform=fig.transFigure,
                              color="#222222", lw=1.2, zorder=0))

    # ── Título ───────────────────────────────────────────────────────────
    fig.text(0.5, 0.985,
             "xG EM SITUAÇÃO NEUTRA",
             ha="center", va="top",
             fontsize=16, fontweight="bold", color=GOLD)
    fig.text(0.5, 0.966,
             f"Série B 2026  ·  {round_label}  ·  xG criado quando o placar estava empatado",
             ha="center", va="top", fontsize=8.5, color=SUBTEXT)

    # ── Rodapé ───────────────────────────────────────────────────────────
    if AVATAR_PATH.exists():
        try:
            av  = Image.open(AVATAR_PATH).convert("RGBA")
            lax = fig.add_axes([0.015, 0.006, 0.038, 0.038])
            lax.imshow(np.array(av))
            lax.axis("off")
        except Exception:
            pass
    fig.text(0.062, 0.016, "@SportRecifeLab",
             ha="left", va="center", fontsize=7.5,
             color=SUBTEXT, fontstyle="italic")
    fig.text(0.985, 0.016, "Fonte: SofaScore",
             ha="right", va="center", fontsize=7, color="#444444")

    out_file.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_file, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"[OK] Card salvo: {out_file}")


# ---------------------------------------------------------------------------
# 4b. Card com 3 estados (legado)
# ---------------------------------------------------------------------------
def generate_all_states_card(pivot: pd.DataFrame, round_label: str,
                              out_file: Path) -> None:
    df = pivot.sort_values("total", ascending=True).reset_index(drop=True)
    n  = len(df)

    fig_h = max(10.0, n * 0.52 + 3.2)
    fig, ax = plt.subplots(figsize=(11, fig_h), facecolor=BG)
    ax.set_facecolor(BG)

    bar_h = 0.46
    y_pos = np.arange(n)
    max_xg = pivot["total"].max()

    for gv in np.arange(0, max_xg + 2, 2):
        ax.axvline(gv, color="#222222", lw=0.6, zorder=0)

    for i, row in df.iterrows():
        y       = y_pos[i]
        xg_e    = row["empatando"]
        xg_v    = row["vencendo"]
        xg_p    = row["perdendo"]
        tot     = row["total"]
        key     = row["team_key"]
        is_spt  = key == "sport"

        ax.barh(y, xg_e, height=bar_h, left=0, color=GOLD_LEVEL, zorder=2)
        ax.barh(y, xg_v, height=bar_h, left=xg_e, color=GREEN_WIN, zorder=2)
        ax.barh(y, xg_p, height=bar_h, left=xg_e + xg_v, color=RED_LOSS, zorder=2)

        if is_spt:
            rect = FancyBboxPatch((-0.04, y - bar_h / 2 - 0.04),
                                  tot + 0.12, bar_h + 0.08,
                                  boxstyle="round,pad=0.02",
                                  linewidth=1.4, edgecolor=GOLD,
                                  facecolor="none", zorder=5)
            ax.add_patch(rect)

        min_lbl = 1.5
        if xg_e >= min_lbl:
            ax.text(xg_e / 2, y, f"{xg_e:.1f}", va="center", ha="center",
                    fontsize=6.5, color="#1a1a1a", fontweight="bold", zorder=7)
        if xg_v >= min_lbl:
            ax.text(xg_e + xg_v / 2, y, f"{xg_v:.1f}", va="center", ha="center",
                    fontsize=6.5, color="#e8e8e8", fontweight="bold", zorder=7)
        if xg_p >= min_lbl:
            ax.text(xg_e + xg_v + xg_p / 2, y, f"{xg_p:.1f}", va="center", ha="center",
                    fontsize=6.5, color="#e8e8e8", fontweight="bold", zorder=7)

        ax.text(tot + max_xg * 0.012, y, f"{tot:.1f}",
                va="center", ha="left", fontsize=7.5,
                color=TEXT_COLOR, fontweight="bold", zorder=6)

    display_names = [_KEY_DISPLAY.get(r["team_key"], r["team_key"])
                     for _, r in df.iterrows()]
    ax.set_yticks(y_pos)
    ax.set_yticklabels(display_names, fontsize=8.5, color=TEXT_COLOR)
    ax.tick_params(axis="y", length=0, pad=6)
    ax.tick_params(axis="x", colors=SUBTEXT, labelsize=7.5)
    ax.set_xlim(0, max_xg * 1.12)
    ax.set_xlabel("xG acumulado", fontsize=8, color=SUBTEXT, labelpad=6)
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#333333")

    patches = [mpatches.Patch(color=GOLD_LEVEL, label="Empatando"),
               mpatches.Patch(color=GREEN_WIN,  label="Vencendo"),
               mpatches.Patch(color=RED_LOSS,   label="Perdendo")]
    ax.legend(handles=patches, loc="lower right", frameon=True,
              framealpha=0.15, edgecolor="#444444",
              fontsize=8, labelcolor=TEXT_COLOR, ncol=3)

    fig.text(0.5, 0.975, "xG POR ESTADO DE JOGO",
             ha="center", va="top", fontsize=15, fontweight="bold", color=GOLD)
    fig.text(0.5, 0.959,
             f"Série B 2026 · {round_label} · xG criado quando vencendo / empatando / perdendo",
             ha="center", va="top", fontsize=8, color=SUBTEXT)

    if AVATAR_PATH.exists():
        try:
            av   = Image.open(AVATAR_PATH).convert("RGBA")
            l_ax = fig.add_axes([0.02, 0.005, 0.055, 0.055])
            l_ax.imshow(np.array(av))
            l_ax.axis("off")
        except Exception:
            pass
    fig.text(0.085, 0.018, "@SportRecifeLab",
             ha="left", va="center", fontsize=7.5, color=SUBTEXT, fontstyle="italic")
    fig.text(0.98, 0.018, "Fonte: SofaScore",
             ha="right", va="center", fontsize=7, color="#555555")

    plt.tight_layout(rect=[0, 0.03, 1, 0.965])
    out_file.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_file, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"[OK] Card salvo: {out_file}")


# ---------------------------------------------------------------------------
# Utilitário de cor
# ---------------------------------------------------------------------------
def _gold_shade(frac: float) -> str:
    """Interpola entre ouro escuro e ouro médio conforme ranking (0=last, 1=1st)."""
    r0, g0, b0 = 0x7a, 0x62, 0x00   # GOLD_DARK
    r1, g1, b1 = 0xc9, 0xa8, 0x00   # GOLD_LEVEL
    r = int(r0 + (r1 - r0) * frac)
    g = int(g0 + (g1 - g0) * frac)
    b = int(b0 + (b1 - b0) * frac)
    return f"#{r:02x}{g:02x}{b:02x}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    global TEAM_IDS

    parser = argparse.ArgumentParser()
    parser.add_argument("--all-states", action="store_true",
                        help="Gera card com as 3 situações empilhadas")
    args = parser.parse_args()

    TEAM_IDS = _load_team_ids()

    print("Carregando shotmaps...")
    with open(SHOTMAP_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    all_shots  = [s for m in raw["matches"] for s in m["shots"]]
    max_round  = max(m["round"] for m in raw["matches"])
    print(f"  {len(all_shots)} chutes · R1–R{max_round}")

    print("Carregando timelines de gol...")
    timelines = load_goal_timelines()
    print(f"  {len(timelines)} partidas com dados de gol")

    print("Calculando xG por estado de jogo...")
    pivot = build_xg_by_state(all_shots, timelines)

    print("\nResumo (empatando):")
    print(
        pivot[["team_key", "empatando", "pct_neutro", "total"]]
        .sort_values("empatando", ascending=False)
        .to_string(index=False, float_format="{:.2f}".format)
    )

    round_label = f"R1–R{max_round}"
    date_str    = datetime.date.today().isoformat()

    if args.all_states:
        slug     = f"{date_str}_xg-estado-jogo-r{max_round}"
        out_file = OUT_PATH / slug / "card_all_states.png"
        generate_all_states_card(pivot, round_label, out_file)
    else:
        slug     = f"{date_str}_xg-estado-jogo-r{max_round}"
        out_file = OUT_PATH / slug / "card.png"
        generate_neutral_card(pivot, round_label, out_file)


if __name__ == "__main__":
    main()
