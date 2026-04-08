"""
Métricas de difusão da narrativa.

Mede como a ideia se espalhou ao longo do tempo:
  - Velocidade de crescimento
  - Concentração de usuários vs dispersão
  - Distribuição de engajamento (Gini / percentis)
  - Perfil de crescimento (linear, exponencial, viral burst)
"""

import pandas as pd
import numpy as np
from typing import Dict


# ---------------------------------------------------------------------------
# Métricas de concentração de usuários
# ---------------------------------------------------------------------------

def gini(values: np.ndarray) -> float:
    """
    Calcula o coeficiente de Gini de uma distribuição.

    Gini = 0 -> distribuição perfeitamente igual
    Gini = 1 -> concentração total em um único agente

    Usado para medir se o engajamento está concentrado em poucos usuários.
    """
    arr = np.array(values, dtype=float)
    if arr.sum() == 0:
        return 0.0
    arr = np.sort(arr)
    n = len(arr)
    index = np.arange(1, n + 1)
    return (2 * (index * arr).sum()) / (n * arr.sum()) - (n + 1) / n


def calcular_concentracao_usuarios(
    df: pd.DataFrame,
    apenas_relevantes: bool = True,
    top_n: int = 10,
) -> Dict:
    """
    Analisa a concentração de atividade por usuário ao longo de todo o dataset.

    Parâmetros
    ----------
    df : pd.DataFrame
    apenas_relevantes : bool
    top_n : int
        Quantos top usuários incluir no detalhe

    Retorna
    -------
    dict com métricas de concentração
    """
    df_work = df.copy()
    if apenas_relevantes and "relevante" in df_work.columns:
        df_work = df_work[df_work["relevante"]].copy()

    if df_work.empty:
        return {
            "n_usuarios_totais": 0, "n_tweets_relevantes": 0,
            f"share_top{top_n}_usuarios_pct": 0.0,
            "gini_tweets": 0.0, "gini_engajamento": 0.0, "top_usuarios": [],
        }

    por_usuario = df_work.groupby("username").agg(
        n_tweets=("text", "count"),
        total_likes=("likes", "sum"),
        total_rts=("retweets", "sum"),
    ).reset_index()

    por_usuario["engajamento_total"] = por_usuario["total_likes"] + por_usuario["total_rts"]
    por_usuario = por_usuario.sort_values("engajamento_total", ascending=False)

    n_usuarios = len(por_usuario)
    n_tweets_total = por_usuario["n_tweets"].sum()

    # Top N usuários respondem por X% dos tweets
    top_n_tweets = por_usuario.head(top_n)["n_tweets"].sum()
    share_top_n = (top_n_tweets / n_tweets_total * 100) if n_tweets_total > 0 else 0

    gini_tweets = gini(por_usuario["n_tweets"].values)
    gini_eng = gini(por_usuario["engajamento_total"].values)

    return {
        "n_usuarios_totais": n_usuarios,
        "n_tweets_relevantes": int(n_tweets_total),
        f"share_top{top_n}_usuarios_pct": round(share_top_n, 1),
        "gini_tweets": round(gini_tweets, 3),
        "gini_engajamento": round(gini_eng, 3),
        "top_usuarios": por_usuario.head(top_n).to_dict(orient="records"),
    }


# ---------------------------------------------------------------------------
# Distribuição de engajamento
# ---------------------------------------------------------------------------

def calcular_distribuicao_engajamento(
    df: pd.DataFrame,
    apenas_relevantes: bool = True,
) -> Dict:
    """
    Calcula percentis e estatísticas da distribuição de engajamento por tweet.

    Retorna
    -------
    dict com p25, p50, p75, p90, p95, p99, média, desvio, max, % com engaj > 0
    """
    df_work = df.copy()
    if apenas_relevantes and "relevante" in df_work.columns:
        df_work = df_work[df_work["relevante"]].copy()

    if df_work.empty:
        return {
            "p25": 0.0, "p50_mediana": 0.0, "p75": 0.0,
            "p90": 0.0, "p95": 0.0, "p99": 0.0,
            "media": 0.0, "desvio_padrao": 0.0, "max": 0,
            "pct_com_engajamento": 0.0, "gini": 0.0,
        }

    engajamento = df_work["likes"] + df_work["retweets"]

    return {
        "p25": float(np.percentile(engajamento, 25)),
        "p50_mediana": float(np.percentile(engajamento, 50)),
        "p75": float(np.percentile(engajamento, 75)),
        "p90": float(np.percentile(engajamento, 90)),
        "p95": float(np.percentile(engajamento, 95)),
        "p99": float(np.percentile(engajamento, 99)),
        "media": round(float(engajamento.mean()), 2),
        "desvio_padrao": round(float(engajamento.std()), 2),
        "max": int(engajamento.max()),
        "pct_com_engajamento": round(float((engajamento > 0).mean() * 100), 1),
        "gini": round(gini(engajamento.values), 3),
    }


# ---------------------------------------------------------------------------
# Velocidade de crescimento
# ---------------------------------------------------------------------------

def calcular_velocidade_crescimento(
    df: pd.DataFrame,
    coluna_tempo: str = "datetime",
    janelas: list = [10, 50, 100],
    apenas_relevantes: bool = True,
) -> Dict:
    """
    Calcula o tempo (horas) para atingir cada marco de tweets.

    Parâmetros
    ----------
    janelas : list
        Marcos de tweets (ex: [10, 50, 100])

    Retorna
    -------
    dict: marco -> horas_desde_inicio
    """
    df_work = df.copy()
    if apenas_relevantes and "relevante" in df_work.columns:
        df_work = df_work[df_work["relevante"]].copy()

    df_work = df_work.sort_values(coluna_tempo).reset_index(drop=True)

    if df_work.empty:
        return {}

    t_inicio = df_work[coluna_tempo].iloc[0]
    resultado = {}

    for marco in janelas:
        if len(df_work) >= marco:
            t_marco = df_work[coluna_tempo].iloc[marco - 1]
            horas = (t_marco - t_inicio).total_seconds() / 3600
            resultado[f"horas_para_{marco}_tweets"] = round(horas, 2)
        else:
            resultado[f"horas_para_{marco}_tweets"] = None

    return resultado


# ---------------------------------------------------------------------------
# Métricas completas de difusão
# ---------------------------------------------------------------------------

def calcular_metricas_difusao(
    df: pd.DataFrame,
    n_primeiros: int = 20,
    apenas_relevantes: bool = True,
) -> Dict:
    """
    Calcula todas as métricas de difusão em um único dicionário.

    Combina: concentração de usuários, distribuição de engajamento,
    velocidade de crescimento.

    Retorna
    -------
    dict com todas as métricas de difusão
    """
    metricas = {}

    metricas["concentracao"] = calcular_concentracao_usuarios(
        df, apenas_relevantes=apenas_relevantes
    )
    metricas["engajamento"] = calcular_distribuicao_engajamento(
        df, apenas_relevantes=apenas_relevantes
    )
    metricas["velocidade"] = calcular_velocidade_crescimento(
        df, apenas_relevantes=apenas_relevantes
    )

    return metricas
