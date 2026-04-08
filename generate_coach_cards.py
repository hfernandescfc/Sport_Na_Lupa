"""
Gera cards visuais dos técnicos especulados para o Sport Recife.
Estilo: dark + amarelo ouro, referência gustavo_maia_card_v4.png
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
import numpy as np

# ─── Paleta ─────────────────────────────────────────────────────────────────
BG       = "#111111"
CARD_BG  = "#1a1a1a"
YELLOW   = "#F5C400"
RED      = "#CC1020"
WHITE    = "#FFFFFF"
GRAY     = "#888888"
LGRAY    = "#AAAAAA"
DARKGRAY = "#2a2a2a"

# ─── Dados dos técnicos ──────────────────────────────────────────────────────
COACHES = [
    {
        "nome_linha1": "CLAUDIO",
        "nome_linha2": "TENCATI",
        "idade": 52,
        "nacionalidade": "Brasil / Italia",
        "formacao": "4-4-2 / 4-2-3-1",
        "total_jogos": 570,
        "ppj_carreira": 1.52,
        "win_pct": 47.0,   # baseado em dados reais: Londrina 57.6% (269J), Criciuma ~41% (174J)
        "titulos": ["Paranaense (1x)", "1a Liga (1x)", "Catarinense (2x)", "Recopa Cat. (1x)"],
        "destaques": [
            ("Londrina",      "2011-2017", "269J", 1.70),
            ("Criciuma",      "2021-2024", "174J", 1.49),
            ("Atletico-GO",   "2018",       "42J", 1.45),
            ("Brasil Pelotas","2020-2021",  "43J", 1.19),
            ("Botafogo-SP",   "2025-ativo",  "9J", 1.56),
        ],
        "obs": "Com Criciuma: acesso Serie B (2021) + acesso Serie A (2023)",
        "filename": "card_tencati.png",
    },
    {
        "nome_linha1": "EDUARDO",
        "nome_linha2": "BAPTISTA",
        "idade": 55,
        "nacionalidade": "Brasil",
        "formacao": "3-4-3",
        "total_jogos": 542,
        "ppj_carreira": 1.55,
        "win_pct": 49.0,   # Sport 53%, Novorizontino 56%, carreira ~48-50%
        "titulos": ["Copa do Nordeste 2014 (Sport)", "Pernambucano 2014 (Sport)", "Serie D 2021 (Mirassol)"],
        "destaques": [
            ("Sport Recife",       "2014-2015", "127J", 1.61),
            ("Novorizontino",      "2022-2025", "124J", 1.68),
            ("Criciuma",           "2025-ativo", "47J", 1.72),
            ("Palmeiras",          "2017",       "23J", 2.10),
            ("Sport Recife",       "2018",         "8J", 0.50),
        ],
        "obs": "Treinou o Sport em 2014-15 (Copa do NE) e 2018 — conhece o clube",
        "filename": "card_baptista.png",
    },
    {
        "nome_linha1": "LUIZINHO",
        "nome_linha2": "LOPES",
        "idade": 44,
        "nacionalidade": "Brasil",
        "formacao": "4-2-3-1",
        "total_jogos": 252,
        "ppj_carreira": 1.52,
        "win_pct": 41.5,   # estimado; atual 72.7% (8V/11J)
        "titulos": ["Sem titulos registrados"],
        "destaques": [
            ("Brusque",      "2022-2024", "72J", 1.54),
            ("Vila Nova",    "2024",      "26J", 1.54),
            ("Paysandu",     "2025",      "24J", 1.25),
            ("Confianca",    "2021-2022", "31J", 1.48),
            ("Operario-PR",  "2026-ativo","11J", 2.45),
        ],
        "obs": "Atual: Operario-PR  8V-3E-0D em 11J  (PPJ 2.45 — invicto em 2026)",
        "filename": "card_luizinho.png",
    },
]


def ppj_color(ppj):
    if ppj >= 1.80:
        return "#44DD88"
    elif ppj >= 1.50:
        return YELLOW
    elif ppj >= 1.20:
        return "#FF9900"
    else:
        return "#FF4444"


def draw_badge(ax, x, y, text, color=YELLOW, text_color="#111111", fontsize=7.5, width=None):
    t = ax.text(x, y, text,
                color=text_color, fontsize=fontsize,
                fontweight='bold', fontfamily='Franklin Gothic Heavy',
                ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.35', facecolor=color,
                          edgecolor='none', alpha=0.92),
                transform=ax.transAxes, zorder=5)
    return t


def generate_card(coach):
    fig_w, fig_h = 6.8, 9.6   # inches → ~680x960px @ 100dpi
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=120)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    # ── Fundo do card (com margem) ────────────────────────────────────────────
    card = FancyBboxPatch((0.03, 0.02), 0.94, 0.96,
                          boxstyle="round,pad=0.01",
                          facecolor=CARD_BG, edgecolor=YELLOW,
                          linewidth=1.5, zorder=1)
    ax.add_patch(card)

    # ── Faixa vermelha top ────────────────────────────────────────────────────
    faixa = FancyBboxPatch((0.03, 0.90), 0.94, 0.08,
                           boxstyle="round,pad=0.01",
                           facecolor=RED, edgecolor='none', zorder=2)
    ax.add_patch(faixa)

    ax.text(0.50, 0.942, "SPORT RECIFE  ·  TÉCNICO ESPECULADO",
            color=WHITE, fontsize=9.5, fontweight='bold',
            fontfamily='Franklin Gothic Heavy',
            ha='center', va='center', transform=ax.transAxes, zorder=3)

    # ── Nome do técnico ───────────────────────────────────────────────────────
    ax.text(0.50, 0.855,
            coach["nome_linha1"],
            color=WHITE, fontsize=38, fontweight='black',
            fontfamily='Franklin Gothic Heavy',
            ha='center', va='center', transform=ax.transAxes, zorder=3)

    ax.text(0.50, 0.805,
            coach["nome_linha2"],
            color=YELLOW, fontsize=38, fontweight='black',
            fontfamily='Franklin Gothic Heavy',
            ha='center', va='center', transform=ax.transAxes, zorder=3)

    # ── Subtítulo: idade · nacionalidade · formação ───────────────────────────
    sub = f"{coach['idade']} anos  ·  {coach['nacionalidade']}  ·  {coach['formacao']}"
    ax.text(0.50, 0.764, sub,
            color=LGRAY, fontsize=10, fontfamily='Arial',
            ha='center', va='center', transform=ax.transAxes, zorder=3)

    # ── Linha divisória ───────────────────────────────────────────────────────
    ax.plot([0.08, 0.92], [0.745, 0.745], color=YELLOW, linewidth=0.8,
            alpha=0.5, transform=ax.transAxes, zorder=3)

    # ── 3 métricas principais ─────────────────────────────────────────────────
    win_sub = "aprox. (est.)" if coach["win_pct"] < 45 else "dados reais"
    metrics = [
        ("PPJ CARREIRA",      f"{coach['ppj_carreira']:.2f}",
         f"{coach['total_jogos']} jogos"),
        ("% VITÓRIAS",        f"{coach['win_pct']:.1f}%",
         win_sub),
        ("FORMAÇÃO PREF.",    coach["formacao"],
         "tática preferida"),
    ]

    xs = [0.195, 0.50, 0.805]
    y_label = 0.710
    y_value = 0.672
    y_sub   = 0.643

    for (label, value, sub_text), x in zip(metrics, xs):
        ax.text(x, y_label, label, color=GRAY, fontsize=7.5,
                fontfamily='Arial', fontweight='bold',
                ha='center', va='center', transform=ax.transAxes, zorder=3)
        # formacao pode ser longa — reduz fonte
        fsize = 18 if len(value) > 7 else 22
        ax.text(x, y_value, value, color=WHITE, fontsize=fsize,
                fontfamily='Franklin Gothic Heavy', fontweight='black',
                ha='center', va='center', transform=ax.transAxes, zorder=3)
        ax.text(x, y_sub, sub_text, color=GRAY, fontsize=7.5,
                fontfamily='Arial',
                ha='center', va='center', transform=ax.transAxes, zorder=3)

    # ── Linha divisória 2 ─────────────────────────────────────────────────────
    ax.plot([0.08, 0.92], [0.620, 0.620], color=DARKGRAY, linewidth=0.8,
            transform=ax.transAxes, zorder=3)

    # ── Títulos ───────────────────────────────────────────────────────────────
    ax.text(0.08, 0.600, "TITULOS",
            color=GRAY, fontsize=7.5, fontfamily='Arial', fontweight='bold',
            ha='left', va='center', transform=ax.transAxes, zorder=3)

    titulos = coach["titulos"]
    # divide em até 2 linhas se muitos títulos
    if len(titulos) <= 2:
        ax.text(0.08, 0.579, "  /  ".join(titulos),
                color=WHITE, fontsize=9.0, fontfamily='Arial',
                ha='left', va='center', transform=ax.transAxes, zorder=3)
        div3_y = 0.558
    else:
        metade = (len(titulos) + 1) // 2
        linha1 = "  /  ".join(titulos[:metade])
        linha2 = "  /  ".join(titulos[metade:])
        ax.text(0.08, 0.587, linha1,
                color=WHITE, fontsize=8.5, fontfamily='Arial',
                ha='left', va='center', transform=ax.transAxes, zorder=3)
        ax.text(0.08, 0.571, linha2,
                color=YELLOW, fontsize=8.5, fontfamily='Arial',
                ha='left', va='center', transform=ax.transAxes, zorder=3)
        div3_y = 0.553

    # ── Linha divisória 3 ─────────────────────────────────────────────────────
    ax.plot([0.08, 0.92], [div3_y, div3_y], color=DARKGRAY, linewidth=0.8,
            transform=ax.transAxes, zorder=3)

    # ── Tabela: principais clubes ─────────────────────────────────────────────
    tab_label_y = div3_y - 0.020
    ax.text(0.08, tab_label_y, "PRINCIPAIS PASSAGENS",
            color=GRAY, fontsize=7.5, fontfamily='Arial', fontweight='bold',
            ha='left', va='center', transform=ax.transAxes, zorder=3)

    # Cabeçalho da tabela
    headers = ["CLUBE", "PERIODO", "JOGOS", "PPJ"]
    hx = [0.10, 0.44, 0.65, 0.82]
    hy = tab_label_y - 0.023
    for h, hxi in zip(headers, hx):
        ax.text(hxi, hy, h, color=YELLOW, fontsize=7,
                fontfamily='Arial', fontweight='bold',
                ha='left', va='center', transform=ax.transAxes, zorder=3)

    # Linhas da tabela
    row_h = 0.044
    for i, (clube, periodo, jogos, ppj) in enumerate(coach["destaques"]):
        ry = hy - (i + 1) * row_h

        # fundo alternado
        if i % 2 == 0:
            row_rect = FancyBboxPatch((0.08, ry - 0.016), 0.84, 0.032,
                                     boxstyle="round,pad=0.003",
                                     facecolor="#242424", edgecolor='none',
                                     zorder=2)
            ax.add_patch(row_rect)

        ax.text(hx[0], ry, clube,  color=WHITE,  fontsize=8.5,
                fontfamily='Arial', ha='left', va='center',
                transform=ax.transAxes, zorder=3)
        ax.text(hx[1], ry, periodo, color=LGRAY, fontsize=8,
                fontfamily='Arial', ha='left', va='center',
                transform=ax.transAxes, zorder=3)
        ax.text(hx[2], ry, jogos,   color=LGRAY, fontsize=8,
                fontfamily='Arial', ha='left', va='center',
                transform=ax.transAxes, zorder=3)

        # PPJ com cor
        ppj_c = ppj_color(ppj)
        ax.text(hx[3], ry, f"{ppj:.2f}", color=ppj_c, fontsize=8.5,
                fontfamily='Franklin Gothic Heavy', fontweight='bold',
                ha='left', va='center', transform=ax.transAxes, zorder=3)

    # ── Legenda PPJ ───────────────────────────────────────────────────────────
    legend_y = hy - 6 * row_h - 0.01
    ax.plot([0.08, 0.92], [legend_y, legend_y],
            color=DARKGRAY, linewidth=0.6, transform=ax.transAxes, zorder=3)

    legend_y -= 0.022
    ppj_legend = [
        ("≥1.80", "#44DD88"),
        ("1.50–1.79", YELLOW),
        ("1.20–1.49", "#FF9900"),
        ("<1.20", "#FF4444"),
    ]
    ax.text(0.08, legend_y, "PPJ:", color=GRAY, fontsize=6.5,
            fontfamily='Arial', ha='left', va='center',
            transform=ax.transAxes, zorder=3)
    lx = 0.155
    for lbl, clr in ppj_legend:
        ax.text(lx, legend_y, f"● {lbl}", color=clr, fontsize=6.2,
                fontfamily='Arial', ha='left', va='center',
                transform=ax.transAxes, zorder=3)
        lx += 0.175

    # ── Observação (destaque) ─────────────────────────────────────────────────
    obs_y = legend_y - 0.038
    ax.plot([0.08, 0.92], [obs_y + 0.022, obs_y + 0.022],
            color=DARKGRAY, linewidth=0.6, transform=ax.transAxes, zorder=3)

    obs_bg = FancyBboxPatch((0.08, obs_y - 0.014), 0.84, 0.030,
                            boxstyle="round,pad=0.005",
                            facecolor="#1e1e00", edgecolor=YELLOW,
                            linewidth=0.5, zorder=2)
    ax.add_patch(obs_bg)
    ax.text(0.50, obs_y, f">>  {coach['obs']}",
            color=YELLOW, fontsize=8, fontfamily='Arial',
            ha='center', va='center', transform=ax.transAxes, zorder=3)

    # ── Footer ────────────────────────────────────────────────────────────────
    ax.plot([0.08, 0.92], [0.065, 0.065], color=YELLOW, linewidth=0.6,
            alpha=0.4, transform=ax.transAxes, zorder=3)

    ax.text(0.08, 0.046, "@SportRecifeLab",
            color=YELLOW, fontsize=9, fontfamily='Franklin Gothic Heavy',
            fontweight='bold', ha='left', va='center',
            transform=ax.transAxes, zorder=3)

    ax.text(0.92, 0.046, "Dados: Transfermarkt",
            color=GRAY, fontsize=7.5, fontfamily='Arial',
            ha='right', va='center', transform=ax.transAxes, zorder=3)

    # ── Salvar ────────────────────────────────────────────────────────────────
    out_path = f"C:/Users/compesa/Desktop/SportSofa/{coach['filename']}"
    plt.tight_layout(pad=0)
    plt.savefig(out_path, dpi=120, bbox_inches='tight',
                facecolor=BG, edgecolor='none')
    plt.close()
    print(f"[OK] Salvo: {coach['filename']}")


if __name__ == "__main__":
    for coach in COACHES:
        generate_card(coach)
    print("\nTodos os cards gerados.")
