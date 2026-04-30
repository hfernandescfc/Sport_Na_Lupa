"""
Gera "Como o Ceará SC Joga" como HTML com dados reais + render PNG via Selenium Edge.

Estratégia:
  - CSS idêntico ao template HTML de referência (Barlow Condensed, layout grid)
  - Heatmap KDE real gerado em matplotlib → PNG base64 embutido no .pitch div
  - Logo Ceará base64 do cache local
  - Todos os valores calculados de attack_profile.json + team_heatmap.json
  - Selenium Edge headless → screenshot 1200×675 → PNG
"""
from __future__ import annotations

import base64
import io
import json
from collections import Counter, deque
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Arc
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
from scipy.stats import gaussian_kde
from scipy.ndimage import gaussian_filter, maximum_filter

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

BASE = Path(__file__).parent

# ── Constantes Série B 2026 ───────────────────────────────────────────────────
LEAGUE_AVG = {
    "possession":          50.0,
    "expected_goals":       1.10,
    "shots_total":         11.5,
    "long_balls_accurate": 18.0,
}
LEAGUE_AVG_GOALS = {
    "goals_pg":     1.10,
    "conversion":   10.5,   # % gols/chutes
    "xg_per_goal":  0.25,   # xG médio dos gols marcados
    "head_pct":     25.0,   # % gols de cabeça
}
FIELD_DARK = "#0a2412"
FIELD_MID  = "#0d3520"
FIELD_LINE = "#1a5a2e"
GOLD       = "#F5C200"


# ── Dados ─────────────────────────────────────────────────────────────────────

def load_data(team_key: str):
    hm = BASE / f"data/processed/2026/opponents/{team_key}/team_heatmap.json"
    ap = BASE / f"data/curated/opponents_2026/{team_key}/attack_profile.json"
    with open(hm, encoding="utf-8") as f:
        heatmap = json.load(f)
    with open(ap, encoding="utf-8") as f:
        profile = json.load(f)
    return heatmap, profile


def situation_groups(shots):
    mapping = {
        "regular": "Jogada Aberta", "assisted": "Jogada Aberta",
        "fast-break": "Contra-Ataque",
        "corner": "Bola Parada", "free-kick": "Bola Parada",
        "set-piece": "Bola Parada", "throw-in-set-piece": "Bola Parada",
        "penalty": "Pênalti",
    }
    c = Counter(mapping.get(s.get("situation", ""), None)
                for s in shots if s.get("situation") != "shootout")
    c.pop(None, None)
    total = sum(c.values()) or 1
    xg_by = {g: 0.0 for g in ["Jogada Aberta","Bola Parada","Contra-Ataque","Pênalti"]}
    for s in shots:
        g = mapping.get(s.get("situation", ""), None)
        if g and s.get("situation") != "shootout":
            xg_by[g] += float(s.get("xg") or 0)
    order = ["Jogada Aberta", "Bola Parada", "Contra-Ataque", "Pênalti"]
    return {g: {
        "n":   c.get(g, 0),
        "pct": round(c.get(g, 0) / total * 100),
        "xg":  xg_by[g],
        "xgps": round(xg_by[g] / c.get(g, 1), 2) if c.get(g) else 0.0,
    } for g in order}


def lateral_balance(points):
    if not points:
        return 33, 34, 33
    e = sum(1 for p in points if p["y"] < 33.33)
    d = sum(1 for p in points if p["y"] > 66.67)
    c = len(points) - e - d
    t = len(points)
    return round(e/t*100), round(c/t*100), round(d/t*100)


def depth_distribution(points):
    """5 faixas defensiva→ofensiva, filtrando cluster do goleiro."""
    bands = [0]*5; valid = 0
    for p in points:
        x, y = p["x"], p["y"]
        if x < 12 and 32 < y < 68:
            continue
        bands[min(int(x/20), 4)] += 1; valid += 1
    if not valid:
        return [20]*5
    return [round(b/valid*100, 1) for b in bands]


def top_zones(points, n=2):
    """Detecta zonas de maior concentração (ignora GK)."""
    valid = [(p["x"], p["y"]) for p in points
             if not (p["x"] < 12 and 32 < p["y"] < 68)]
    if not valid:
        return []

    hx_arr = np.array([p[0] for p in valid], float)
    hy_arr = np.array([p[1] for p in valid], float)
    xi = np.linspace(0, 100, 80)
    yi = np.linspace(0, 100, 80)
    xg, yg = np.meshgrid(xi, yi)
    try:
        kde = gaussian_kde(np.vstack([hx_arr, hy_arr]), bw_method=0.13)
        z = kde(np.vstack([yg.ravel(), xg.ravel()])).reshape(80, 80)
    except Exception:
        return []
    z = gaussian_filter(z, sigma=1.5)
    z = (z - z.min()) / (z.max() - z.min() + 1e-9)
    lm = maximum_filter(z, size=12) == z
    peaks = sorted(np.argwhere(lm & (z > 0.55)),
                   key=lambda p: z[p[0], p[1]], reverse=True)
    zones, used = [], []
    for p in peaks:
        iy, ix = p
        if any(abs(iy-u[0]) < 14 and abs(ix-u[1]) < 14 for u in used):
            continue
        used.append((iy, ix))
        hx_val = float(yi[iy])
        hy_val = float(xi[ix])
        if hx_val < 33:    depth = "Bloco Rec."
        elif hx_val < 52:  depth = "Meio-Campo"
        elif hx_val < 72:  depth = "Terço Final"
        else:              depth = "Área Rival"
        if hy_val < 30:    side = "ESQ"
        elif hy_val > 70:  side = "DIR"
        else:              side = "CTR"
        intens = round(float(z[iy, ix]) * 100)
        zones.append({"depth": depth, "side": side, "intens": intens,
                       "hx": hx_val, "hy": hy_val})
        if len(zones) >= n:
            break
    return zones


def build_synthesis(avgs, sits, lat_bal, depth_pcts):
    pos = avgs.get("possession", 50)
    style = ("posse equilibrada" if 47 <= pos <= 53
             else ("vocação reativa" if pos < 47 else "vocação propositiva"))
    open_play = sits["Jogada Aberta"]["pct"]
    sp = sits["Bola Parada"]["pct"]
    tr = sits["Contra-Ataque"]["pct"]
    e, c, d = lat_bal
    lat_max = max(e, c, d)
    lat_txt = (f"forte pelo corredor {'esquerdo' if e==lat_max else 'central' if c==lat_max else 'direito'} ({lat_max}%)"
               if lat_max > 38 else "distribuído pelos corredores")
    off = depth_pcts[3] + depth_pcts[4]
    mid = depth_pcts[2]
    def_pct = depth_pcts[0] + depth_pcts[1]
    depth_cl = (f", com pressão alta no campo ofensivo ({off:.0f}%)" if off >= 35
                else f", de bloco recuado ({def_pct:.0f}% no terço defensivo)" if def_pct > 40
                else f", apoiado no meio-campo ({mid:.0f}%)")
    sec = "bola parada" if sp > tr else "transição"
    sec_pct = max(sp, tr)
    return (f'Time de {style} ({pos:.0f}%), {lat_txt}{depth_cl}. '
            f'Ataque com <strong>{open_play}% via jogo corrido</strong> — '
            f'{sec} é a 2ª fonte ({sec_pct}%).')


# ── Heatmap como PNG base64 ───────────────────────────────────────────────────

def goal_stats(shots):
    """Calcula métricas de finalização a partir dos gols marcados."""
    goals = [s for s in shots if s.get("shot_type") == "goal"]
    n_goals = len(goals)
    n_shots = len(shots) or 1
    conversion = round(n_goals / n_shots * 100, 1)
    xg_avg = round(sum(float(g.get("xg") or 0) for g in goals) / (n_goals or 1), 2)
    from collections import Counter
    parts = Counter(g.get("body_part", "") for g in goals)
    foot = parts.get("right-foot", 0) + parts.get("left-foot", 0)
    head = parts.get("head", 0)
    return {
        "n": n_goals,
        "goals": goals,
        "conversion": conversion,
        "xg_per_goal": xg_avg,
        "foot_pct": round(foot / (n_goals or 1) * 100),
        "head_pct": round(head / (n_goals or 1) * 100),
    }


def _heatmap_png_b64(points, w=260, h=440, bw_method=0.11) -> str:
    """Renderiza KDE sobre campo vertical → PNG base64 (2× para tela retina)."""
    hx_arr = np.array([p["x"] for p in points], float)
    hy_arr = np.array([p["y"] for p in points], float)
    n = 100
    xi = np.linspace(0, 100, n)   # lateral
    yi = np.linspace(0, 100, n)   # profundidade (0=def, 100=atq)
    xg, yg = np.meshgrid(xi, yi)
    try:
        kde = gaussian_kde(np.vstack([hy_arr, hx_arr]), bw_method=bw_method)
        z = kde(np.vstack([xg.ravel(), yg.ravel()])).reshape(n, n)
    except Exception:
        z = np.zeros((n, n))
    z = gaussian_filter(z, sigma=1.2)
    z = (z - z.min()) / (z.max() - z.min() + 1e-9)

    dpi = 96
    fig, ax = plt.subplots(figsize=(w/dpi, h/dpi), dpi=dpi)
    fig.patch.set_facecolor(FIELD_DARK)
    ax.set_facecolor(FIELD_DARK)

    # Faixas de campo verticais
    for i in range(0, 100, 20):
        ax.add_patch(Rectangle((i, 0), 10, 100, fc=FIELD_MID, ec="none", alpha=0.35, zorder=1))

    # KDE — atenção: yi é profundidade (x-axis do pitch vertical), xi é lateral
    # No campo vertical (atq em cima): y-axis do plot = profundidade (0=def-baixo, 100=atq-cima)
    cmap = LinearSegmentedColormap.from_list("hm", [
        (0.00, "none"),
        (0.20, "#0a2d15"),
        (0.45, "#2a5c1e"),
        (0.68, "#9a7800"),
        (0.85, GOLD),
        (1.00, "#fff8b0"),
    ])
    ax.contourf(xi, yi, z, levels=22, cmap=cmap, alpha=0.88, zorder=2, vmin=0.05, vmax=1.0)

    # Linhas do campo
    lc = FIELD_LINE
    lw = 0.9
    ax.plot([0,100,100,0,0], [0,0,100,100,0], color=lc, lw=lw, zorder=5)
    ax.plot([0,100], [50,50], color=lc, lw=lw*0.8, zorder=5)
    ax.add_patch(plt.Circle((50,50), 9.15, color=lc, fill=False, lw=lw*0.7, zorder=5))
    ax.add_patch(Rectangle((29.84, 0),    40.32, 16.5, ec=lc, fc="none", lw=lw*0.8, zorder=5))
    ax.add_patch(Rectangle((29.84, 83.5), 40.32, 16.5, ec=lc, fc="none", lw=lw*0.8, zorder=5))
    ax.add_patch(Rectangle((41.34, 0),    17.32,  5.5, ec=lc, fc="none", lw=lw*0.6, zorder=5))
    ax.add_patch(Rectangle((41.34, 94.5), 17.32,  5.5, ec=lc, fc="none", lw=lw*0.6, zorder=5))
    ax.add_patch(Arc((50, 16.5), 18.3, 18.3, angle=0, theta1=37,  theta2=143, color=lc, lw=lw*0.7, zorder=5))
    ax.add_patch(Arc((50, 83.5), 18.3, 18.3, angle=0, theta1=217, theta2=323, color=lc, lw=lw*0.7, zorder=5))

    # Seta ATQ
    ax.annotate("", xy=(50, 97), xytext=(50, 90),
                arrowprops=dict(arrowstyle="-|>", color=GOLD, lw=0.9,
                                mutation_scale=6, alpha=0.85), zorder=6)

    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.set_aspect("auto"); ax.axis("off")
    plt.tight_layout(pad=0)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                pad_inches=0, facecolor=FIELD_DARK)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def _logo_b64(path: Path) -> str:
    if not HAS_PIL or not path.exists():
        return ""
    img = Image.open(path).convert("RGBA")
    img.thumbnail((120, 120), Image.LANCZOS)
    # BFS remove bg
    data = np.array(img, dtype=np.uint8)
    h, w = data.shape[:2]
    vis = np.zeros((h, w), bool)
    q = deque()
    for py in range(h):
        for px in (0, w-1):
            if not vis[py,px] and all(data[py,px,c]>230 for c in range(3)):
                q.append((py,px)); vis[py,px]=True
    for px in range(w):
        for py in (0, h-1):
            if not vis[py,px] and all(data[py,px,c]>230 for c in range(3)):
                q.append((py,px)); vis[py,px]=True
    while q:
        cy,cx=q.popleft(); data[cy,cx,3]=0
        for dy,dx in ((-1,0),(1,0),(0,-1),(0,1)):
            ny,nx=cy+dy,cx+dx
            if 0<=ny<h and 0<=nx<w and not vis[ny,nx] and all(data[ny,nx,c]>230 for c in range(3)):
                vis[ny,nx]=True; q.append((ny,nx))
    img2 = Image.fromarray(data,"RGBA")
    buf = io.BytesIO()
    img2.save(buf, "PNG")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


# ── HTML builder ──────────────────────────────────────────────────────────────

def _stat_card_html(label, value, ref, higher_good=True, fmt=".1f", unit=""):
    scale = ref * 2 if ref else 1
    fill_w = min(int(value / scale * 100), 100)
    marker = min(int(ref / scale * 100), 100)
    ratio = value / ref if ref else 1.0
    if ratio >= 1.10:
        badge_cls = "above"; badge_txt = "▲ Acima da liga"
        fill_color = ("#F5C200" if higher_good else "#E05A4A")
    elif ratio <= 0.90:
        badge_cls = "below"; badge_txt = "▼ Abaixo da liga"
        fill_color = ("#E05A4A" if higher_good else "#4CAF7D")
    else:
        badge_cls = "avg"; badge_txt = "≈ Na média"
        fill_color = "rgba(255,255,255,0.3)"
    val_str = f"{value:{fmt}}{unit}"
    ref_str = f"{ref:{fmt}}{unit}"
    return f"""
        <div class="stat-card">
          <div class="stat-label">{label}</div>
          <div class="stat-value">{val_str}</div>
          <div class="stat-bar-row">
            <div class="stat-compare-bar">
              <div class="stat-compare-fill" style="width:{fill_w}%;background:linear-gradient(90deg,{fill_color},{fill_color}cc);border-radius:2px;"></div>
              <div class="stat-compare-marker" style="left:{marker}%;"></div>
            </div>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span class="stat-badge {badge_cls}">{badge_txt}</span>
            <span class="stat-liga">liga: {ref_str}</span>
          </div>
        </div>"""


def _shot_row_html(name, data, color_cls, is_highlighted=False, unit="chutes"):
    pct  = data["pct"]
    n    = data["n"]
    xgps = data["xgps"]
    xg   = data["xg"]
    xg_col = "#4A90D9" if xg > 0 and (xgps > 0.15) else "rgba(255,255,255,0.25)"
    xg_arrow = " ↑" if xgps > 0.15 else ""
    pct_style = "" if pct >= 10 else 'font-size:18px;'
    xg_label = "xG/gol" if unit == "gols" else "xG/chute"
    return f"""
        <div class="shot-row">
          <div class="shot-header">
            <span class="shot-name">{name}</span>
            <div class="shot-meta">
              <span class="shot-pct" style="{pct_style}">{pct}%</span>
            </div>
          </div>
          <div class="shot-bar-track">
            <div class="shot-bar-fill {color_cls}" style="width:{max(pct,1)}%;{'min-width:6px;' if pct<2 else ''}"></div>
          </div>
          <div style="display:flex;justify-content:space-between;margin-top:2px;">
            <span style="font-size:11px;color:rgba(255,255,255,0.25);">{n} {unit}</span>
            <span style="font-size:11px;color:{xg_col};{'font-weight:600;' if xg_arrow else ''}">{xgps:.2f} {xg_label}{xg_arrow}</span>
          </div>
        </div>"""


def build_html(
    team_key="ceara",
    team_name="Ceará SC",
    team_id=2001,
    round_num=7,
    match_date="03/05",
    goals_mode=False,
) -> str:

    heatmap_data, profile = load_data(team_key)
    pts       = heatmap_data["points"]
    n_match   = heatmap_data.get("match_count", 0)
    shots     = profile.get("shots", [])
    avgs      = profile.get("averages", {})

    # Col 1 e Col 3 são sempre baseados no modo chutes (heatmap posicional + avgs)
    sits       = situation_groups(shots)
    lat_bal    = lateral_balance(pts)
    depth_pcts = depth_distribution(pts)
    zones      = top_zones(pts, n=2)
    hm_b64     = _heatmap_png_b64(pts)

    if goals_mode:
        # Filtra gols da Série B cruzando event_id com matches.csv do adversário
        import csv as _csv
        matches_path = BASE / f"data/curated/opponents_2026/{team_key}/matches.csv"
        sb_event_ids: set = set()
        if matches_path.exists():
            with open(matches_path, encoding="utf-8") as _f:
                for _r in _csv.DictReader(_f):
                    if "Série B" in (_r.get("competition_name") or "") or \
                       "Serie B" in (_r.get("competition_name") or ""):
                        sb_event_ids.add(str(_r["event_id"]))
        sb_goals = [s for s in shots
                    if s.get("shot_type") == "goal"
                    and str(s.get("event_id")) in sb_event_ids]
        # Conta só partidas da Série B que têm dados no attack_profile (já jogadas)
        sb_ids_with_data = {str(s.get("event_id")) for s in shots
                            if str(s.get("event_id")) in sb_event_ids}
        n_sb_matches = len(sb_ids_with_data) or len(sb_event_ids)
        gstats    = goal_stats(sb_goals if sb_goals else shots)
        goal_sits = situation_groups(sb_goals if sb_goals else shots)
        open_pct  = goal_sits["Jogada Aberta"]["pct"]
        sp_pct    = goal_sits["Bola Parada"]["pct"]
        synthesis = build_synthesis(avgs, sits, lat_bal, depth_pcts)  # mantém síntese de chutes
    else:
        goal_sits    = sits        # alias para f-string não falhar
        gstats       = {"n": 0}
        n_sb_matches = 0
        synthesis    = build_synthesis(avgs, sits, lat_bal, depth_pcts)

    # Valores extraídos
    pos_pct   = avgs.get("possession", 50.0)
    xg_pg     = avgs.get("expected_goals", 1.0)
    shots_pg  = avgs.get("shots_total", 10.0)
    lb_acc    = avgs.get("long_balls_accurate", 18.0)

    # Base64 assets
    hm_b64   = hm_b64  # já definido acima
    logo_b64 = _logo_b64(BASE / f"data/cache/logos/{team_id}.png")
    srl_b64  = _logo_b64(BASE / "sportrecifelab_avatar.png")

    # Corredor DOM
    e, c, d = lat_bal
    dom_idx   = [e, c, d].index(max(e, c, d))
    corr_names = ["ESQ", "CTR", "DIR"]
    corr_vals  = [e, c, d]

    # Faixas de profundidade: DEF / MEIO / ATQ
    dep_def  = round(depth_pcts[0] + depth_pcts[1])
    dep_meio = round(depth_pcts[2])
    dep_atq  = round(depth_pcts[3] + depth_pcts[4])
    dep_dom  = max(dep_def, dep_meio, dep_atq)

    def _depth_row(label, pct, color):
        is_dom = pct == dep_dom
        label_col = "#fff" if is_dom else "rgba(255,255,255,0.4)"
        pct_col   = color if is_dom else "rgba(255,255,255,0.5)"
        return f"""
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:5px;">
          <div style="font-family:'Barlow Condensed',sans-serif;font-size:9px;font-weight:700;
                      letter-spacing:1px;color:{label_col};width:28px;">{label}</div>
          <div style="flex:1;height:4px;background:rgba(255,255,255,0.08);border-radius:2px;overflow:hidden;">
            <div style="width:{pct}%;height:100%;background:{color};border-radius:2px;{'opacity:0.45;' if not is_dom else ''}"></div>
          </div>
          <div style="font-family:'Barlow Condensed',sans-serif;font-size:10px;font-weight:{'700' if is_dom else '400'};
                      color:{pct_col};width:28px;text-align:right;">{pct}%</div>
        </div>"""

    zone_blocks = f"""
        <div style="width:130px;margin-top:8px;">
          <div style="font-family:'Barlow Condensed',sans-serif;font-size:9px;font-weight:700;
                      letter-spacing:2px;color:rgba(255,255,255,0.25);text-transform:uppercase;
                      margin-bottom:8px;text-align:center;">Presença no Campo</div>
          {_depth_row("ATQ", dep_atq, "#F5C200")}
          {_depth_row("MEIO", dep_meio, "rgba(255,255,255,0.6)")}
          {_depth_row("DEF", dep_def, "#4A90D9")}
        </div>"""

    # Barra proporcional — usa goal_sits ou sits conforme modo
    _bar_sits  = goal_sits if goals_mode else sits
    sit_order  = ["Jogada Aberta","Bola Parada","Contra-Ataque","Pênalti"]
    sit_colors = ["#F5C200","#4A90D9","#E8622A","rgba(255,255,255,0.2)"]
    prop_bars = "".join(
        f'<div style="flex:{_bar_sits[g]["pct"]};background:{c};{("border-radius:3px 0 0 3px;" if i==0 else "border-radius:0 3px 3px 0;" if i==3 else "")}"></div>'
        for i,(g,c) in enumerate(zip(sit_order, sit_colors))
    )

    # Corredores HTML
    def corridor_html(label, pct, is_dom):
        col = "#F5C200" if is_dom else "rgba(255,255,255,0.7)"
        fill_col = "#F5C200" if is_dom else "rgba(255,255,255,0.3)"
        return f"""
            <div class="corridor-bar">
              <div class="corridor-pct" style="color:{col};">{pct}%</div>
              <div class="corridor-fill"><div class="corridor-fill-inner" style="width:{pct}%;background:{fill_col};"></div></div>
              <div class="corridor-label">{label}</div>
            </div>"""

    corridors_html = "".join(corridor_html(corr_names[i], corr_vals[i], i==dom_idx) for i in range(3))

    # Logo tag
    logo_img = (f'<img src="data:image/png;base64,{logo_b64}" style="width:56px;height:56px;object-fit:contain;">'
                if logo_b64 else "")
    srl_img = (f'<img src="data:image/png;base64,{srl_b64}" style="width:20px;height:20px;object-fit:contain;vertical-align:middle;margin-right:4px;opacity:0.6;">'
               if srl_b64 else "")

    html = f"""<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1200">
<title>Como o {team_name} Joga</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;800;900&family=Barlow:wght@400;500&display=swap" rel="stylesheet">
<style>
* {{ margin:0;padding:0;box-sizing:border-box; }}
body {{ background:#111111;display:flex;align-items:center;justify-content:center;min-height:100vh; }}

.card {{
  width:1200px;height:675px;background:#111111;
  display:grid;grid-template-rows:auto 1fr auto;
  position:relative;overflow:hidden;
}}
.header {{
  position:relative;z-index:1;display:flex;align-items:center;
  justify-content:space-between;padding:22px 32px 18px;
  border-bottom:1px solid rgba(255,255,255,0.07);
}}
.header-left {{ display:flex;flex-direction:column;gap:4px; }}
.label-como {{
  font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:600;
  letter-spacing:3px;color:rgba(255,255,255,0.35);text-transform:uppercase;
}}
.title {{
  font-family:'Barlow Condensed',sans-serif;font-size:46px;font-weight:900;
  color:#fff;line-height:1;letter-spacing:-0.5px;text-transform:uppercase;white-space:nowrap;
}}
.title span {{ color:#F5C200; }}
.header-center {{ display:flex;flex-direction:column;align-items:center;gap:4px; }}
.meta-badges {{ display:flex;gap:8px;align-items:center; }}
.badge {{
  font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:700;
  letter-spacing:1.5px;color:#F5C200;background:rgba(245,194,0,0.12);
  border:1px solid rgba(245,194,0,0.25);padding:3px 10px;border-radius:3px;text-transform:uppercase;
}}
.meta-sub {{ font-size:11px;color:rgba(255,255,255,0.3);letter-spacing:0.5px; }}
.header-right {{ display:flex;align-items:center;gap:16px; }}
.logo-placeholder {{
  width:60px;height:60px;border-radius:50%;background:#1e1e1e;
  border:2px solid rgba(245,194,0,0.3);display:flex;align-items:center;
  justify-content:center;overflow:hidden;
}}
.body {{
  position:relative;z-index:1;display:grid;
  grid-template-columns:196px 420px 1fr;gap:0;
}}
.col+.col {{ border-left:1px solid rgba(255,255,255,0.07); }}
.col {{ padding:18px 24px;display:flex;flex-direction:column;gap:14px; }}
.col-title {{
  font-family:'Barlow Condensed',sans-serif;font-size:10px;font-weight:700;
  letter-spacing:2.5px;color:rgba(255,255,255,0.3);text-transform:uppercase;margin-bottom:2px;
}}
.pitch-wrap {{ flex:1;display:flex;flex-direction:column;align-items:center;gap:12px; }}
.pitch {{
  width:130px;height:220px;position:relative;
  border:1.5px solid rgba(255,255,255,0.15);border-radius:4px;overflow:hidden;
  background:{FIELD_DARK};flex-shrink:0;
}}
.pitch::after {{
  content:'';position:absolute;top:50%;left:0;right:0;height:1px;
  background:rgba(255,255,255,0.1);transform:translateY(-50%);pointer-events:none;z-index:3;
}}
.pitch-center-circle {{
  position:absolute;width:36px;height:36px;border-radius:50%;
  border:1px solid rgba(255,255,255,0.1);top:50%;left:50%;
  transform:translate(-50%,-50%);z-index:3;pointer-events:none;
}}
.pitch-box-top {{
  position:absolute;top:0;left:50%;transform:translateX(-50%);
  width:70px;height:30px;border:1px solid rgba(255,255,255,0.1);border-top:none;z-index:3;
}}
.pitch-box-bot {{
  position:absolute;bottom:0;left:50%;transform:translateX(-50%);
  width:70px;height:30px;border:1px solid rgba(255,255,255,0.1);border-bottom:none;z-index:3;
}}
.zone-label {{
  position:absolute;font-family:'Barlow Condensed',sans-serif;font-size:9px;
  font-weight:700;letter-spacing:1.5px;color:rgba(255,255,255,0.55);text-transform:uppercase;z-index:4;
}}
.zone-label.atk {{ top:6px;right:6px; }}
.zone-label.def {{ bottom:6px;left:50%;transform:translateX(-50%); }}
.pitch-corridor {{ display:flex;gap:6px;width:100%;margin-top:2px; }}
.corridor-bar {{ flex:1;display:flex;flex-direction:column;align-items:center;gap:4px; }}
.corridor-fill {{ height:4px;width:100%;background:rgba(255,255,255,0.08);border-radius:2px;overflow:hidden; }}
.corridor-fill-inner {{ height:100%;border-radius:2px;background:#F5C200; }}
.corridor-label {{ font-size:10px;color:rgba(255,255,255,0.4);font-family:'Barlow Condensed',sans-serif;font-weight:600;letter-spacing:0.5px; }}
.corridor-pct {{ font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:700;color:rgba(255,255,255,0.7); }}
.shot-list {{ display:flex;flex-direction:column;gap:16px;flex:1; }}
.shot-row {{ display:flex;flex-direction:column;gap:6px; }}
.shot-header {{ display:flex;align-items:baseline;justify-content:space-between; }}
.shot-name {{
  font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:700;
  letter-spacing:1px;color:rgba(255,255,255,0.65);text-transform:uppercase;white-space:nowrap;
}}
.shot-meta {{ display:flex;gap:12px;align-items:baseline; }}
.shot-pct {{ font-family:'Barlow Condensed',sans-serif;font-size:22px;font-weight:800;color:#fff;line-height:1; }}
.shot-bar-track {{ height:6px;background:rgba(255,255,255,0.07);border-radius:3px;overflow:hidden; }}
.shot-bar-fill {{ height:100%;border-radius:3px; }}
.color-yellow {{ background:#F5C200; }}
.color-blue   {{ background:#4A90D9; }}
.color-orange {{ background:#E8622A; }}
.color-gray   {{ background:rgba(255,255,255,0.25); }}
.shot-divider {{ height:1px;background:rgba(255,255,255,0.05); }}
.stat-grid {{ display:grid;grid-template-columns:1fr 1fr;gap:12px;flex:1; }}
.stat-card {{
  background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.07);
  border-radius:6px;padding:14px 16px;display:flex;flex-direction:column;gap:6px;
}}
.stat-label {{
  font-family:'Barlow Condensed',sans-serif;font-size:10px;font-weight:700;
  letter-spacing:2px;color:rgba(255,255,255,0.3);text-transform:uppercase;
}}
.stat-value {{
  font-family:'Barlow Condensed',sans-serif;font-size:40px;font-weight:900;
  color:#fff;line-height:1;letter-spacing:-1px;
}}
.stat-bar-row {{ display:flex;flex-direction:column;gap:4px; }}
.stat-compare-bar {{
  height:3px;background:rgba(255,255,255,0.08);border-radius:2px;
  position:relative;overflow:visible;
}}
.stat-compare-fill {{ height:100%;border-radius:2px;position:absolute;top:0;left:0; }}
.stat-compare-marker {{ position:absolute;top:-2px;width:2px;height:7px;background:rgba(255,255,255,0.3);border-radius:1px; }}
.stat-badge {{ font-family:'Barlow Condensed',sans-serif;font-size:10px;font-weight:700;letter-spacing:0.5px;display:flex;align-items:center;gap:4px; }}
.stat-badge.above {{ color:#4CAF7D; }}
.stat-badge.avg   {{ color:rgba(255,255,255,0.35); }}
.stat-badge.below {{ color:#E05A4A; }}
.stat-liga {{ font-size:10px;color:rgba(255,255,255,0.2); }}
.footer {{
  position:relative;z-index:1;display:flex;align-items:center;
  justify-content:space-between;padding:12px 32px;
  border-top:1px solid rgba(255,255,255,0.07);background:rgba(0,0,0,0.2);
}}
.synthesis {{ font-size:12px;color:rgba(255,255,255,0.45);line-height:1.5;max-width:820px;font-style:italic; }}
.synthesis strong {{ color:rgba(255,255,255,0.7);font-style:normal; }}
.watermark {{ font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:600;letter-spacing:1px;color:rgba(255,255,255,0.2);white-space:nowrap; }}
.watermark span {{ color:#F5C200; }}
</style>
</head><body>
<div class="card">

  <div class="header">
    <div class="header-left">
      <span class="label-como">Como o</span>
      <div class="title">{team_name}&nbsp;<span>Joga</span></div>
    </div>
    <div class="header-center">
      <div class="meta-badges">
        <span class="badge">Série B 2026</span>
        <span class="badge">R{round_num}</span>
        <span class="badge">{match_date}</span>
      </div>
      <div class="meta-sub">{n_match} partidas · {len(shots)} chutes analisados</div>
    </div>
    <div class="header-right">
      <div class="logo-placeholder">{logo_img}</div>
    </div>
  </div>

  <div class="body">

    <!-- COL 1: ZONAS DE ATUAÇÃO -->
    <div class="col">
      <div class="col-title">Zonas de Atuação</div>
      <div class="pitch-wrap">
        <div class="pitch">
          <img src="data:image/png;base64,{hm_b64}"
               style="position:absolute;inset:0;width:100%;height:100%;z-index:1;object-fit:fill;">
          <div class="zone-label atk">ATQ</div>
          <div class="zone-label def">DEF</div>
        </div>

        <div style="width:130px;">
          <div style="font-family:'Barlow Condensed',sans-serif;font-size:9px;font-weight:700;letter-spacing:2px;color:rgba(255,255,255,0.25);text-transform:uppercase;margin-bottom:8px;text-align:center;">Distribuição</div>
          <div class="pitch-corridor">{corridors_html}</div>
        </div>

        {zone_blocks}
      </div>
    </div>

    <!-- COL 2: ORIGEM DOS CHUTES / GOLS -->
    <div class="col">
      <div class="col-title">{"Origem dos Gols · Série B" if goals_mode else "Origem dos Chutes"}</div>
      <div class="shot-list">
        {_shot_row_html("Jogada Aberta", goal_sits["Jogada Aberta"] if goals_mode else sits["Jogada Aberta"], "color-yellow", unit="gols" if goals_mode else "chutes")}
        <div class="shot-divider"></div>
        {_shot_row_html("Bola Parada", goal_sits["Bola Parada"] if goals_mode else sits["Bola Parada"], "color-blue", unit="gols" if goals_mode else "chutes")}
        <div class="shot-divider"></div>
        {_shot_row_html("Contra-Ataque", goal_sits["Contra-Ataque"] if goals_mode else sits["Contra-Ataque"], "color-orange", unit="gols" if goals_mode else "chutes")}
        <div class="shot-divider"></div>
        {_shot_row_html("Pênalti", goal_sits["Pênalti"] if goals_mode else sits["Pênalti"], "color-gray", unit="gols" if goals_mode else "chutes")}

        <div style="margin-top:auto;">
          <div style="font-family:'Barlow Condensed',sans-serif;font-size:9px;font-weight:700;letter-spacing:2px;color:rgba(255,255,255,0.2);text-transform:uppercase;margin-bottom:6px;">
            {"Proporção total · " + str(gstats["n"]) + " gols / " + str(n_sb_matches) + " jogos" if goals_mode else "Proporção total"}
          </div>
          <div style="display:flex;height:8px;border-radius:4px;overflow:hidden;gap:2px;">{prop_bars}</div>
        </div>
      </div>
    </div>

    <!-- COL 3: PERFIL OFENSIVO (sempre igual, independente do modo) -->
    <div class="col">
      <div class="col-title">Perfil Ofensivo · por jogo vs Série B</div>
      <div class="stat-grid">
        {_stat_card_html("xG / Jogo", xg_pg, LEAGUE_AVG["expected_goals"], True, ".2f")}
        {_stat_card_html("Posse de Bola", pos_pct, LEAGUE_AVG["possession"], True, ".0f", "%")}
        {_stat_card_html("Chutes / Jogo", shots_pg, LEAGUE_AVG["shots_total"], True, ".1f")}
        {_stat_card_html("Bolas Longas", lb_acc, LEAGUE_AVG["long_balls_accurate"], True, ".1f")}
      </div>
    </div>

  </div>

  <div class="footer">
    <div class="synthesis"><strong>Síntese:</strong> {synthesis}</div>
    <div class="watermark">{srl_img}<span>@</span>SportRecifeLab</div>
  </div>

</div>
</body></html>"""
    return html


# ── Render PNG via Selenium ───────────────────────────────────────────────────

def render_to_png(html: str, output_path: Path, width=1200, height=675) -> None:
    import tempfile, os
    from selenium import webdriver
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By

    with tempfile.NamedTemporaryFile(mode="w", suffix=".html",
                                     encoding="utf-8", delete=False) as f:
        f.write(html); tmp = f.name

    opts = webdriver.EdgeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument(f"--window-size={width},{height}")
    opts.add_argument("--force-device-scale-factor=1")
    driver = webdriver.Edge(options=opts)
    try:
        driver.get(f"file:///{tmp.replace(chr(92), '/')}")
        # Aguarda fontes e imagens carregarem
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "card"))
        )
        import time; time.sleep(2.5)  # garante render completo das fontes
        # Ajusta viewport para garantir que o card caiba sem scroll
        driver.set_window_size(width + 200, height + 200)
        time.sleep(0.5)
        card = driver.find_element(By.CLASS_NAME, "card")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        card.screenshot(str(output_path))
        # Redimensiona para exatamente 1200×675 se necessário
        from PIL import Image as _Img
        img = _Img.open(str(output_path))
        if img.size != (width, height):
            img = img.resize((width, height), _Img.LANCZOS)
            img.save(str(output_path))
    finally:
        driver.quit()
        os.unlink(tmp)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--team-key",   default="ceara")
    p.add_argument("--team-name",  default="Ceará SC")
    p.add_argument("--team-id",    type=int, default=2001)
    p.add_argument("--round",      type=int, default=7, dest="round_num")
    p.add_argument("--date",       default="03/05")
    p.add_argument("--goals",      action="store_true", help="Modo origem dos gols")
    p.add_argument("--out",        default=None)
    args = p.parse_args()

    default_out = (
        "pending_posts/2026-05-03_raio-x-ceara/08_como_marca_gols.png"
        if args.goals else
        "pending_posts/2026-05-03_raio-x-ceara/07_como_joga_v2.png"
    )
    if args.out is None:
        args.out = default_out

    print(f"Gerando HTML para {args.team_name} [{'gols' if args.goals else 'chutes'}]...")
    html = build_html(args.team_key, args.team_name, args.team_id,
                      args.round_num, args.date, goals_mode=args.goals)

    out = Path(args.out)
    html_path = out.with_suffix(".html")
    html_path.parent.mkdir(parents=True, exist_ok=True)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  HTML: {html_path}")

    print("  Renderizando via Selenium Edge...")
    render_to_png(html, out)
    print(f"  PNG: {out}")
