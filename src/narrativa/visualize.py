"""
Visualizações do pipeline de análise de narrativas.

Gráficos gerados:
  1. Série temporal de tweets (com picos marcados)
  2. Distribuição de engajamento (histograma + boxplot)
  3. Top usuários por engajamento (barras horizontais)
  4. (Opcional) Grafo de propagação via networkx
"""

import warnings
from pathlib import Path
from typing import Optional, List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns

# Paleta visual SportRecifeLab
CORES = {
    "fundo": "#0d0d0d",
    "texto": "#f0f0f0",
    "amarelo": "#F5C400",
    "verde": "#2a7a3a",
    "vermelho": "#c0392b",
    "cinza": "#4a4a4a",
    "azul": "#2980b9",
}

plt.rcParams.update({
    "figure.facecolor": CORES["fundo"],
    "axes.facecolor": CORES["fundo"],
    "axes.edgecolor": CORES["cinza"],
    "axes.labelcolor": CORES["texto"],
    "xtick.color": CORES["texto"],
    "ytick.color": CORES["texto"],
    "text.color": CORES["texto"],
    "grid.color": CORES["cinza"],
    "grid.alpha": 0.3,
    "font.family": "Arial",
})


# ---------------------------------------------------------------------------
# 1. Série temporal de tweets
# ---------------------------------------------------------------------------

def plot_serie_temporal(
    serie: pd.Series,
    picos: Optional[pd.DataFrame] = None,
    titulo: str = "Propagação da narrativa ao longo do tempo",
    tema: str = "Sport Recife",
    output_path: Optional[str] = None,
    ax: Optional[plt.Axes] = None,
) -> plt.Figure:
    """
    Plota a série temporal de tweets com picos marcados.

    Parâmetros
    ----------
    serie : pd.Series
        Série temporal (índice datetime, valores = contagem)
    picos : pd.DataFrame, opcional
        Saída de timeline.detectar_picos()
    titulo : str
    tema : str
        Tema da análise (ex: "Sport Recife")
    output_path : str, opcional
        Se fornecido, salva o gráfico neste caminho
    ax : plt.Axes, opcional
        Eixo existente para subplot

    Retorna
    -------
    plt.Figure
    """
    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(12, 5), facecolor=CORES["fundo"])
    else:
        fig = ax.get_figure()

    # Linha principal
    ax.fill_between(
        serie.index,
        serie.values,
        alpha=0.3,
        color=CORES["amarelo"],
    )
    ax.plot(
        serie.index,
        serie.values,
        color=CORES["amarelo"],
        linewidth=2,
        label="Tweets / período",
    )

    # Marcar picos
    if picos is not None:
        picos_df = picos[picos["eh_pico"]].copy()
        if not picos_df.empty:
            ax.scatter(
                picos_df["datetime"],
                picos_df["n_tweets"],
                color=CORES["vermelho"],
                zorder=5,
                s=80,
                label="Pico de atividade",
                marker="^",
            )

    # Formatação do eixo X
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m %Hh"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=8)

    ax.set_title(titulo, color=CORES["amarelo"], fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Data/Hora", fontsize=10)
    ax.set_ylabel("Quantidade de tweets", fontsize=10)
    ax.legend(facecolor=CORES["cinza"], edgecolor="none", fontsize=9)
    ax.grid(True, axis="y")

    # Rodapé
    ax.annotate(
        "@SportRecifeLab",
        xy=(1, -0.18), xycoords="axes fraction",
        ha="right", fontsize=8, color=CORES["cinza"],
        style="italic",
    )

    plt.tight_layout()

    if standalone and output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=CORES["fundo"])
        print(f"[Visualização] Série temporal salva em: {output_path}")

    return fig


# ---------------------------------------------------------------------------
# 2. Distribuição de engajamento
# ---------------------------------------------------------------------------

def plot_distribuicao_engajamento(
    df: pd.DataFrame,
    apenas_relevantes: bool = True,
    titulo: str = "Distribuição de engajamento por tweet",
    output_path: Optional[str] = None,
    ax: Optional[plt.Axes] = None,
) -> plt.Figure:
    """
    Plota histograma de engajamento (likes + retweets) por tweet.

    Inclui linha de mediana e percentil 90 para contextualizar.
    """
    df_work = df.copy()
    if apenas_relevantes and "relevante" in df_work.columns:
        df_work = df_work[df_work["relevante"]].copy()

    engajamento = (df_work["likes"] + df_work["retweets"]).clip(upper=500)

    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(10, 5), facecolor=CORES["fundo"])
    else:
        fig = ax.get_figure()

    # Histograma em escala log para lidar com cauda longa
    ax.hist(
        engajamento,
        bins=40,
        color=CORES["amarelo"],
        edgecolor=CORES["fundo"],
        alpha=0.8,
        log=True,
    )

    # Linhas de referência
    mediana = engajamento.median()
    p90 = np.percentile(engajamento, 90)

    ax.axvline(mediana, color=CORES["verde"], linewidth=1.5, linestyle="--", label=f"Mediana: {mediana:.0f}")
    ax.axvline(p90, color=CORES["vermelho"], linewidth=1.5, linestyle="--", label=f"P90: {p90:.0f}")

    ax.set_title(titulo, color=CORES["amarelo"], fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Engajamento por tweet (likes + RTs, cap 500)", fontsize=10)
    ax.set_ylabel("Frequência (escala log)", fontsize=10)
    ax.legend(facecolor=CORES["cinza"], edgecolor="none", fontsize=9)
    ax.grid(True, axis="y")

    plt.tight_layout()

    if standalone and output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=CORES["fundo"])
        print(f"[Visualização] Distribuição de engajamento salva em: {output_path}")

    return fig


# ---------------------------------------------------------------------------
# 3. Top usuários por engajamento
# ---------------------------------------------------------------------------

def plot_top_usuarios(
    metricas_usuarios: pd.DataFrame,
    n: int = 15,
    titulo: str = "Top usuários por engajamento nos primeiros tweets",
    output_path: Optional[str] = None,
    ax: Optional[plt.Axes] = None,
) -> plt.Figure:
    """
    Barras horizontais dos top N usuários por engajamento médio.
    """
    top = metricas_usuarios.head(n).copy()

    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(10, 0.45 * n + 2), facecolor=CORES["fundo"])
    else:
        fig = ax.get_figure()

    cores = [CORES["amarelo"] if i < 3 else CORES["verde"] for i in range(len(top))]

    bars = ax.barh(
        top["username"][::-1],
        top["engajamento_medio"][::-1],
        color=cores[::-1],
        edgecolor="none",
        height=0.65,
    )

    # Labels nos valores
    for bar in bars:
        width = bar.get_width()
        ax.text(
            width * 1.02, bar.get_y() + bar.get_height() / 2,
            f"{width:.0f}",
            va="center", ha="left", fontsize=8, color=CORES["texto"],
        )

    ax.set_title(titulo, color=CORES["amarelo"], fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Engajamento médio por tweet (likes + RTs)", fontsize=10)
    ax.grid(True, axis="x")
    ax.set_xlim(right=top["engajamento_medio"].max() * 1.2)

    plt.tight_layout()

    if standalone and output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=CORES["fundo"])
        print(f"[Visualização] Top usuários salvo em: {output_path}")

    return fig


# ---------------------------------------------------------------------------
# 4. (Opcional) Grafo de propagação
# ---------------------------------------------------------------------------

def plot_grafo_propagacao(
    df: pd.DataFrame,
    apenas_relevantes: bool = True,
    max_nos: int = 50,
    titulo: str = "Grafo de propagação (amostra)",
    output_path: Optional[str] = None,
) -> Optional[plt.Figure]:
    """
    Grafo simples de propagação usando networkx.

    Nós = usuários, arestas = tweets em sequência temporal próximos
    (proxy de influência/reação, sem dados reais de retweet-graph).

    Instale com: pip install networkx

    Parâmetros
    ----------
    max_nos : int
        Limita o número de nós para clareza visual
    """
    try:
        import networkx as nx
    except ImportError:
        warnings.warn("networkx não instalado. Pule esta visualização: pip install networkx")
        return None

    df_work = df.copy()
    if apenas_relevantes and "relevante" in df_work.columns:
        df_work = df_work[df_work["relevante"]].copy()

    df_work = df_work.sort_values("datetime").head(max_nos * 3).reset_index(drop=True)

    # Construir grafo: aresta entre tweet[i] e tweet[i+1] se mesmo usuário ou
    # se distância temporal < 30 minutos (proxy de reação/cascata)
    G = nx.DiGraph()

    for _, row in df_work.iterrows():
        G.add_node(row["username"], engajamento=row["likes"] + row["retweets"])

    for i in range(len(df_work) - 1):
        curr = df_work.iloc[i]
        prox = df_work.iloc[i + 1]
        delta_min = (prox["datetime"] - curr["datetime"]).total_seconds() / 60
        if delta_min <= 30:
            G.add_edge(curr["username"], prox["username"])

    # Limitar ao subgrafo dos nós com mais conexões
    if G.number_of_nodes() > max_nos:
        graus = dict(G.degree())
        top_nos = sorted(graus, key=graus.get, reverse=True)[:max_nos]
        G = G.subgraph(top_nos).copy()

    fig, ax = plt.subplots(figsize=(12, 8), facecolor=CORES["fundo"])

    # Layout
    try:
        pos = nx.kamada_kawai_layout(G)
    except Exception:
        pos = nx.spring_layout(G, seed=42)

    # Tamanho dos nós proporcional ao engajamento
    engajamentos = [G.nodes[n].get("engajamento", 1) + 1 for n in G.nodes()]
    max_eng = max(engajamentos)
    tamanhos = [200 + 600 * (e / max_eng) for e in engajamentos]

    nx.draw_networkx_nodes(G, pos, node_size=tamanhos, node_color=CORES["amarelo"], alpha=0.8, ax=ax)
    nx.draw_networkx_edges(G, pos, edge_color=CORES["cinza"], arrows=True, arrowsize=8, alpha=0.5, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=7, font_color=CORES["fundo"], ax=ax)

    ax.set_title(titulo, color=CORES["amarelo"], fontsize=13, fontweight="bold")
    ax.axis("off")

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=CORES["fundo"])
        print(f"[Visualização] Grafo de propagação salvo em: {output_path}")

    return fig


# ---------------------------------------------------------------------------
# Dashboard completo (todos os gráficos em um único arquivo)
# ---------------------------------------------------------------------------

def gerar_dashboard(
    df: pd.DataFrame,
    serie_temporal: pd.Series,
    picos: Optional[pd.DataFrame],
    metricas_usuarios: pd.DataFrame,
    classificacao: dict,
    tema: str = "narrativa",
    output_path: str = "dashboard_narrativa.png",
) -> plt.Figure:
    """
    Gera um dashboard com 3 gráficos em um único arquivo PNG.

    Layout:
      [  Série temporal (topo, largo)  ]
      [ Engajamento ]  [ Top usuários  ]
    """
    fig = plt.figure(figsize=(16, 12), facecolor=CORES["fundo"])
    gs = fig.add_gridspec(2, 2, hspace=0.4, wspace=0.3)

    ax_timeline = fig.add_subplot(gs[0, :])  # topo, ocupa toda a largura
    ax_eng = fig.add_subplot(gs[1, 0])       # inferior esquerdo
    ax_top = fig.add_subplot(gs[1, 1])       # inferior direito

    # Classificação no título geral
    cls = classificacao.get("classificacao", "?")
    score = classificacao.get("score_impulsao", 0)
    fig.suptitle(
        f'Análise de Narrativa -- "{tema}" | Classificação: {cls} (score: {score:.0f}/100)',
        color=CORES["amarelo"],
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )

    # Gráficos individuais (sem output_path -- embutidos no dashboard)
    plot_serie_temporal(serie_temporal, picos, titulo="Tweets ao longo do tempo", ax=ax_timeline)
    plot_distribuicao_engajamento(df, titulo="Distribuição de engajamento", ax=ax_eng)
    plot_top_usuarios(metricas_usuarios, n=12, titulo="Top usuários (primeiros tweets)", ax=ax_top)

    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=CORES["fundo"])
    print(f"[Dashboard] Salvo em: {output_path}")

    return fig
