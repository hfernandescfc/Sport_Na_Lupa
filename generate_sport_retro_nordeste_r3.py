"""
Gera os 4 cards de análise para:
  Sport Recife 3 × 0 Retrô — Copa do Nordeste R3 — 08/04/2026
"""
import json, sys
sys.path.insert(0, ".")

from generate_match_cards import generate_match_cards

with open("data/raw/sofascore/sport/sport_retro_copa_nordeste_r3_graph.json") as f:
    _graph = json.load(f)
MOMENTUM = [{"minute": p["minute"], "value": p["value"]}
            for p in _graph.get("graphPoints", [])]

MATCH_DATA = {
    "home_team":   "SPORT",
    "away_team":   "RETRÔ",
    "score":       [3, 0],
    "date":        "08.04.2026",
    "round":       "R3",
    "competition": "COPA DO NORDESTE",
    "status":      "completed",

    "home_logo": "data/cache/logos/1959.png",    # Sport Recife
    "away_logo": "data/cache/logos/324839.png",  # Retrô

    "stats": {
        "possession":      [64.0, 36.0],
        "xg":              [2.29, 0.47],
        "shots_total":     [19,   4],
        "shots_on_target": [6,    0],
        "corners":         [8,    0],
        "fouls":           [17,   20],
        "passes_total":    [506,  256],
        "passes_accuracy": [88.0, 82.0],   # accurate/total * 100
        "tackles":         [4,    0],
        "yellow_cards":    [2,    2],
        "red_cards":       [0,    0],
    },

    "shots": [
        # ── Sport (home) ──────────────────────────────────────────────────
        {"team": "home", "player": "Perotti",           "minute": 5,  "type": "save",  "xg": 0.1752,   "coord": (6,  59)},
        {"team": "home", "player": "Felipinho",         "minute": 11, "type": "save",  "xg": 0.0511,   "coord": (23, 33)},
        {"team": "home", "player": "Perotti",           "minute": 11, "type": "miss",  "xg": 0.0188,   "coord": (29, 68)},
        {"team": "home", "player": "Clayson",           "minute": 13, "type": "block", "xg": 0.0099,   "coord": (21, 25)},
        {"team": "home", "player": "C. Barletta",       "minute": 33, "type": "miss",  "xg": 0.0041,   "coord": (15, 73)},
        {"team": "home", "player": "Perotti",           "minute": 59, "type": "miss",  "xg": 0.1792,   "coord": (8,  50)},
        {"team": "home", "player": "Carlos De Pena",    "minute": 60, "type": "save",  "xg": 0.0769,   "coord": (20, 35)},
        {"team": "home", "player": "Iury Castilho",     "minute": 60, "type": "goal",  "xg": 0.7745,   "coord": (5,  52)},
        {"team": "home", "player": "Zé Lucas",          "minute": 66, "type": "miss",  "xg": 0.0396,   "coord": (19, 60)},
        {"team": "home", "player": "Yago Felipe",       "minute": 68, "type": "miss",  "xg": 0.3074,   "coord": (7,  44)},
        {"team": "home", "player": "Iury Castilho",     "minute": 73, "type": "miss",  "xg": 0.1129,   "coord": (15, 50)},
        {"team": "home", "player": "Carlos De Pena",    "minute": 73, "type": "miss",  "xg": 0.0009,   "coord": (22, 24)},
        {"team": "home", "player": "C. Barletta",       "minute": 74, "type": "goal",  "xg": 0.2052,   "coord": (8,  64)},
        {"team": "home", "player": "Carlos De Pena",    "minute": 77, "type": "miss",  "xg": 0.1390,   "coord": (6,  34)},
        {"team": "home", "player": "Habraão",           "minute": 77, "type": "goal",  "xg": 0.0779,   "coord": (10, 56)},
        {"team": "home", "player": "Felipinho",         "minute": 81, "type": "miss",  "xg": 0.0009,   "coord": (25, 46)},
        {"team": "home", "player": "Carlos De Pena",    "minute": 86, "type": "block", "xg": 0.0602,   "coord": (15, 49)},
        {"team": "home", "player": "Carlos De Pena",    "minute": 86, "type": "block", "xg": 0.0084,   "coord": (14, 52)},
        {"team": "home", "player": "Edson Lucas",       "minute": 90, "type": "block", "xg": 0.0486,   "coord": (8,  36)},
        # ── Retrô (away) ─────────────────────────────────────────────────
        {"team": "away", "player": "D. Matos",          "minute": 12, "type": "miss",  "xg": 0.0054,   "coord": (29, 50)},
        {"team": "away", "player": "Sillas",            "minute": 29, "type": "block", "xg": 0.0049,   "coord": (22, 66)},
        {"team": "away", "player": "D. Matos",          "minute": 45, "type": "miss",  "xg": 0.4501,   "coord": (4,  46)},
        {"team": "away", "player": "Kadi",              "minute": 63, "type": "miss",  "xg": 0.0046,   "coord": (18, 51)},
    ],

    "momentum": MOMENTUM,
}

if __name__ == "__main__":
    import os
    out_dir = "pending_posts/2026-04-09_sport-retro-nordeste-r3"
    cards = generate_match_cards(MATCH_DATA, output_dir=out_dir)
    print(f"\n{len(cards)} cards gerados em {out_dir}/")
