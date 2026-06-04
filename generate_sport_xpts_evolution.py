"""
Gera card "Sport xPts por Rodada" — Série B 2026.

Para cada rodada exibe:
  - Escudo do adversário + rank em xPts (#N)
  - Barra com xPts obtido no jogo (Poisson, colorida por resultado)
  - Resultado V/E/D + placar
  - Linhas de xPts e pts acumulados

Saída: pending_posts/{date}_sport-xpts-rodada/01_xpts_evolution.png
"""
import base64, datetime, math, re, sys, time
from pathlib import Path
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR     = Path(__file__).parent
TEMPLATE     = BASE_DIR / "card_sport_xpts_evolution.html"
LOGOS_DIR    = BASE_DIR / "data/cache/logos"
AVATAR_PATH  = BASE_DIR / "sportrecifelab_avatar.png"
TODAY_STR    = datetime.date.today().strftime("%Y-%m-%d")
OUT_DIR      = BASE_DIR / f"pending_posts/{TODAY_STR}_sport-xpts-rodada"

SPORT_KEY    = "sport"
SPORT_ID     = 1959

TEAM_ID_MAP = {
    "america-mg":      1973,
    "america-mineiro": 1973,
    "athletic-club":   342775,
    "atletico-go":     7314,
    "avai":            7315,
    "botafogo-sp":     1979,
    "ceara":           2001,
    "crb":             22032,
    "criciuma":        1984,
    "cuiaba":          49202,
    "fortaleza":       2020,
    "goias":           1960,
    "novorizontino":   135514,
    "juventude":       1980,
    "londrina":        2022,
    "nautico":         2011,
    "operario-pr":     39634,
    "ponte-preta":     1969,
    "sao-bernardo":    47504,
    "sport":           1959,
    "vila-nova":       2021,
    "vila-nova-fc":    2021,
}

OPP_DISPLAY = {
    "america-mg":      "América-MG",
    "america-mineiro": "América-MG",
    "athletic-club":   "Athletic",
    "atletico-go":     "Atl. Goianiense",
    "avai":            "Avaí",
    "botafogo-sp":     "Botafogo-SP",
    "ceara":           "Ceará",
    "crb":             "CRB",
    "criciuma":        "Criciúma",
    "cuiaba":          "Cuiabá",
    "fortaleza":       "Fortaleza",
    "goias":           "Goiás",
    "novorizontino":   "Grêmio Nov.",
    "juventude":       "Juventude",
    "londrina":        "Londrina",
    "nautico":         "Náutico",
    "operario-pr":     "Operário-PR",
    "ponte-preta":     "Ponte Preta",
    "sao-bernardo":    "São Bernardo",
    "vila-nova":       "Vila Nova",
    "vila-nova-fc":    "Vila Nova",
}

# Normalise xPts table keys to match matches.csv
XPTS_KEY_ALIAS = {
    "vila-nova-fc": "vila-nova",
    "america-mineiro": "america-mg",
}


# ---------------------------------------------------------------------------
# Poisson helpers
# ---------------------------------------------------------------------------

def _pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam + k * math.log(lam) - math.lgamma(k + 1))


def _max_k(lam: float) -> int:
    if lam <= 0:
        return 0
    k, cdf = 0, 0.0
    while True:
        cdf += _pmf(k, lam)
        if 1 - cdf < 1e-10:
            return k
        k += 1


def xpts_from_xg(xg_home: float, xg_away: float) -> tuple[float, float]:
    """Return (xpts_home, xpts_away) using independent Poisson model."""
    nh, na = _max_k(xg_home), _max_k(xg_away)
    hpmf = [_pmf(i, xg_home) for i in range(nh + 1)]
    apmf = [_pmf(j, xg_away) for j in range(na + 1)]
    ph = pd_ = pa = 0.0
    for i, h in enumerate(hpmf):
        for j, a in enumerate(apmf):
            p = h * a
            if i > j:   ph  += p
            elif i == j: pd_ += p
            else:        pa  += p
    return 3 * ph + pd_, 3 * pa + pd_


# ---------------------------------------------------------------------------
# Data assembly
# ---------------------------------------------------------------------------

def build_rounds(season: int = 2026) -> list[dict]:
    curated = BASE_DIR / f"data/curated/serie_b_{season}"
    matches_df = pd.read_csv(curated / "matches.csv")
    stats_df   = pd.read_csv(curated / "team_match_stats.csv")
    xpts_df    = pd.read_csv(curated / "expected_points_table.csv")

    # Normalise xPts table keys to match matches keys
    xpts_df["team_key_lookup"] = xpts_df["team_key"].replace(XPTS_KEY_ALIAS)
    rank_map = dict(zip(xpts_df["team_key_lookup"], xpts_df["rank_xpts"]))

    # Sport matches only
    sport_m = matches_df[
        ((matches_df["home_team_key"] == SPORT_KEY) |
         (matches_df["away_team_key"] == SPORT_KEY)) &
        (matches_df["status"] == "completed")
    ].sort_values("round")

    # xG indexed by match_code + team_key
    xg_map = dict(zip(
        stats_df["match_code"] + "|" + stats_df["team_key"],
        pd.to_numeric(stats_df["expected_goals"], errors="coerce").fillna(1.0)
    ))

    rounds_data = []
    cum_pts = cum_xpts = 0.0

    for _, row in sport_m.iterrows():
        is_home   = row["home_team_key"] == SPORT_KEY
        opp_key   = row["away_team_key"] if is_home else row["home_team_key"]
        mc        = row["match_code"]

        sport_g  = int(row["home_score"] if is_home else row["away_score"])
        opp_g    = int(row["away_score"] if is_home else row["home_score"])

        sport_xg = xg_map.get(f"{mc}|{SPORT_KEY}", 1.0)
        opp_xg   = xg_map.get(f"{mc}|{opp_key}", 1.0)

        if is_home:
            xp_sport, _ = xpts_from_xg(sport_xg, opp_xg)
        else:
            _, xp_sport = xpts_from_xg(opp_xg, sport_xg)

        result = "V" if sport_g > opp_g else ("E" if sport_g == opp_g else "D")
        pts    = 3 if result == "V" else (1 if result == "E" else 0)

        cum_pts   += pts
        cum_xpts  += xp_sport

        opp_rank = rank_map.get(opp_key, 10)

        rounds_data.append({
            "round":      int(row["round"]),
            "oppKey":     opp_key,
            "opp":        OPP_DISPLAY.get(opp_key, opp_key),
            "rank":       int(opp_rank),
            "isHome":     "true" if is_home else "false",
            "sportScore": sport_g,
            "oppScore":   opp_g,
            "result":     result,
            "pts":        pts,
            "xpts":       round(xp_sport, 2),
            "cumPts":     cum_pts,
            "cumXpts":    round(cum_xpts, 2),
        })

    return rounds_data


# ---------------------------------------------------------------------------
# Logo helpers
# ---------------------------------------------------------------------------

def _logo_b64(key: str) -> str:
    team_id = TEAM_ID_MAP.get(key)
    if not team_id:
        return ""
    path = LOGOS_DIR / f"{team_id}.png"
    if not path.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def _build_rounds_js(rounds_data: list[dict]) -> str:
    lines = []
    for r in rounds_data:
        logo = _logo_b64(r["oppKey"])
        lines.append(
            f'  {{ round:{r["round"]}, opp:"{r["opp"]}", rank:{r["rank"]}, '
            f'isHome:{r["isHome"]}, sportScore:{r["sportScore"]}, oppScore:{r["oppScore"]}, '
            f'result:"{r["result"]}", pts:{r["pts"]}, xpts:{r["xpts"]}, '
            f'oppLogo:"{logo}", cumPts:{r["cumPts"]}, cumXpts:{r["cumXpts"]} }},'
        )
    return "[\n" + "\n".join(lines) + "\n]"


def _patch_html(src: str, rounds_data: list[dict]) -> str:
    # 1. Rounds data
    src = re.sub(
        r"const rounds = \[[\s\S]*?\];",
        f"const rounds = {_build_rounds_js(rounds_data)};",
        src,
    )

    # 2. Max round in title
    max_round = rounds_data[-1]["round"] if rounds_data else ""
    if max_round:
        src = src.replace(
            "Sport Recife · xPts por Rodada · Série B 2026",
            f"Sport Recife · xPts por Rodada · Série B 2026 · R{max_round}"
        )

    # 3. maxRound constant
    src = re.sub(r"const maxRound\s*=\s*\d+;", f"const maxRound  = {max_round};", src)

    # 4. Sport logo
    sport_logo = _logo_b64(SPORT_KEY)
    src = src.replace("'__SPORT_LOGO__'", f"'{sport_logo}'")

    # 5. ACC_Y_MAX — round up to nearest 5 above cumXpts
    max_xpts = rounds_data[-1]["cumXpts"] if rounds_data else 20
    max_pts  = rounds_data[-1]["cumPts"]  if rounds_data else 20
    acc_max  = math.ceil(max(max_xpts, max_pts) / 5 + 0.5) * 5
    src = re.sub(
        r"const ACC_Y_MAX\s*=.*?;",
        f"const ACC_Y_MAX  = {acc_max};",
        src,
    )

    # 6. Avatar
    if AVATAR_PATH.exists():
        b64 = base64.b64encode(AVATAR_PATH.read_bytes()).decode()
        src = src.replace("__AVATAR_SRC__", f"data:image/png;base64,{b64}")
    else:
        src = src.replace('src="__AVATAR_SRC__"', 'style="display:none"')

    return src


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render(rounds_data: list[dict]) -> None:
    if not TEMPLATE.exists():
        print(f"⚠  Template não encontrado: {TEMPLATE}")
        return

    html_src     = TEMPLATE.read_text(encoding="utf-8")
    html_patched = _patch_html(html_src, rounds_data)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = OUT_DIR / "_xpts_evo_tmp.html"
    tmp.write_text(html_patched, encoding="utf-8")

    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
        from selenium.webdriver.common.by import By
    except ImportError:
        print("⚠  Selenium não disponível")
        tmp.unlink(missing_ok=True)
        return

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1200,1200")
    opts.add_argument("--force-device-scale-factor=1")

    driver = webdriver.Edge(options=opts)
    out_path = OUT_DIR / "01_xpts_evolution.png"
    try:
        driver.get(tmp.as_uri())
        driver.set_window_size(1200, 1200)
        time.sleep(2.0)
        card = driver.find_element(By.CSS_SELECTOR, ".card")
        card.screenshot(str(out_path))
        print(f"  OK  {out_path}")
    finally:
        driver.quit()
        tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Montando dados por rodada...")
    rounds_data = build_rounds(season=2026)
    for r in rounds_data:
        print(f"  R{r['round']} vs {r['opp']:<16} "
              f"{r['result']} {r['sportScore']}-{r['oppScore']}  "
              f"xPts={r['xpts']:.2f}  cum={r['cumXpts']:.2f}/{r['cumPts']:.0f}  "
              f"opp#xPts={r['rank']}")

    print(f"\nGerando card ({len(rounds_data)} rodadas)...")
    render(rounds_data)
    print(f"Salvo em: {OUT_DIR}")
