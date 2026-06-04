"""
generate_xg_xga_scatter_card.py
Scatter: saldo xG e xGA de cada time (Real - Esperado pelo calendário).
Paleta SportRecifeLab — fundo #0d0d0d, amarelo #F5C400.
"""

import os, datetime
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from PIL import Image

# ── paths ────────────────────────────────────────────────────────────────────
BASE       = os.path.dirname(os.path.abspath(__file__))
LOGOS_DIR  = os.path.join(BASE, "data", "cache", "logos")
STATS_CSV  = os.path.join(BASE, "data", "curated", "serie_b_2026", "team_match_stats.csv")
AVATAR     = os.path.join(BASE, "sportrecifelab_avatar.png")
OUT_DIR    = os.path.join(BASE, "pending_posts")

# ── team_key → sofascore_id ──────────────────────────────────────────────────
TEAM_ID = {
    "america-mg": 1973,    "athletic-club": 342775, "atletico-go": 7314,
    "avai": 7315,          "botafogo-sp": 1979,     "ceara": 2001,
    "crb": 22032,          "criciuma": 1984,         "cuiaba": 49202,
    "fortaleza": 2020,     "goias": 1960,            "juventude": 1980,
    "londrina": 2022,      "nautico": 2011,           "novorizontino": 135514,
    "operario-pr": 39634,  "ponte-preta": 1969,      "sao-bernardo": 47504,
    "sport": 1959,         "vila-nova": 2021,
}

DISPLAY_NAMES = {
    "america-mg": "América-MG",    "athletic-club": "Athletic Club",
    "atletico-go": "Atlético-GO",  "avai": "Avaí",
    "botafogo-sp": "Botafogo-SP",   "ceara": "Ceará",
    "crb": "CRB",                   "criciuma": "Criciúma",
    "cuiaba": "Cuiabá",             "fortaleza": "Fortaleza",
    "goias": "Goiás",               "juventude": "Juventude",
    "londrina": "Londrina",         "nautico": "Náutico",
    "novorizontino": "Nov'tino",    "operario-pr": "Operário-PR",
    "ponte-preta": "Ponte Preta",   "sao-bernardo": "São Bernardo",
    "sport": "Sport Recife",        "vila-nova": "Vila Nova",
}

# ── label offsets (data units) to separate crowded points ───────────────────
LABEL_OFFSETS = {
    # right cluster
    "criciuma":      (+0.020, +0.055),   # above-right  (now top after Y inversion)
    "ceara":         (+0.020, +0.055),   # above-right
    "atletico-go":   (+0.020, -0.065),   # below-right
    "botafogo-sp":   (-0.020, +0.055),   # above-left
    "crb":           (-0.020, -0.065),   # below-left
    "vila-nova":     (+0.020, +0.055),   # above-right
    "nautico":       (-0.020, +0.055),   # above-left
    "novorizontino": (-0.020, +0.055),   # above-left
    # mid cluster
    "ponte-preta":   (+0.020, -0.065),
    "america-mg":    (-0.020, +0.055),
    "cuiaba":        (+0.020, +0.055),
    "goias":         (-0.020, +0.055),
    "sao-bernardo":  (+0.020, -0.065),
    "athletic-club": (-0.020, +0.055),
    "avai":          (-0.020, -0.065),
    "operario-pr":   (-0.020, -0.065),
    "fortaleza":     (-0.020, +0.055),
    "londrina":      (+0.020, -0.065),
    "juventude":     (+0.020, +0.055),
}

# ── colors ───────────────────────────────────────────────────────────────────
BG         = "#0d0d0d"
GOLD       = "#F5C400"
GRAY_DIM   = "#2e2e2e"
GRAY_MID   = "#5a5a5a"
GRAY_LIGHT = "#9a9a9a"
WHITE      = "#e8e8e8"

plt.rcParams.update({
    "font.family":    "Franklin Gothic Heavy",
    "text.color":     WHITE,
    "axes.facecolor": BG,
    "figure.facecolor": BG,
})


# ─────────────────────────────────────────────────────────────────────────────
def _remove_bg_floodfill(img: Image.Image, thresh: int = 25) -> Image.Image:
    img = img.convert("RGBA")
    arr = np.array(img, dtype=np.int32)
    h, w = arr.shape[:2]
    visited = np.zeros((h, w), dtype=bool)
    seeds = (
        [(0, c) for c in range(w)] + [(h - 1, c) for c in range(w)] +
        [(r, 0) for r in range(h)] + [(r, w - 1) for r in range(h)]
    )
    stack = []
    for r, c in seeds:
        if not visited[r, c]:
            px = arr[r, c]
            if px[3] > 0 and all(abs(int(px[i]) - 255) < thresh for i in range(3)):
                stack.append((r, c))
                visited[r, c] = True
    while stack:
        r, c = stack.pop()
        arr[r, c, 3] = 0
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w and not visited[nr, nc]:
                px = arr[nr, nc]
                if px[3] > 0 and all(abs(int(px[i]) - 255) < thresh for i in range(3)):
                    visited[nr, nc] = True
                    stack.append((nr, nc))
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def _logo_image(team_key: str, size: int = 32) -> OffsetImage | None:
    tid = TEAM_ID.get(team_key)
    if not tid:
        return None
    path = os.path.join(LOGOS_DIR, f"{tid}.png")
    if not os.path.exists(path):
        return None
    try:
        img = Image.open(path).convert("RGBA")
        img = _remove_bg_floodfill(img)
        img.thumbnail((size, size), Image.LANCZOS)
        return OffsetImage(np.array(img), zoom=1.0)
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
def _build_data() -> pd.DataFrame:
    df = pd.read_csv(STATS_CSV)
    stats = df[["match_code", "team_key", "expected_goals"]].copy()
    opp = stats.rename(columns={"team_key": "opp_key", "expected_goals": "opp_xg"})
    joined = stats.merge(opp, on="match_code")
    joined = joined[joined["team_key"] != joined["opp_key"]]

    actual = joined.groupby("team_key").agg(
        xg_actual=("expected_goals", "mean"),
        xga_actual=("opp_xg", "mean"),
    ).reset_index()

    team_avg = actual.rename(columns={
        "team_key": "opp_key", "xg_actual": "opp_avg_xg", "xga_actual": "opp_avg_xga"
    })
    expected = joined.merge(team_avg, on="opp_key").groupby("team_key").agg(
        xg_expected=("opp_avg_xga", "mean"),
        xga_expected=("opp_avg_xg", "mean"),
    ).reset_index()

    result = actual.merge(expected, on="team_key")
    result["xg_delta"]  = (result["xg_actual"]  - result["xg_expected"]).round(3)
    # negated so that positive Y = better defense (top-right = best quadrant)
    result["xga_delta"] = -(result["xga_actual"] - result["xga_expected"]).round(3)
    result["display"]   = result["team_key"].map(DISPLAY_NAMES)
    result["rounds"]    = df["round"].nunique()
    return result


# ─────────────────────────────────────────────────────────────────────────────
def _draw_card(data: pd.DataFrame, out_path: str):
    fig = plt.figure(figsize=(12, 9.5), dpi=130)
    ax  = fig.add_axes([0.10, 0.10, 0.82, 0.74])
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    # ── axis ranges ───────────────────────────────────────────────────────────
    pad = 0.12
    xpad = max(abs(data["xg_delta"].min()), abs(data["xg_delta"].max())) + pad
    ypad = max(abs(data["xga_delta"].min()), abs(data["xga_delta"].max())) + pad
    ax.set_xlim(-xpad, xpad)
    ax.set_ylim(-ypad, ypad)

    # ── quadrant shading ──────────────────────────────────────────────────────
    # top-right = best (more xG + less xGA than expected)
    ax.fill_between([0, xpad],   0, ypad,  color="#14532d", alpha=0.12, zorder=0)
    # bottom-left = worst
    ax.fill_between([-xpad, 0], -ypad, 0,  color="#450a0a", alpha=0.10, zorder=0)
    # bottom-right = good attack, bad defense
    ax.fill_between([0, xpad],  -ypad, 0,  color="#312e11", alpha=0.08, zorder=0)
    # top-left = bad attack, good defense
    ax.fill_between([-xpad, 0],  0, ypad,  color="#0f172a", alpha=0.08, zorder=0)

    # ── reference cross ───────────────────────────────────────────────────────
    ax.axvline(0, color=GRAY_MID, lw=0.9, alpha=0.7, zorder=1)
    ax.axhline(0, color=GRAY_MID, lw=0.9, alpha=0.7, zorder=1)

    # ── quadrant corner labels ────────────────────────────────────────────────
    ql = dict(fontsize=7.5, fontfamily="Franklin Gothic Medium", va="center", ha="center")
    ax.text( xpad * 0.55,  ypad * 0.88, "ATAQUE FORTE\nDEFESA SÓLIDA",
            color="#4ade80", alpha=0.60, **ql)
    ax.text(-xpad * 0.55,  ypad * 0.88, "ATAQUE FRACO\nDEFESA SÓLIDA",
            color=GRAY_LIGHT, alpha=0.50, **ql)
    ax.text( xpad * 0.55, -ypad * 0.88, "ATAQUE FORTE\nDEFESA FRACA",
            color=GRAY_LIGHT, alpha=0.50, **ql)
    ax.text(-xpad * 0.55, -ypad * 0.88, "ATAQUE FRACO\nDEFESA FRACA",
            color="#c0392b", alpha=0.55, **ql)

    # ── grid ──────────────────────────────────────────────────────────────────
    ax.grid(True, color=GRAY_DIM, linewidth=0.35, alpha=0.5, zorder=0)
    ax.tick_params(colors=GRAY_MID, labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRAY_DIM)
        spine.set_linewidth(0.6)

    # ── axis labels ───────────────────────────────────────────────────────────
    ax.set_xlabel("Saldo xG  (Real − Esperado pelo calendário)",
                  fontsize=10, color=GRAY_LIGHT,
                  fontfamily="Franklin Gothic Medium", labelpad=8)
    ax.set_ylabel("Saldo xGA  (↑ melhor defesa que o esperado)",
                  fontsize=10, color=GRAY_LIGHT,
                  fontfamily="Franklin Gothic Medium", labelpad=8)

    # axis direction hints along the reference lines
    ax.text(xpad * 0.97, 0.012, "› melhor ataque",
            fontsize=6.5, color=GRAY_MID, ha="right", va="bottom",
            fontfamily="Franklin Gothic Medium", alpha=0.7)
    ax.text(0.012, ypad * 0.97, "› melhor defesa",
            fontsize=6.5, color=GRAY_MID, ha="left", va="top",
            fontfamily="Franklin Gothic Medium", alpha=0.7, rotation=90)

    # ── plot each team ────────────────────────────────────────────────────────
    for _, row in data.iterrows():
        is_sport = row["team_key"] == "sport"
        x, y = row["xg_delta"], row["xga_delta"]

        # Sport highlight: gold glow ring drawn BEHIND the logo
        if is_sport:
            ax.scatter(x, y, s=520, color=GOLD, alpha=0.18, marker="o", zorder=4)
            ax.scatter(x, y, s=320, color="none", edgecolors=GOLD,
                       linewidths=2.2, marker="o", zorder=4)

        logo = _logo_image(row["team_key"], size=36 if is_sport else 30)
        if logo:
            ab = AnnotationBbox(
                logo, (x, y),
                frameon=False,
                zorder=5 + (10 if is_sport else 0),
                pad=0.0,
            )
            ax.add_artist(ab)
        else:
            ax.scatter(x, y, s=100 if is_sport else 60,
                       color=GOLD if is_sport else GRAY_MID,
                       zorder=5, marker="o")

        # Label
        label = row["display"] if not is_sport else "Sport Recife"
        ox, oy = LABEL_OFFSETS.get(row["team_key"], (+0.015, +0.040))
        ha = "left" if ox >= 0 else "right"
        ax.text(
            x + ox, y + oy, label,
            fontsize=9.0 if is_sport else 6.2,
            color=GOLD if is_sport else GRAY_LIGHT,
            fontfamily="Franklin Gothic Heavy" if is_sport else "Franklin Gothic Medium",
            alpha=1.0 if is_sport else 0.75,
            va="bottom", ha=ha, zorder=6 + (10 if is_sport else 0),
            path_effects=[pe.withStroke(linewidth=2.0 if is_sport else 1.5,
                                        foreground=BG)],
        )

    # ── title block ───────────────────────────────────────────────────────────
    rounds = int(data["rounds"].iloc[0])
    df_raw = pd.read_csv(STATS_CSV)
    rnds   = sorted(df_raw["round"].dropna().unique().astype(int))
    rnd_label = f"R{rnds[0]}–R{rnds[-1]}" if len(rnds) > 1 else f"R{rnds[0]}"

    fig.text(0.10, 0.930, "Saldo xG vs xGA",
             fontsize=22, color=WHITE, fontfamily="Franklin Gothic Heavy",
             va="bottom", ha="left")
    fig.text(0.10, 0.910,
             f"DESEMPENHO REAL vs ESPERADO PELO CALENDÁRIO — SÉRIE B 2026 · {rnd_label}",
             fontsize=8.5, color=GRAY_LIGHT, fontfamily="Franklin Gothic Medium",
             va="bottom", ha="left", alpha=0.85)

    fig.add_artist(plt.Line2D(
        [0.10, 0.92], [0.900, 0.900],
        color=GOLD, linewidth=0.8, alpha=0.5,
        transform=fig.transFigure,
    ))

    # round badge
    ax.text(0.99, 0.987, f"Série B 2026 · {rnd_label} · {rounds} rodadas",
            transform=ax.transAxes, fontsize=7.5, color=GRAY_MID,
            va="top", ha="right", fontfamily="Franklin Gothic Medium", alpha=0.8)

    # ── avatar footer ─────────────────────────────────────────────────────────
    if os.path.exists(AVATAR):
        avatar_img = Image.open(AVATAR).convert("RGBA")
        avatar_img.thumbnail((32, 32), Image.LANCZOS)
        av_ax = fig.add_axes([0.875, 0.015, 0.042, 0.055])
        av_ax.imshow(np.array(avatar_img))
        av_ax.axis("off")
    fig.text(0.10, 0.038, "@SportRecifeLab",
             fontsize=7.5, color=GRAY_MID, fontfamily="Franklin Gothic Medium",
             va="center", alpha=0.7)

    # ── save ─────────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=130, bbox_inches="tight",
                facecolor=BG, edgecolor="none")
    plt.close(fig)
    print(f"Saved -> {out_path}")


# ─────────────────────────────────────────────────────────────────────────────
def main():
    data     = _build_data()
    today    = datetime.date.today().strftime("%Y-%m-%d")
    slug     = f"{today}_xg-xga-scatter"
    out_dir  = os.path.join(OUT_DIR, slug)
    out_path = os.path.join(out_dir, "card.png")
    _draw_card(data, out_path)

    sport = data[data["team_key"] == "sport"].iloc[0]
    tweet_lines = [
        "xG vs xGA — saldo de cada time na Serie B 2026",
        "",
        "Eixo X: produziu mais (ou menos) xG do que o calendário sugeria.",
        "Eixo Y: sofreu mais (ou menos) xGA do que o esperado.",
        "",
        f"Sport: +{sport['xg_delta']:.2f} xG | {sport['xga_delta']:+.2f} xGA vs esperado",
        "",
        "#SerieB2026 #SportRecife #DataFootball",
    ]
    with open(os.path.join(out_dir, "tweet.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(tweet_lines))

    import json
    meta = {
        "slug": slug, "type": "xg_xga_delta_scatter",
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "data_source": "serie_b_2026/team_match_stats.csv",
    }
    with open(os.path.join(out_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print("Done.")


if __name__ == "__main__":
    main()
