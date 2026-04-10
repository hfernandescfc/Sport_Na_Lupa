"""
generate_match_cards.py — @SportRecifeLab
==========================================

Gera os 4 cards de análise de uma partida a partir de um dicionário
``match_data`` no formato descrito abaixo.

Uso rápido
----------
    from generate_match_cards import generate_match_cards

    cards = generate_match_cards(match_data)
    # retorna lista de PIL.Image prontas para salvar ou postar

    # ou salvar diretamente em disco:
    generate_match_cards(match_data, output_dir="pending_posts/2026-04-10_sport-csa/")

Formato de entrada (match_data)
--------------------------------
{
  "home_team":   "SPORT",          # nome do time mandante
  "away_team":   "LONDRINA",       # nome do time visitante
  "score":       [2, 1],           # [home, away]
  "date":        "04.04.2026",
  "round":       "R3",
  "competition": "SÉRIE B 2026",
  "status":      "completed",      # "completed" | "in_progress" | "scheduled"
  "model_image": "Spt_Ars.jpeg",   # opcional — foto do jogo para o header do Card 1

  # Estatísticas do time — índice 0 = home, 1 = away
  "stats": {
      "possession":       [55.0, 45.0],   # % — deve somar 100
      "shots_total":      [12, 8],
      "shots_on_target":  [5, 3],
      "xg":               [1.42, 0.74],
      "corners":          [6, 3],
      "fouls":            [11, 14],
      "passes_total":     [430, 310],
      "passes_accuracy":  [82.0, 74.0],   # %
      "tackles":          [18, 22],
      "yellow_cards":     [1, 3],
      "red_cards":        [0, 0],
  },

  # Finalizações individuais
  "shots": [
    {
      "team":   "home",       # "home" | "away"
      "player": "PEROTTI",
      "minute": 43,
      "type":   "save",       # "goal" | "save" | "block" | "miss"
      "xg":     0.173,        # pode ser None se não disponível
      "coord":  (5.4, 60.5),  # (x, y) SofaScore %: x=dist.do gol, y=lateral
    },
    ...
  ],

  # Série temporal de momentos de ataque (SofaScore "attack momentum")
  # value: 0‒100 — >50 domínio do mandante, <50 domínio do visitante
  "momentum": [
    {"minute": 1,  "value": 60},
    {"minute": 2,  "value": 55},
    ...
  ]
}
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
import numpy as np

try:
    from scipy.interpolate import make_interp_spline
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    from mplsoccer import Pitch
    HAS_MPLSOCCER = True
except ImportError:
    HAS_MPLSOCCER = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ─── Paleta visual @SportRecifeLab ───────────────────────────────────────────
BG          = "#0d0d0d"
PITCH_COLOR = "#0e3d1f"
LINE_COLOR  = "#2a7a3a"
YELLOW      = "#F5C400"
RED         = "#E04040"
BLUE        = "#4A90D9"
GREEN       = "#4CAF50"
GRAY        = "#444444"
LGRAY       = "#AAAAAA"
DGRAY       = "#222222"
WHITE       = "#FFFFFF"

# Cores dos tipos de finalização
SHOT_COLOR  = {"goal": YELLOW, "save": BLUE,  "block": RED,   "miss": LGRAY}
SHOT_LABEL  = {"goal": "GOL",  "save": "DEF.", "block": "BLQ.", "miss": "FORA"}
SHOT_MARKER = {"goal": "*",    "save": "o",   "block": "X",   "miss": "^"}
SHOT_MS     = {"goal": 280,    "save": 130,   "block": 130,   "miss": 110}

LOGO_PATH = Path(__file__).parent / "sportrecifelab_avatar.png"

# ─── Helpers internos ────────────────────────────────────────────────────────

def _fig_to_pil(fig: plt.Figure) -> "Image.Image":
    """Converte matplotlib Figure em PIL Image sem gravar em disco."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=fig.dpi,
                bbox_inches="tight", facecolor=BG, edgecolor="none")
    buf.seek(0)
    return Image.open(buf).copy()


def _footer(fig: plt.Figure, ax_ref: plt.Axes) -> None:
    """Rodapé padrão: logo + handle + fonte de dados."""
    if LOGO_PATH.exists() and HAS_PIL:
        logo_arr = np.array(
            Image.open(LOGO_PATH).convert("RGBA").resize((40, 40), Image.LANCZOS)
        )
        ab = AnnotationBbox(
            OffsetImage(logo_arr, zoom=1.0),
            (0.07, 0.026), xycoords="figure fraction",
            frameon=False, zorder=10,
        )
        ax_ref.add_artist(ab)

    fig.text(0.14, 0.026, "@SportRecifeLab",
             color=YELLOW, fontsize=8, fontfamily="Franklin Gothic Heavy",
             fontweight="bold", ha="left", va="center")
    fig.text(0.97, 0.026, "Dados: SofaScore",
             color=LGRAY, fontsize=7, fontfamily="Arial",
             ha="right", va="center")


def _header(fig: plt.Figure, md: dict) -> None:
    """Cabeçalho padrão: competição + partida + placar + data."""
    home  = md.get("home_team", "MANDANTE").upper()
    away  = md.get("away_team", "VISITANTE").upper()
    score = md.get("score", [0, 0])
    rnd   = md.get("round", "")
    comp  = md.get("competition", "")
    date  = md.get("date", "")
    status = md.get("status", "completed")

    # Linha de contexto (competição + rodada)
    ctx = f"{comp}  ·  {rnd}" if rnd else comp
    fig.text(0.50, 0.977, ctx.upper(),
             color=YELLOW, fontsize=8, fontweight="bold",
             fontfamily="Franklin Gothic Heavy", ha="center", va="center")

    # Placar principal
    score_str = f"{home}  {score[0]} × {score[1]}  {away}"
    if status == "in_progress":
        score_str += "  ▶"
    fig.text(0.50, 0.955, score_str,
             color=WHITE, fontsize=14, fontweight="black",
             fontfamily="Franklin Gothic Heavy", ha="center", va="center",
             path_effects=[pe.withStroke(linewidth=2, foreground=BG)])

    # Data
    fig.text(0.50, 0.936, date,
             color=LGRAY, fontsize=7.5, fontfamily="Arial",
             ha="center", va="center")


def _to_sb_home(x_ss: float, y_ss: float) -> tuple[float, float]:
    """Coordenadas SofaScore → StatsBomb para o time mandante (ataca a direita).

    SofaScore: x=0 perto do gol adversário, y=0 lateral esquerda.
    StatsBomb: x=120 = gol direito, y=0 = inferior.
    """
    return 120 - (x_ss / 100 * 120), (y_ss / 100 * 80)


def _to_sb_away(x_ss: float, y_ss: float) -> tuple[float, float]:
    """Coordenadas SofaScore → StatsBomb para o time visitante (ataca a esquerda)."""
    return x_ss / 100 * 120, (100 - y_ss) / 100 * 80


# ─── CARD 1 — Stats do jogo ──────────────────────────────────────────────────

def _build_stats_rows(stats: dict, shots: list | None = None) -> list[tuple[str, float, float, str]]:
    """Monta linhas normalizadas para o card de stats.

    Retorna lista de (label, valor_home, valor_away, tipo) onde tipo é:
      'pct'  — barra bilateral proporcional ao valor (0-100)
      'abs'  — barra bilateral proporcional ao máximo entre os dois
      'raw'  — apenas exibir o número, sem barra

    Field Tilt (Presença Ofensiva):
      Aceita ``stats["field_tilt"] = [home_pct, away_pct]`` explicitamente.
      Fallback: estimado a partir de ``shots`` com coord x < 25 (chutes próximos
      do gol = finalizações no terço final). Se não houver dados, omite a linha.
    """
    rows: list[tuple[str, float, float, str]] = []

    def safe(key: str, idx: int) -> float:
        vals = stats.get(key, [0, 0])
        try:
            return float(vals[idx]) if vals[idx] is not None else 0.0
        except (TypeError, IndexError):
            return 0.0

    # ── Field Tilt (Presença Ofensiva) ──────────────────────────────────────
    # Calculado antes para aparecer no topo da lista.
    if "field_tilt" in stats:
        ft_h, ft_a = safe("field_tilt", 0), safe("field_tilt", 1)
    elif shots:
        # Estimativa: chutes com x < 25 (dentro dos ~25% finais do campo)
        h_att = sum(1 for s in shots if s.get("team") == "home"
                    and (s.get("coord") or (100,))[0] < 25)
        a_att = sum(1 for s in shots if s.get("team") == "away"
                    and (s.get("coord") or (100,))[0] < 25)
        total_att = h_att + a_att
        if total_att > 0:
            ft_h = h_att / total_att * 100
            ft_a = a_att / total_att * 100
        else:
            ft_h = ft_a = 0.0
    else:
        ft_h = ft_a = 0.0

    # Ordem de exibição — Field Tilt sempre no topo se disponível
    config = [
        ("PRESENÇA OFENSIVA", None,               "pct"),   # field tilt especial
        ("POSSE DE BOLA",     "possession",        "pct"),
        ("xG",                "xg",               "abs"),
        ("CHUTES",            "shots_total",      "abs"),
        ("CHUTES NO GOL",     "shots_on_target",  "abs"),
        ("PASSES",            "passes_total",     "abs"),
        ("ACERTO DE PASSES",  "passes_accuracy",  "pct"),
        ("ESCANTEIOS",        "corners",          "abs"),
        ("FALTAS",            "fouls",            "abs"),
        ("DESARMES",          "tackles",          "abs"),
        ("CARTÕES AM.",       "yellow_cards",     "raw"),
        ("CARTÕES VM.",       "red_cards",        "raw"),
    ]

    for label, key, kind in config:
        if key is None:
            # Field tilt — só inclui se tem dado
            if ft_h > 0 or ft_a > 0:
                rows.append((label, ft_h, ft_a, kind))
        else:
            h, a = safe(key, 0), safe(key, 1)
            if h > 0 or a > 0:
                rows.append((label, h, a, kind))

    return rows


def generate_card_stats(match_data: dict) -> "Image.Image":
    """CARD 1 — comparação de estatísticas da partida.

    Design mobile-first: barras finas arredondadas (via ax.plot com
    solid_capstyle='round'), paleta suavizada, escudos dos times no topo,
    Field Tilt como primeira métrica de destaque.

    Novos campos opcionais em match_data:
      ``home_logo``  — path para PNG/JPEG do escudo do mandante
      ``away_logo``  — path para PNG/JPEG do escudo do visitante

    Se ``model_image`` estiver definido, é usado como faixa decorativa
    no topo do card, atrás do cabeçalho de texto.
    """
    # ── Paleta específica do Card 1 ──────────────────────────────────────────
    # Cores mais suaves e harmoniosas que a paleta global
    C_HOME       = "#E8B84B"   # âmbar dourado — mais quente e legível que #F5C400
    C_AWAY       = "#5B9BD5"   # azul aço — menos frio que #4A90D9
    C_HOME_WIN   = "#F0DD80"   # valor em destaque quando mandante vence métrica
    C_AWAY_WIN   = "#90C4F0"   # valor em destaque quando visitante vence métrica
    C_TRACK      = "#1E1E1E"   # trilho de fundo das barras — discreto no BG escuro
    C_LABEL      = "#9A9A9A"   # label central da métrica
    C_SEP        = "#2A2A2A"   # linha separadora entre rows
    C_NAME_HOME  = C_HOME
    C_NAME_AWAY  = C_AWAY

    stats  = match_data.get("stats", {})
    shots  = match_data.get("shots", [])
    rows   = _build_stats_rows(stats, shots)
    n      = len(rows)

    # ── Figura ───────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(7.0, 8.5), dpi=130)
    fig.patch.set_facecolor(BG)

    # Área de stats: deixa espaço para o header (_header ocupa ~0.936-0.977)
    ax_top    = 0.910
    ax_bottom = 0.065
    ax = fig.add_axes([0.04, ax_bottom, 0.92, ax_top - ax_bottom])
    ax.set_facecolor(BG)
    ax.axis("off")

    # ── Coordenadas do eixo ───────────────────────────────────────────────────
    # Reserva espaço extra no topo para logos + nomes dos times
    LOGO_ZONE  = 2.2   # unidades de y reservadas acima das linhas de stats
    ax.set_xlim(-1.0, 1.0)
    ax.set_ylim(-0.5, n + LOGO_ZONE)

    bar_max = 0.84    # extensão máxima de cada barra (em unidades x)
    val_x   = 0.97   # posição x dos valores numéricos (borda)

    # ── Calcular linewidth das barras em pontos ───────────────────────────────
    # Garante que as barras tenham ~0.22 data units de altura visual,
    # convertendo para pontos com base no tamanho físico dos eixos.
    fig_h_in     = 8.5
    ax_h_frac    = ax_top - ax_bottom
    ax_h_in      = fig_h_in * ax_h_frac
    y_range      = n + LOGO_ZONE + 0.5
    bar_lw       = max(5.5, round((0.22 / y_range) * ax_h_in * 72, 1))

    # ── Escudos e nomes dos times ─────────────────────────────────────────────
    home_name  = match_data.get("home_team", "MANDANTE").upper()
    away_name  = match_data.get("away_team", "VISITANTE").upper()
    logo_y     = n + LOGO_ZONE - 0.55   # centro vertical dos logos
    name_y     = n + LOGO_ZONE - 1.30   # linha dos nomes

    def _load_logo(path_or_none, size: int = 52) -> "np.ndarray | None":
        """Carrega e redimensiona logo; retorna array RGBA ou None."""
        if not path_or_none or not HAS_PIL:
            return None
        p = Path(path_or_none)
        if not p.exists():
            return None
        try:
            img = Image.open(p).convert("RGBA").resize((size, size), Image.LANCZOS)
            return np.array(img)
        except Exception:
            return None

    home_logo_arr = _load_logo(match_data.get("home_logo"))
    away_logo_arr = _load_logo(match_data.get("away_logo"))

    logo_x_home = -0.68   # posição x do centro do logo mandante
    logo_x_away =  0.68   # posição x do centro do logo visitante

    if home_logo_arr is not None:
        ab = AnnotationBbox(
            OffsetImage(home_logo_arr, zoom=1.0),
            (logo_x_home, logo_y), xycoords="data",
            frameon=False, zorder=6,
        )
        ax.add_artist(ab)
    if away_logo_arr is not None:
        ab = AnnotationBbox(
            OffsetImage(away_logo_arr, zoom=1.0),
            (logo_x_away, logo_y), xycoords="data",
            frameon=False, zorder=6,
        )
        ax.add_artist(ab)

    # Nomes dos times abaixo dos logos
    ax.text(logo_x_home, name_y, home_name,
            color=C_NAME_HOME, fontsize=10.5, fontfamily="Franklin Gothic Heavy",
            fontweight="bold", ha="center", va="top", zorder=5)
    ax.text(logo_x_away, name_y, away_name,
            color=C_NAME_AWAY, fontsize=10.5, fontfamily="Franklin Gothic Heavy",
            fontweight="bold", ha="center", va="top", zorder=5)

    # Linha separadora entre zona de logos e zona de stats
    sep_y = n + LOGO_ZONE - 1.85
    ax.plot([-0.97, 0.97], [sep_y, sep_y],
            color=C_SEP, linewidth=0.8, alpha=0.7, zorder=2)

    # ── Linhas de estatísticas ────────────────────────────────────────────────
    for i, (label, h_val, a_val, kind) in enumerate(reversed(rows)):
        y = i   # linha de baixo para cima (row 0 = última da lista = topo visual)

        # Normalização da largura das barras
        if kind == "pct":
            total = h_val + a_val
            if total > 0:
                h_bar = (h_val / total) * bar_max
                a_bar = (a_val / total) * bar_max
            else:
                h_bar = a_bar = 0.0
        elif kind == "abs":
            mx    = max(h_val, a_val, 1e-9)
            h_bar = (h_val / mx) * bar_max * 0.88
            a_bar = (a_val / mx) * bar_max * 0.88
        else:  # "raw" — sem barra
            h_bar = a_bar = 0.0

        # Trilho de fundo (full-width, discreto) — indica o espaço disponível
        if h_bar > 0 or a_bar > 0:
            ax.plot([-bar_max, 0], [y, y],
                    color=C_TRACK, linewidth=bar_lw,
                    solid_capstyle="round", zorder=1)
            ax.plot([0, bar_max], [y, y],
                    color=C_TRACK, linewidth=bar_lw,
                    solid_capstyle="round", zorder=1)

        # Barra mandante — parte do centro para a esquerda
        if h_bar > 0:
            ax.plot([0, -h_bar], [y, y],
                    color=C_HOME, linewidth=bar_lw,
                    solid_capstyle="round", alpha=0.82, zorder=3)

        # Barra visitante — parte do centro para a direita
        if a_bar > 0:
            ax.plot([0, a_bar], [y, y],
                    color=C_AWAY, linewidth=bar_lw,
                    solid_capstyle="round", alpha=0.82, zorder=3)

        # Label central da métrica (sobreposto às barras, com halo escuro)
        ax.text(0, y, label,
                color=C_LABEL, fontsize=6.8, fontfamily="Arial",
                ha="center", va="center", zorder=5,
                path_effects=[pe.withStroke(linewidth=4, foreground=BG)])

        # ── Valores numéricos ────────────────────────────────────────────────
        # Formatação: % para tipo pct, 2 casas decimais para xG (<10), inteiro demais
        def _fmt(v: float, k: str) -> str:
            if k == "pct":
                return f"{v:.0f}%"
            if k == "abs" and v < 10:
                return f"{v:.2f}"
            return f"{v:.0f}"

        h_display = _fmt(h_val, kind)
        a_display = _fmt(a_val, kind)

        # Vencedor da métrica recebe cor de destaque; perdedor recebe branco suave
        h_wins = h_val >= a_val
        ax.text(-val_x, y, h_display,
                color=C_HOME_WIN if h_wins else "#707070",
                fontsize=11.5, fontfamily="Franklin Gothic Heavy",
                fontweight="bold", ha="left", va="center", zorder=5)
        ax.text(val_x, y, a_display,
                color=C_AWAY_WIN if not h_wins else "#707070",
                fontsize=11.5, fontfamily="Franklin Gothic Heavy",
                fontweight="bold", ha="right", va="center", zorder=5)

        # Linha divisória tênue entre linhas (exceto última)
        if i < n - 1:
            ax.plot([-0.97, 0.97], [y + 0.5, y + 0.5],
                    color=C_SEP, linewidth=0.5, alpha=0.6, zorder=1)

    _header(fig, match_data)
    _footer(fig, ax)

    img = _fig_to_pil(fig)
    plt.close(fig)
    return img


# ─── CARD 2 — Evolução do xG Acumulado ───────────────────────────────────────

def generate_card_xg_timeline(match_data: dict) -> "Image.Image":
    """CARD 2 — xG acumulado ao longo do tempo para ambos os times.

    Linha amarela = mandante, linha azul = visitante.
    Marcadores nos eventos de gol (estrela) e demais finalizações.
    Suporta jogo em andamento (dados parciais): o eixo X vai até
    o último minuto registrado + margem, e um indicador "▶ AO VIVO"
    aparece no título se status == 'in_progress'.
    """
    shots  = match_data.get("shots", [])
    status = match_data.get("status", "completed")
    score  = match_data.get("score", [0, 0])

    # Ordena por minuto (tolera desordem)
    home_shots = sorted(
        [s for s in shots if s.get("team") == "home"],
        key=lambda s: s.get("minute", 0)
    )
    away_shots = sorted(
        [s for s in shots if s.get("team") == "away"],
        key=lambda s: s.get("minute", 0)
    )

    def _cum_xg(shot_list: list) -> tuple[list[int], list[float]]:
        """Retorna (minutos, xg_acumulado) incluindo ponto inicial em 0."""
        mins, acc = [0], [0.0]
        running = 0.0
        for s in shot_list:
            xg = s.get("xg") or 0.0
            running += xg
            mins.append(s.get("minute", 0))
            acc.append(running)
        return mins, acc

    h_mins, h_xg = _cum_xg(home_shots)
    a_mins, a_xg = _cum_xg(away_shots)

    # Limite do eixo X
    all_mins = [s.get("minute", 0) for s in shots]
    max_min  = max(all_mins, default=90)
    x_max    = max(max_min + 3, 93)  # margem + ao menos 90'

    fig = plt.figure(figsize=(7.0, 8.5), dpi=130)
    fig.patch.set_facecolor(BG)

    gs = fig.add_gridspec(1, 1, left=0.10, right=0.97,
                          top=0.900, bottom=0.085)
    ax = fig.add_subplot(gs[0])
    ax.set_facecolor(BG)

    # ── Step lines ─────────────────────────────────────────────────────────
    def _step_xy(mins, xgs):
        """Expande pontos em step-chart (patamar sobe no minuto do evento)."""
        sx, sy = [0], [0.0]
        for i in range(1, len(mins)):
            sx += [mins[i], mins[i]]
            sy += [sy[-1], xgs[i]]
        return sx, sy

    h_sx, h_sy = _step_xy(h_mins, h_xg)
    a_sx, a_sy = _step_xy(a_mins, a_xg)

    # Estende as linhas até x_max para que não terminem no último chute
    if h_sx[-1] < x_max:
        h_sx.append(x_max); h_sy.append(h_sy[-1])
    if a_sx[-1] < x_max:
        a_sx.append(x_max); a_sy.append(a_sy[-1])

    ax.plot(h_sx, h_sy, color=YELLOW, linewidth=2.0,
            alpha=0.90, zorder=3, solid_capstyle="round", label=match_data.get("home_team", "Mandante"))
    ax.fill_between(h_sx, h_sy, alpha=0.12, color=YELLOW, zorder=2)

    ax.plot(a_sx, a_sy, color=BLUE, linewidth=2.0,
            alpha=0.90, zorder=3, solid_capstyle="round", label=match_data.get("away_team", "Visitante"))
    ax.fill_between(a_sx, a_sy, alpha=0.10, color=BLUE, zorder=2)

    # ── Marcadores de gol no placar ─────────────────────────────────────────
    # Linha de referência 1 xG
    y_max_val = max(max(h_xg, default=0), max(a_xg, default=0), 1.1)
    ax.axhline(1.0, color=LGRAY, linewidth=0.7, linestyle="--",
               alpha=0.4, zorder=1)
    ax.text(x_max - 0.5, 1.015, "1 xG",
            color=LGRAY, fontsize=6, fontfamily="Arial", ha="right", va="bottom")

    # ── Marcadores de gol ───────────────────────────────────────────────────
    def _plot_shot_markers(shot_list, all_shots_sorted, color, xg_acc):
        """Plota marcadores apenas nos eventos de gol.

        Labels com menos de 8 minutos de distância entre si são alternados
        acima/abaixo para evitar sobreposição.
        """
        running = 0.0
        shot_xg_by_min: dict[int, float] = {}
        for s in all_shots_sorted:
            xg = s.get("xg") or 0.0
            running += xg
            shot_xg_by_min[s.get("minute", 0)] = running

        goals = [s for s in shot_list if s.get("type") == "goal"]

        for idx, s in enumerate(goals):
            m    = s.get("minute", 0)
            xg   = s.get("xg") or 0.0
            y_pt = shot_xg_by_min.get(m, 0.0)

            ax.scatter(m, y_pt, s=SHOT_MS["goal"], marker=SHOT_MARKER["goal"],
                       color=color, edgecolors=WHITE, linewidths=0.7, zorder=5)

            player = s.get("player", "")
            lbl = f"{m}' {player}\n+{xg:.3f} xG" if player else f"{m}'\n+{xg:.3f} xG"

            # Verifica proximidade com o gol anterior para alternar posição
            prev_min = goals[idx - 1].get("minute", 0) if idx > 0 else -99
            too_close = abs(m - prev_min) < 8

            if too_close and idx % 2 == 1:
                # Label abaixo do marcador quando próximo do anterior
                y_off, va = -0.10, "top"
            else:
                y_off, va = 0.06, "bottom"

            ax.text(m, y_pt + y_off, lbl,
                    color=color, fontsize=5.8, fontfamily="Arial",
                    ha="center", va=va, linespacing=1.3, zorder=6,
                    path_effects=[pe.withStroke(linewidth=1.5, foreground=BG)])

    _plot_shot_markers(home_shots, home_shots, YELLOW, h_xg)
    _plot_shot_markers(away_shots, away_shots, BLUE,   a_xg)

    # ── xG totais no final das linhas ───────────────────────────────────────
    if h_xg:
        ax.text(x_max - 0.5, h_xg[-1] + 0.04,
                f"xG {h_xg[-1]:.2f}",
                color=YELLOW, fontsize=7.5, fontfamily="Franklin Gothic Heavy",
                fontweight="bold", ha="right", va="bottom", zorder=6,
                path_effects=[pe.withStroke(linewidth=1.5, foreground=BG)])
    if a_xg:
        ax.text(x_max - 0.5, a_xg[-1] - 0.06,
                f"xG {a_xg[-1]:.2f}",
                color=BLUE, fontsize=7.5, fontfamily="Franklin Gothic Heavy",
                fontweight="bold", ha="right", va="top", zorder=6,
                path_effects=[pe.withStroke(linewidth=1.5, foreground=BG)])

    # ── Eixos ───────────────────────────────────────────────────────────────
    ax.set_xlim(0, x_max)
    ax.set_ylim(-0.05, y_max_val * 1.15)
    ax.set_xlabel("MINUTO", color=LGRAY, fontsize=7, fontfamily="Arial", labelpad=4)
    ax.set_ylabel("xG ACUMULADO", color=LGRAY, fontsize=7, fontfamily="Arial", labelpad=6)
    ax.tick_params(colors=LGRAY, labelsize=6.5)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["bottom", "left"]].set_color(GRAY)

    # Xticks nos minutos de gol + 0, 45, 90
    goal_mins = sorted({s.get("minute", 0) for s in shots if s.get("type") == "goal"})
    base_ticks = [0, 45, 90]
    all_ticks  = sorted(set(base_ticks + goal_mins))
    ax.set_xticks(all_ticks)
    ax.set_xticklabels(
        ["0" if t == 0 else f"{t}'" for t in all_ticks],
        color=LGRAY, fontsize=6.5
    )

    # Grade suave
    for gv in [0.25, 0.5, 0.75, 1.0]:
        ax.axhline(gv, color=GRAY, linewidth=0.3, alpha=0.4, zorder=1)

    # Linha vertical no intervalo (45')
    ax.axvline(45, color=GRAY, linewidth=0.5, linestyle=":", alpha=0.5, zorder=1)

    # ── Legenda ─────────────────────────────────────────────────────────────
    home_name = match_data.get("home_team", "Mandante")
    away_name = match_data.get("away_team", "Visitante")
    legend_handles = [
        Line2D([0], [0], color=YELLOW, linewidth=2, label=home_name),
        Line2D([0], [0], color=BLUE,   linewidth=2, label=away_name),
        Line2D([0], [0], marker="*", color="w", markerfacecolor=YELLOW,
               markersize=9, label="GOL", linestyle="None"),
    ]
    ax.legend(handles=legend_handles, loc="upper left",
              fontsize=6.5, framealpha=0.2, facecolor=BG,
              labelcolor=LGRAY, edgecolor=GRAY, handlelength=1.2,
              borderpad=0.6, labelspacing=0.4, ncol=2)

    title = "xG ACUMULADO POR FINALIZAÇÃO"
    if status == "in_progress":
        title += "  ▶ AO VIVO"
    ax.set_title(title, color=LGRAY, fontsize=7.5,
                 fontfamily="Arial", pad=6, loc="left")

    _header(fig, match_data)
    _footer(fig, ax)

    img = _fig_to_pil(fig)
    plt.close(fig)
    return img


# ─── CARD 3 — Momentos de Ataque ─────────────────────────────────────────────

def generate_card_momentum(match_data: dict) -> "Image.Image":
    """CARD 3 — gráfico de área de momentos de ataque (attack momentum).

    Baseado no gráfico do SofaScore.
    A série temporal de ``momentum`` deve ter entradas ``{minute, value}``
    onde ``value`` é 0-100:
      - > 50 → mandante domina
      - < 50 → visitante domina
      - = 50 → equilíbrio

    O gráfico exibe:
      - Área positiva (mandante) em amarelo
      - Área negativa (visitante) em azul
      - Linha 0 como eixo central
      - Suavização via spline (se scipy disponível) ou interpolação linear
      - Marcadores verticais nos gols
    """
    raw_momentum = match_data.get("momentum", [])
    shots        = match_data.get("shots", [])
    status       = match_data.get("status", "completed")
    score        = match_data.get("score", [0, 0])

    fig = plt.figure(figsize=(7.0, 8.5), dpi=130)
    fig.patch.set_facecolor(BG)

    gs = fig.add_gridspec(1, 1, left=0.10, right=0.97,
                          top=0.900, bottom=0.085)
    ax = fig.add_subplot(gs[0])
    ax.set_facecolor(BG)

    if not raw_momentum:
        # Sem dados: exibe mensagem
        ax.text(0.5, 0.5, "DADOS DE MOMENTUM\nNÃO DISPONÍVEIS",
                color=LGRAY, fontsize=12, fontfamily="Arial",
                ha="center", va="center", transform=ax.transAxes)
        ax.axis("off")
    else:
        # Ordena e converte para array numpy
        raw_momentum = sorted(raw_momentum, key=lambda p: p.get("minute", 0))
        mins_raw  = np.array([p["minute"] for p in raw_momentum], dtype=float)
        vals_raw  = np.array([p["value"]  for p in raw_momentum], dtype=float)

        # Converte 0-100 → -1.0 a +1.0 (centro em 0)
        # Convenção SofaScore /graph: valor baixo = mandante dominante.
        # Invertemos o sinal para que home > 0 e away < 0.
        normalized = (50.0 - vals_raw) / 50.0

        # Suavização via rolling average antes da interpolação.
        # Janela pequena (5 pts ≈ 2.5 min) para preservar picos de ambos
        # os times sem amplificar o ruído ponto-a-ponto.
        window = 5
        kernel = np.ones(window) / window
        padded = np.pad(normalized, window // 2, mode="edge")
        normalized = np.convolve(padded, kernel, mode="valid")[:len(normalized)]

        # Interpolação suave sobre os valores já suavizados
        mins_smooth = np.linspace(mins_raw[0], mins_raw[-1], 500)
        if HAS_SCIPY and len(mins_raw) >= 4:
            k = min(3, len(mins_raw) - 1)
            spline = make_interp_spline(mins_raw, normalized, k=k)
            vals_smooth = np.clip(spline(mins_smooth), -1.0, 1.0)
        else:
            vals_smooth = np.interp(mins_smooth, mins_raw, normalized)

        # Área mandante (positiva) — amarelo
        ax.fill_between(mins_smooth, 0, vals_smooth,
                        where=vals_smooth >= 0,
                        color=YELLOW, alpha=0.50, zorder=2, interpolate=True)
        # Área visitante (negativa) — azul
        ax.fill_between(mins_smooth, 0, vals_smooth,
                        where=vals_smooth <= 0,
                        color=BLUE, alpha=0.45, zorder=2, interpolate=True)

        # Linha de contorno
        ax.plot(mins_smooth, vals_smooth, color=WHITE, linewidth=0.6,
                alpha=0.25, zorder=3)

        # Linha zero
        ax.axhline(0, color=GRAY, linewidth=1.0, zorder=4, alpha=0.7)

        # ── Marcadores de gol ──────────────────────────────────────────
        for shot in shots:
            if shot.get("type") != "goal":
                continue
            m     = shot.get("minute", 0)
            team  = shot.get("team", "home")
            color = YELLOW if team == "home" else BLUE
            # Linha vertical no gol
            ax.axvline(m, color=color, linewidth=1.2,
                       linestyle="--", alpha=0.80, zorder=5)
            player = shot.get("player", "")
            label  = f"⚽ {m}'"
            if player:
                label += f"\n{player}"
            # Posiciona label no topo ou fundo conforme time
            y_lbl = 0.92 if team == "home" else -0.92
            va_lbl = "top" if team == "away" else "bottom"
            ax.text(m, y_lbl, label,
                    color=color, fontsize=6, fontfamily="Arial",
                    ha="center", va=va_lbl, linespacing=1.3, zorder=6,
                    path_effects=[pe.withStroke(linewidth=1.5, foreground=BG)])

        # Linha vertical no intervalo
        ax.axvline(45, color=GRAY, linewidth=0.7, linestyle=":",
                   alpha=0.5, zorder=3)
        ax.text(45, 1.02, "HT", color=LGRAY, fontsize=6,
                fontfamily="Arial", ha="center", va="bottom")

        # Labels de dominância
        x_mid = (mins_raw[0] + mins_raw[-1]) / 2
        home_name = match_data.get("home_team", "MANDANTE")
        away_name = match_data.get("away_team", "VISITANTE")
        ax.text(0.01, 0.97, home_name.upper(),
                color=YELLOW, fontsize=7, fontfamily="Franklin Gothic Heavy",
                fontweight="bold", transform=ax.transAxes,
                ha="left", va="top", alpha=0.7)
        ax.text(0.01, 0.03, away_name.upper(),
                color=BLUE, fontsize=7, fontfamily="Franklin Gothic Heavy",
                fontweight="bold", transform=ax.transAxes,
                ha="left", va="bottom", alpha=0.7)

        # Eixos
        x_max = max(float(mins_raw[-1]) + 3, 93.0)
        ax.set_xlim(mins_raw[0], x_max)
        ax.set_ylim(-1.15, 1.15)
        ax.set_yticks([-1.0, -0.5, 0, 0.5, 1.0])
        ax.set_yticklabels([])   # Omite labels — escala não é intuitiva
        ax.set_xlabel("MINUTO", color=LGRAY, fontsize=7,
                      fontfamily="Arial", labelpad=4)
        ax.tick_params(colors=LGRAY, labelsize=6.5)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.spines["bottom"].set_color(GRAY)

        # Grade suave de tempo
        for xg in [15, 30, 45, 60, 75, 90]:
            ax.axvline(xg, color=GRAY, linewidth=0.3, alpha=0.3, zorder=1)

        title = "MOMENTOS DE ATAQUE"
        if status == "in_progress":
            title += "  ▶ AO VIVO"
        ax.set_title(title, color=LGRAY, fontsize=7.5,
                     fontfamily="Arial", pad=6, loc="left")

    _header(fig, match_data)
    _footer(fig, ax)

    img = _fig_to_pil(fig)
    plt.close(fig)
    return img


# ─── CARD 4 — Shotmap ────────────────────────────────────────────────────────

def generate_card_shotmap(match_data: dict) -> "Image.Image":
    """CARD 4 — mapa de finalizações dos dois times no campo.

    Layout: campo completo (StatsBomb 120×80).
      - Mandante ataca para a direita
      - Visitante ataca para a esquerda

    Marcadores:
      ● Finalização comum — círculo, tamanho proporcional ao xG
      ★ Gol             — estrela, tamanho proporcional ao xG

    Chutes sem xG recebem valor-base 0.04 para permanecerem visíveis.
    """
    if not HAS_MPLSOCCER:
        # Retorna card de aviso se mplsoccer não está instalado
        fig, ax = plt.subplots(figsize=(7.0, 8.5), dpi=130)
        fig.patch.set_facecolor(BG)
        ax.set_facecolor(BG)
        ax.text(0.5, 0.5, "mplsoccer não instalado\npip install mplsoccer",
                color=LGRAY, fontsize=12, ha="center", va="center",
                transform=ax.transAxes)
        ax.axis("off")
        _header(fig, match_data)
        _footer(fig, ax)
        img = _fig_to_pil(fig)
        plt.close(fig)
        return img

    shots = match_data.get("shots", [])
    # Separa por time
    home_shots = [s for s in shots if s.get("team") == "home"]
    away_shots = [s for s in shots if s.get("team") == "away"]

    # xG padrão para chutes sem valor (mantém visível mas pequeno)
    XG_DEFAULT = 0.04
    XG_SCALE   = 6    # raio do círculo em unidades StatsBomb = xg * XG_SCALE

    # Tamanho base do scatter para o marcador central (estrela no gol)
    # Escalonado pelo xG para reforçar a proporção visualmente
    SCATTER_SCALE = 900   # s = xg * SCATTER_SCALE (mínimo aplicado abaixo)

    fig = plt.figure(figsize=(7.0, 8.5), dpi=130)
    fig.patch.set_facecolor(BG)

    ax = fig.add_axes([0.03, 0.10, 0.94, 0.72])

    pitch = Pitch(
        pitch_type="statsbomb",
        pitch_color=PITCH_COLOR,
        line_color=LINE_COLOR,
        linewidth=1.0,
        goal_type="box",
        corner_arcs=True,
    )
    pitch.draw(ax=ax)

    def _plot_shots(shot_list: list, to_sb_fn, color: str) -> None:
        """Plota finalizações de um time.

        Todos os chutes: círculo proporcional ao xG.
        Gols: estrela sobreposta ao círculo (marcador especial).
        """
        for shot in shot_list:
            coord = shot.get("coord")
            if coord is None:
                continue
            xg   = shot.get("xg") or XG_DEFAULT
            kind = shot.get("type", "miss")
            sx, sy = to_sb_fn(*coord)
            r    = xg * XG_SCALE

            # Círculo de fundo — preenchido com baixa opacidade
            ax.add_patch(plt.Circle((sx, sy), r,
                                    color=color, alpha=0.18,
                                    zorder=3, linewidth=0))
            # Borda do círculo
            ax.add_patch(plt.Circle((sx, sy), r,
                                    color=color, alpha=0.55,
                                    fill=False, linewidth=1.0, zorder=4))

            if kind == "goal":
                # Estrela — marcador especial para gol
                ms = max(80, xg * SCATTER_SCALE)
                ax.scatter(sx, sy, s=ms, marker="*",
                           color=color, edgecolors=WHITE,
                           linewidths=0.6, zorder=6)

    _plot_shots(home_shots, _to_sb_home, YELLOW)
    _plot_shots(away_shots, _to_sb_away, BLUE)

    # ── Legenda ─────────────────────────────────────────────────────────────
    home_name = match_data.get("home_team", "MANDANTE")
    away_name = match_data.get("away_team", "VISITANTE")
    legend_items = [
        Line2D([0],[0], marker="o", color="w", markerfacecolor=YELLOW,
               markersize=8, label=home_name, linestyle="None"),
        Line2D([0],[0], marker="o", color="w", markerfacecolor=BLUE,
               markersize=8, label=away_name, linestyle="None"),
        Line2D([0],[0], marker="*", color="w", markerfacecolor=WHITE,
               markersize=10, label="GOL", linestyle="None"),
    ]
    ax.legend(
        handles=legend_items,
        loc="lower center", bbox_to_anchor=(0.5, 0.0),
        ncol=3, fontsize=6.5, framealpha=0.2,
        facecolor=BG, labelcolor=LGRAY, edgecolor=GRAY,
        handlelength=1.0, borderpad=0.6, columnspacing=1.2,
    )

    # Rótulo de cada time sobre o gol que ataca
    ax.text(112, 82, home_name.upper(),
            color=YELLOW, fontsize=7, fontfamily="Franklin Gothic Heavy",
            fontweight="bold", ha="center", va="bottom",
            path_effects=[pe.withStroke(linewidth=1.5, foreground=BG)])
    ax.text(8, 82, away_name.upper(),
            color=BLUE, fontsize=7, fontfamily="Franklin Gothic Heavy",
            fontweight="bold", ha="center", va="bottom",
            path_effects=[pe.withStroke(linewidth=1.5, foreground=BG)])

    # Nota de escala
    fig.text(0.50, 0.083,
             "tamanho do círculo proporcional ao xG · chutes sem xG = 0.04",
             color="#555555", fontsize=6.0, fontfamily="Arial",
             ha="center", va="center")

    _header(fig, match_data)
    _footer(fig, ax)

    img = _fig_to_pil(fig)
    plt.close(fig)
    return img


# ─── Função principal ─────────────────────────────────────────────────────────

def generate_match_cards(
    match_data: dict[str, Any],
    output_dir: str | Path | None = None,
) -> list["Image.Image"]:
    """Gera os 4 cards de análise de partida.

    Parâmetros
    ----------
    match_data:
        Dicionário no formato descrito no módulo docstring.
    output_dir:
        Se fornecido, salva os cards em disco com nomes padronizados:
          01_stats.png, 02_xg.png, 03_momentum.png, 04_shotmap.png

    Retorna
    -------
    Lista de 4 PIL.Image (mesmo que output_dir seja fornecido).
    Imagens ausentes de dependências (mplsoccer) retornam card de aviso.
    """
    if not HAS_PIL:
        raise ImportError("Pillow é necessário: pip install Pillow")

    # ── Sanitização básica dos dados de entrada ──────────────────────────
    md = dict(match_data)

    # Garante score como lista com 2 inteiros
    score = md.get("score", [0, 0])
    if not isinstance(score, (list, tuple)) or len(score) < 2:
        md["score"] = [0, 0]

    # Ordena shots por minuto e preenche xg=None com None (não com 0)
    shots = md.get("shots", [])
    shots = sorted(shots, key=lambda s: s.get("minute", 0))
    md["shots"] = shots

    # Ordena momentum por minuto
    momentum = md.get("momentum", [])
    md["momentum"] = sorted(momentum, key=lambda p: p.get("minute", 0))

    # ── Geração dos cards ────────────────────────────────────────────────
    cards: list[Image.Image] = []

    generators = [
        ("01_stats",    generate_card_stats),
        ("02_xg",       generate_card_xg_timeline),
        ("03_momentum", generate_card_momentum),
        ("04_shotmap",  generate_card_shotmap),
    ]

    for slug, fn in generators:
        img = fn(md)
        cards.append(img)

    # ── Salvar em disco (opcional) ───────────────────────────────────────
    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        names = ["01_stats.png", "02_xg.png", "03_momentum.png", "04_shotmap.png"]
        for img, name in zip(cards, names):
            dest = out / name
            img.save(dest)
            print(f"Salvo: {dest}")

    return cards


# ─── Demo / uso direto ────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Dados de exemplo — Londrina 1×2 Sport, R3 Série B 2026
    DEMO_DATA: dict[str, Any] = {
        "home_team":   "LONDRINA",
        "away_team":   "SPORT",
        "score":       [1, 2],
        "date":        "04.04.2026",
        "round":       "R3",
        "competition": "SÉRIE B 2026",
        "status":      "completed",
        "model_image": "Spt_Ars.jpeg",   # imagem modelo no Card 1

        # Escudos dos times (Card 1) — use paths locais ou data/cache/logos/
        "home_logo":   "data/cache/logos/2020.png",   # Londrina
        "away_logo":   "data/cache/logos/1959.png",   # Sport Recife

        "stats": {
            "possession":      [42.0, 58.0],
            "shots_total":     [8,    13],
            "shots_on_target": [3,    5],
            "xg":              [0.74, 1.44],
            "corners":         [3,    6],
            "fouls":           [14,   11],
            "passes_total":    [310,  430],
            "passes_accuracy": [74.0, 82.0],
            "tackles":         [22,   18],
            "yellow_cards":    [3,    1],
            "red_cards":       [0,    0],
            # Field Tilt explícito (opcional — senão é calculado dos shots)
            "field_tilt":      [35.0, 65.0],
        },

        "shots": [
            # Londrina (home)
            {"team": "home", "player": "CAPRINI",    "minute": 22, "type": "miss",  "xg": 0.08,  "coord": (18.0, 52.0)},
            {"team": "home", "player": "CAPRINI",    "minute": 55, "type": "goal",  "xg": 0.22,  "coord": (8.0,  58.0)},
            {"team": "home", "player": "MARCELINHO", "minute": 78, "type": "save",  "xg": 0.31,  "coord": (6.5,  42.0)},
            {"team": "home", "player": "MARCELINHO", "minute": 88, "type": "block", "xg": 0.13,  "coord": (11.0, 47.0)},
            # Sport (away) — nota: coords da perspectiva do visitante (x=0 = gol adversário)
            {"team": "away", "player": "PEROTTI",    "minute": 43, "type": "save",  "xg": 0.173, "coord": (5.4,  60.5)},
            {"team": "away", "player": "PEROTTI",    "minute": 65, "type": "block", "xg": 0.488, "coord": (5.0,  50.7)},
            {"team": "away", "player": "PEROTTI",    "minute": 70, "type": "miss",  "xg": 0.024, "coord": (23.6, 45.7)},
            {"team": "away", "player": "PEROTTI",    "minute": 87, "type": "goal",  "xg": 0.171, "coord": (5.2,  39.3)},
            {"team": "away", "player": "GUSTAVO M.", "minute": 32, "type": "goal",  "xg": 0.58,  "coord": (4.0,  55.0)},
        ],

        # Dados sintéticos de momentum (minuto a minuto)
        "momentum": [
            {"minute": m, "value": int(50 + 20 * np.sin(m / 8.0) + 5 * np.random.randn())}
            for m in range(1, 91)
        ],
    }

    cards = generate_match_cards(DEMO_DATA, output_dir="match_cards_demo")
    print(f"\n{len(cards)} cards gerados em match_cards_demo/")
