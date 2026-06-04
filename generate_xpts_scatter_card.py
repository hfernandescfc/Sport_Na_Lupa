"""
Gera Card 02 — Scatter xPts vs Força dos Adversários  Série B 2026
  Renderiza card2_scatter_logos.html via Selenium + Edge headless → PNG 1080×1080
  Saída: pending_posts/{date}_xpts-serie-b/02_xpts_scatter.png

Requer:
  data/curated/serie_b_2026/expected_points_table.csv   (colunas sos + sos_rank)
  card2_scatter_logos.html   (template visual)
  data/cache/logos/{team_id}.png                        (escudos dos 20 clubes)
"""

import base64
import datetime
import re
import sys
import time
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR     = Path(__file__).parent
TABLE_PATH   = BASE_DIR / "data/curated/serie_b_2026/expected_points_table.csv"
TEMPLATE     = BASE_DIR / "card2_scatter_logos.html"
LOGOS_DIR    = BASE_DIR / "data/cache/logos"
AVATAR_PATH  = BASE_DIR / "sportrecifelab_avatar.png"
TODAY_STR    = datetime.date.today().strftime("%Y-%m-%d")
OUT_DIR      = BASE_DIR / f"pending_posts/{TODAY_STR}_xpts-serie-b"

SPORT_KEY = "sport"

TEAM_ID_MAP = {
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
    "vila-nova-fc":    2021,
}

SHORT_NAMES: dict[str, str] = {
    "america-mineiro": "América",
    "athletic-club":   "Athletic",
    "atletico-go":     "Atlético",
    "avai":            "Avaí",
    "botafogo-sp":     "Botafogo-SP",
    "ceara":           "Ceará",
    "crb":             "CRB",
    "criciuma":        "Criciúma",
    "cuiaba":          "Cuiabá",
    "fortaleza":       "Fortaleza",
    "goias":           "Goiás",
    "novorizontino":   "Grêmio",
    "juventude":       "Juventude",
    "londrina":        "Londrina",
    "nautico":         "Náutico",
    "operario-pr":     "Operário-PR",
    "ponte-preta":     "Ponte",
    "sao-bernardo":    "São",
    "sport":           "Sport",
    "vila-nova-fc":    "Vila",
}


def _load_logos_as_base64() -> dict[str, str]:
    logos = {}
    for team_key, team_id in TEAM_ID_MAP.items():
        logo_path = LOGOS_DIR / f"{team_id}.png"
        if logo_path.exists():
            b64 = base64.b64encode(logo_path.read_bytes()).decode()
            logos[team_key] = f"data:image/png;base64,{b64}"
        else:
            print(f"  ⚠  Logo não encontrado para {team_key} (id={team_id})")
    return logos


def _build_teams_js(df: pd.DataFrame, logos: dict[str, str]) -> str:
    lines = []
    for _, row in df.iterrows():
        key      = row["team_key"]
        name     = SHORT_NAMES.get(key, row["team_name"].split()[0])
        sos      = float(row["sos"])
        xpts     = float(row["xPts"])
        delta    = float(row["pts_diff"])
        is_sport = "true" if key == SPORT_KEY else "false"
        logo_src = logos.get(key, "")
        lines.append(
            f'  {{ name:"{name}", sos:{sos:.3f}, xPts:{xpts:.2f}, '
            f'delta:{delta:+.1f}, isSport:{is_sport}, logo:"{logo_src}" }},'
        )
    return "[\n" + "\n".join(lines) + "\n]"


def _build_bounds(df: pd.DataFrame) -> dict:
    x = df["sos"].astype(float)
    y = df["xPts"].astype(float)
    return {
        "X_MIN": round(x.min() - 0.04, 3),
        "X_MAX": round(x.max() + 0.06, 3),
        "Y_MIN": round(y.min() - 0.30, 2),
        "Y_MAX": round(y.max() + 0.50, 2),
        "X_MID": round(float(x.median()), 3),
        "Y_MID": round(float(y.median()), 2),
    }


def _patch_html(src: str, df: pd.DataFrame, logos: dict[str, str]) -> str:
    # 1. Substituir bloco const teams = [...]
    teams_js = _build_teams_js(df, logos)
    src = re.sub(
        r"const teams = \[[\s\S]*?\];",
        f"const teams = {teams_js};",
        src,
    )

    # 2. Substituir bounds de escala
    b = _build_bounds(df)
    src = re.sub(
        r"const X_MIN = [\d.]+, X_MAX = [\d.]+;",
        f"const X_MIN = {b['X_MIN']}, X_MAX = {b['X_MAX']};",
        src,
    )
    src = re.sub(
        r"const Y_MIN = [\d.]+,\s*Y_MAX = [\d.]+;",
        f"const Y_MIN = {b['Y_MIN']},  Y_MAX = {b['Y_MAX']};",
        src,
    )
    src = re.sub(r"const X_MID = [\d.]+;", f"const X_MID = {b['X_MID']};", src)
    src = re.sub(r"const Y_MID = [\d.]+;", f"const Y_MID = {b['Y_MID']};", src)

    # 3. Injetar avatar como base64 para evitar bloqueio de file:// no Edge headless
    if AVATAR_PATH.exists():
        b64 = base64.b64encode(AVATAR_PATH.read_bytes()).decode()
        src = src.replace("__AVATAR_SRC__", f"data:image/png;base64,{b64}")
    else:
        src = src.replace('src="__AVATAR_SRC__"', 'style="display:none"')

    # 4. Atualizar round no título
    max_mp = int(df["MP"].max()) if "MP" in df.columns else ""
    if max_mp:
        src = re.sub(
            r"Série B 2026 — xPts vs Força dos Adversários",
            f"Série B 2026 — xPts vs Força dos Adversários · R{max_mp}",
            src,
        )

    return src


def generate_scatter_card(df: pd.DataFrame) -> None:
    if "sos" not in df.columns:
        print(
            "\n⚠  Card 02 requer a coluna 'sos' — rode primeiro:\n"
            "   python -m src.main sync-serie-b-strength --season 2026\n"
            "   python -m src.main transform-standings --season 2026\n"
        )
        return

    if not TEMPLATE.exists():
        print(f"⚠  Template não encontrado: {TEMPLATE}")
        return

    print("  Carregando logos...")
    logos = _load_logos_as_base64()
    print(f"  {len(logos)}/{len(TEAM_ID_MAP)} logos carregados")

    html_src = TEMPLATE.read_text(encoding="utf-8")
    html_patched = _patch_html(html_src, df, logos)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp_html = OUT_DIR / "_scatter_tmp.html"
    tmp_html.write_text(html_patched, encoding="utf-8")

    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
        from selenium.webdriver.common.by import By
    except ImportError:
        print("⚠  Selenium não disponível — instale: pip install selenium")
        tmp_html.unlink(missing_ok=True)
        return

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1200,1200")
    options.add_argument("--force-device-scale-factor=1")

    driver = webdriver.Edge(options=options)
    out_path = OUT_DIR / "02_xpts_scatter.png"
    try:
        driver.get(tmp_html.as_uri())
        driver.set_window_size(1200, 1200)
        time.sleep(2.0)
        card_el = driver.find_element(By.CSS_SELECTOR, ".card")
        card_el.screenshot(str(out_path))
        print(f"  OK  {out_path}")
    finally:
        driver.quit()
        tmp_html.unlink(missing_ok=True)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Carregando dados...")
    df = pd.read_csv(TABLE_PATH)
    # Índice canônico = xPts ajustado por game state (quando disponível)
    if "xPts_adj" in df.columns:
        df["xPts"] = df["xPts_adj"]
        if "pts_diff_adj" in df.columns:
            df["pts_diff"] = df["pts_diff_adj"]
    has_sos = "sos" in df.columns
    print(f"  {len(df)} times  ·  SOS: {'sim' if has_sos else 'não'}")

    print("\nGerando Card 02 — Scatter xPts vs SOS...")
    generate_scatter_card(df)
    print(f"\nCard salvo em: {OUT_DIR}")
