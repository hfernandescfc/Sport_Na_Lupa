# -*- coding: utf-8 -*-
"""
Análise: Sport com vs sem Zé Gabriel em campo (Série B 2026)

Critério: para cada partida, divide os chutes pelo minuto da substituição.
xG e xGA calculados acumulando shotmap por período (com ZG / sem ZG).

Saída no terminal: tabela comparativa + detalhe por partida.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR  = Path(__file__).parent
CACHE_DIR = BASE_DIR / "data/raw/sofascore/sport/zegabriel_shotmaps"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── Partidas em que Zé Gabriel jogou na Série B ──────────────────────────────
# (event_id, match_code, round, minutes_played, sub_minute_or_None)
# sub_minute=None → jogou os 90'
MATCHES = [
    (15525993, "jOscJu",  1, 90, None),                        # R1 vs Cuiabá
    (15526002, "jOswP",   2, 67,  67),                         # R2 vs Vila Nova
    (15526008, "jOsxP",   3, 90, None),                        # R3 vs Londrina
    (15526022, "jOspWc",  4, 86,  86),                         # R4 vs Avaí
    (15526043, "jOsokeb", 6, 45,  45),                         # R6 vs Novorizontino (saiu intervalo)
]

SPORT_NAME = "Sport Recife"


def make_driver():
    opts = EdgeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    return webdriver.Edge(options=opts)


def fetch_shotmap(driver, event_id: int) -> list[dict] | None:
    """Fetch shotmap for an event; cache to disk."""
    cache_path = CACHE_DIR / f"{event_id}_shotmap.json"
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8")).get("shotmap", [])
        except Exception:
            pass

    url = f"/api/v1/event/{event_id}/shotmap"
    try:
        result = driver.execute_script(
            """
            var xhr = new XMLHttpRequest();
            xhr.open("GET", arguments[0], false);
            xhr.send();
            return {status: xhr.status, body: xhr.responseText};
            """,
            url,
        )
    except Exception as exc:
        print(f"  XHR fail event={event_id}: {exc}")
        return None

    if result.get("status") != 200:
        print(f"  HTTP {result.get('status')} for event={event_id}")
        return None

    try:
        body = json.loads(result["body"])
    except Exception as exc:
        print(f"  JSON parse fail event={event_id}: {exc}")
        return None

    cache_path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    return body.get("shotmap", [])


def fetch_match_meta(driver, event_id: int) -> dict | None:
    """Fetch event meta to know which side is Sport."""
    cache_path = CACHE_DIR / f"{event_id}_event.json"
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    url = f"/api/v1/event/{event_id}"
    try:
        result = driver.execute_script(
            """
            var xhr = new XMLHttpRequest();
            xhr.open("GET", arguments[0], false);
            xhr.send();
            return {status: xhr.status, body: xhr.responseText};
            """,
            url,
        )
        if result.get("status") != 200:
            return None
        body = json.loads(result["body"])
        cache_path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
        return body
    except Exception as exc:
        print(f"  meta fail event={event_id}: {exc}")
        return None


def shot_minute(shot: dict) -> float:
    """Effective minute including added time."""
    t = shot.get("time")
    at = shot.get("addedTime") or 0
    if t is None:
        return -1
    return float(t) + float(at)


def main():
    print("Carregando dados via Selenium (Edge headless)...")
    driver = make_driver()
    try:
        driver.get("https://www.sofascore.com/")

        rows_with = []   # períodos com ZG
        rows_without = []  # períodos sem ZG

        for event_id, code, rnd, mins, sub_min in MATCHES:
            print(f"\n[R{rnd}] {code} (event {event_id}) — ZG jogou {mins}', "
                  f"{'SAIU aos ' + str(sub_min) + chr(39) if sub_min else 'JOGOU 90 completos'}")

            meta = fetch_match_meta(driver, event_id)
            if meta is None:
                print("  ⚠ sem meta; pulando")
                continue
            event = meta.get("event", {})
            home_name = event.get("homeTeam", {}).get("name", "")
            away_name = event.get("awayTeam", {}).get("name", "")
            sport_is_home = (SPORT_NAME.lower() in home_name.lower())
            print(f"  {home_name} x {away_name} | Sport home={sport_is_home}")

            shots = fetch_shotmap(driver, event_id)
            if shots is None:
                print("  ⚠ sem shotmap; pulando")
                continue
            print(f"  Total de chutes: {len(shots)}")

            cutoff = sub_min if sub_min is not None else 91   # 91 = todos contam como "com ZG"

            # Categorize each shot
            for s in shots:
                m = shot_minute(s)
                if m < 0:
                    continue
                xg = s.get("xg") or 0.0
                is_home = s.get("isHome", False)
                is_sport = (is_home == sport_is_home)
                period = "with" if m <= cutoff else "without"

                row = {
                    "event_id": event_id,
                    "round": rnd,
                    "minute": m,
                    "is_sport": is_sport,
                    "xg": float(xg),
                    "period": period,
                }
                if period == "with":
                    rows_with.append(row)
                else:
                    rows_without.append(row)

        # ── Agregação ─────────────────────────────────────────────────────
        df_with = pd.DataFrame(rows_with)
        df_without = pd.DataFrame(rows_without)

        # Tempo total em cada período (em minutos, somando partidas)
        total_min_with = sum((s if s is not None else 90) for _, _, _, _, s in MATCHES)
        # Tempo "sem ZG" só conta partidas em que ele saiu durante (jogo até 90)
        total_min_without = sum((90 - s) for _, _, _, _, s in MATCHES if s is not None and s < 90)

        print("\n" + "=" * 80)
        print("COMPARATIVO: SPORT COM vs SEM ZÉ GABRIEL EM CAMPO (Série B 2026)")
        print("=" * 80)
        print(f"\nMinutos totais COM Zé Gabriel:  {total_min_with} min")
        print(f"Minutos totais SEM Zé Gabriel: {total_min_without} min\n")

        def agg(df: pd.DataFrame, key: str, mins: int) -> dict:
            if df.empty:
                return {"shots": 0, "xg_total": 0.0, "xg_per_90": 0.0}
            sel = df[df["is_sport"] == (key == "sport")]
            return {
                "shots": len(sel),
                "xg_total": sel["xg"].sum(),
                "xg_per_90": (sel["xg"].sum() / mins * 90) if mins > 0 else 0.0,
            }

        xg_with    = agg(df_with,    "sport",    total_min_with)
        xg_without = agg(df_without, "sport",    total_min_without)
        xga_with   = agg(df_with,    "opponent", total_min_with)
        xga_without= agg(df_without, "opponent", total_min_without)

        print(f"{'Métrica':<25} {'COM ZG':<22} {'SEM ZG':<22} {'Δ (per 90)':<12}")
        print("-" * 80)
        print(f"{'xG total (Sport)':<25} {xg_with['xg_total']:>8.2f} ({xg_with['shots']:>2} chutes)  "
              f"{xg_without['xg_total']:>8.2f} ({xg_without['shots']:>2} chutes)  ")
        print(f"{'xG por 90 min':<25} {xg_with['xg_per_90']:>20.2f}  {xg_without['xg_per_90']:>20.2f}  "
              f"{xg_with['xg_per_90'] - xg_without['xg_per_90']:>+11.2f}")
        print()
        print(f"{'xGA total (advs.)':<25} {xga_with['xg_total']:>8.2f} ({xga_with['shots']:>2} chutes)  "
              f"{xga_without['xg_total']:>8.2f} ({xga_without['shots']:>2} chutes)  ")
        print(f"{'xGA por 90 min':<25} {xga_with['xg_per_90']:>20.2f}  {xga_without['xg_per_90']:>20.2f}  "
              f"{xga_with['xg_per_90'] - xga_without['xg_per_90']:>+11.2f}")

        # ── Detalhe por partida ──────────────────────────────────────────
        print("\n" + "=" * 80)
        print("DETALHE POR PARTIDA")
        print("=" * 80)
        all_rows = pd.concat([df_with, df_without], ignore_index=True) if not df_with.empty else df_without

        for event_id, code, rnd, mins, sub_min in MATCHES:
            mp = all_rows[all_rows["event_id"] == event_id]
            cutoff = sub_min if sub_min is not None else 91
            sport_with = mp[(mp["is_sport"]) & (mp["period"] == "with")]
            sport_no   = mp[(mp["is_sport"]) & (mp["period"] == "without")]
            opp_with   = mp[(~mp["is_sport"]) & (mp["period"] == "with")]
            opp_no     = mp[(~mp["is_sport"]) & (mp["period"] == "without")]

            sub_str = f"até {sub_min}'" if sub_min else "90'"
            print(f"\nR{rnd} | {code} | ZG {sub_str}")
            print(f"  COM ZG (0-{cutoff}'):  Sport xG={sport_with['xg'].sum():.2f} ({len(sport_with)} ch.)  "
                  f"|  Adv xG={opp_with['xg'].sum():.2f} ({len(opp_with)} ch.)")
            if sub_min and sub_min < 90:
                print(f"  SEM ZG ({cutoff}-90'): Sport xG={sport_no['xg'].sum():.2f} ({len(sport_no)} ch.)  "
                      f"|  Adv xG={opp_no['xg'].sum():.2f} ({len(opp_no)} ch.)")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
