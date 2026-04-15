"""
Sonda candidatos de endpoint para dados de passes individuais com coordenadas.

Uso:
    python discover_pass_endpoints.py --event 15526008 --player 1048276

Salva os resultados em:
    data/raw/sofascore/discovery/pass_endpoints_{event_id}.json
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


MATCH_URL_TEMPLATE = (
    "https://www.sofascore.com/football/match/londrina-sport-recife/jOsxP"
)

# Todos os padrões candidatos a conter passes com coordenadas
CANDIDATE_PATTERNS = [
    # Por evento (sem jogador)
    "/api/v1/event/{event}/incidents",      # eventos de partida — principal candidato (passes, gols, cartões…)
    "/api/v1/event/{event}/pass-map",
    "/api/v1/event/{event}/passmap",
    "/api/v1/event/{event}/passes",
    "/api/v1/event/{event}/shotmap",        # referência já conhecida
    "/api/v1/event/{event}/lineups",        # referência já conhecida
    "/api/v1/event/{event}/statistics",     # referência já conhecida
    # Por jogador
    "/api/v1/event/{event}/player/{player}/heatmap",
    "/api/v1/event/{event}/player/{player}/passes",
    "/api/v1/event/{event}/player/{player}/pass-map",
    "/api/v1/event/{event}/player/{player}/passmap",
    "/api/v1/event/{event}/player/{player}/statistics",
    "/api/v1/event/{event}/player/{player}/highlights",
    "/api/v1/event/{event}/player/{player}/timeline",
    "/api/v1/event/{event}/player/{player}/actions",
]


def probe_endpoints(event_id: int, player_id: int, match_url: str) -> list[dict]:
    from selenium import webdriver
    from selenium.webdriver.edge.options import Options

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Edge(options=opts)
    driver.set_page_load_timeout(30)

    results = []
    try:
        # Visita a página da partida para obter cookies/sessão válida
        print(f"  Abrindo página da partida: {match_url}")
        driver.get(match_url)
        time.sleep(4)

        for pattern in CANDIDATE_PATTERNS:
            path = pattern.format(event=event_id, player=player_id)
            try:
                response = driver.execute_script(
                    """
                    var xhr = new XMLHttpRequest();
                    xhr.open("GET", arguments[0], false);
                    xhr.send();
                    return {status: xhr.status, body: xhr.responseText};
                    """,
                    path,
                )
                status = response.get("status")
                body_raw = response.get("body", "")

                body = None
                parse_error = None
                try:
                    body = json.loads(body_raw)
                except Exception as e:
                    parse_error = str(e)

                # Análise rápida: que chaves de topo existem? Há coordenadas?
                top_keys = list(body.keys()) if isinstance(body, dict) else (
                    f"list[{len(body)}]" if isinstance(body, list) else type(body).__name__
                )
                has_coords = _has_coordinates(body)

                entry = {
                    "path": path,
                    "http_status": status,
                    "top_keys": top_keys,
                    "has_coordinates": has_coords,
                    "body_size_chars": len(body_raw),
                    "parse_error": parse_error,
                }

                icon = "OK" if status == 200 else "--"
                coord_flag = " [coords!]" if has_coords else ""
                print(f"  {icon} {status:>3}  {path}{coord_flag}")

                # Salva o body completo apenas para respostas 200
                if status == 200 and body is not None:
                    entry["body_preview"] = _preview(body)

                results.append(entry)

            except Exception as exc:
                print(f"  ERR  {path}  -> {exc}")
                results.append({"path": path, "error": str(exc)})

    finally:
        driver.quit()

    return results


def _has_coordinates(body) -> bool:
    """Verifica se a resposta contém campos de coordenadas (x, y, toX, toY, etc.)."""
    COORD_KEYS = {"x", "y", "toX", "toY", "startX", "startY", "endX", "endY",
                  "playerCoordinates", "coordinates"}
    if isinstance(body, dict):
        if body.keys() & COORD_KEYS:
            return True
        for v in body.values():
            if _has_coordinates(v):
                return True
    elif isinstance(body, list) and body:
        return _has_coordinates(body[0])
    return False


def _preview(body, max_items: int = 3) -> object:
    """Retorna uma amostra pequena do body para inspecção no JSON salvo."""
    if isinstance(body, list):
        return body[:max_items]
    if isinstance(body, dict):
        preview = {}
        for k, v in body.items():
            preview[k] = _preview(v, max_items) if isinstance(v, (list, dict)) else v
        return preview
    return body


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", type=int, required=True)
    parser.add_argument("--player", type=int, required=True)
    parser.add_argument("--match-url", default=MATCH_URL_TEMPLATE)
    args = parser.parse_args()

    print(f"\nDescoberta de endpoints de passes")
    print(f"  event_id  : {args.event}")
    print(f"  player_id : {args.player}")
    print(f"  match_url : {args.match_url}\n")

    results = probe_endpoints(args.event, args.player, args.match_url)

    out_dir = Path("data/raw/sofascore/discovery")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"pass_endpoints_{args.event}.json"

    payload = {
        "event_id": args.event,
        "player_id": args.player,
        "candidates_probed": len(results),
        "results": results,
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    hits = [r for r in results if r.get("http_status") == 200]
    coord_hits = [r for r in hits if r.get("has_coordinates")]

    print(f"\nResultado: {len(hits)}/{len(results)} endpoints retornaram 200")
    print(f"Com coordenadas: {len(coord_hits)}")
    print(f"Salvo em: {out_path}")

    if coord_hits:
        print("\nEndpoints COM coordenadas:")
        for r in coord_hits:
            print(f"  {r['path']}  chaves={r['top_keys']}")


if __name__ == "__main__":
    main()
