"""
Análise de linha do tempo: distribuição de tweets ao longo do tempo.

Funções:
  - ordenar e indexar tweets por timestamp
  - agregar em janelas temporais (hora, dia, etc.)
  - detectar picos de atividade (burst detection)
"""

import pandas as pd
import numpy as np
from typing import Tuple


# ---------------------------------------------------------------------------
# Construção da série temporal
# ---------------------------------------------------------------------------

def construir_serie_temporal(
    df: pd.DataFrame,
    coluna_tempo: str = "datetime",
    freq: str = "1h",
    apenas_relevantes: bool = True,
) -> pd.Series:
    """
    Agrega tweets em intervalos de tempo regulares.

    Parâmetros
    ----------
    df : pd.DataFrame
        DataFrame com coluna de timestamp
    coluna_tempo : str
        Nome da coluna datetime
    freq : str
        Frequência pandas (ex: "1h", "30min", "1D")
    apenas_relevantes : bool
        Se True e coluna `relevante` existir, filtra apenas tweets relevantes

    Retorna
    -------
    pd.Series com índice datetime e valores = contagem de tweets por período
    """
    df_work = df.copy()

    # Filtrar apenas relevantes se coluna existir
    if apenas_relevantes and "relevante" in df_work.columns:
        df_work = df_work[df_work["relevante"]].copy()

    df_work[coluna_tempo] = pd.to_datetime(df_work[coluna_tempo], utc=True)
    df_work = df_work.set_index(coluna_tempo).sort_index()

    # Contagem por período
    serie = df_work.resample(freq).size()
    serie.name = "n_tweets"

    return serie


def construir_serie_engajamento(
    df: pd.DataFrame,
    coluna_tempo: str = "datetime",
    freq: str = "1h",
    apenas_relevantes: bool = True,
) -> pd.DataFrame:
    """
    Agrega engajamento total (likes + retweets) por período de tempo.

    Retorna
    -------
    pd.DataFrame com colunas: n_tweets, total_likes, total_retweets,
                               total_engajamento (likes + retweets)
    """
    df_work = df.copy()

    if apenas_relevantes and "relevante" in df_work.columns:
        df_work = df_work[df_work["relevante"]].copy()

    df_work[coluna_tempo] = pd.to_datetime(df_work[coluna_tempo], utc=True)
    df_work = df_work.set_index(coluna_tempo).sort_index()

    agg = df_work.resample(freq).agg(
        n_tweets=("text", "count"),
        total_likes=("likes", "sum"),
        total_retweets=("retweets", "sum"),
    )
    agg["total_engajamento"] = agg["total_likes"] + agg["total_retweets"]

    return agg


# ---------------------------------------------------------------------------
# Detecção de picos (burst detection)
# ---------------------------------------------------------------------------

def detectar_picos(
    serie: pd.Series,
    z_threshold: float = 2.0,
    janela_suavizacao: int = 3,
) -> pd.DataFrame:
    """
    Detecta picos de atividade incomuns na série temporal.

    Usa Z-score: pico = valor > média + z_threshold * desvio_padrão

    Parâmetros
    ----------
    serie : pd.Series
        Série temporal de contagem de tweets
    z_threshold : float
        Multiplicador do desvio padrão para considerar pico
    janela_suavizacao : int
        Janela para média móvel antes de calcular Z-score (reduz ruído)

    Retorna
    -------
    pd.DataFrame com colunas: datetime, n_tweets, z_score, eh_pico
    """
    suavizada = serie.rolling(window=janela_suavizacao, center=True, min_periods=1).mean()

    media = suavizada.mean()
    desvio = suavizada.std()

    if desvio == 0:
        z_scores = pd.Series(0.0, index=serie.index)
    else:
        z_scores = (suavizada - media) / desvio

    resultado = pd.DataFrame({
        "datetime": serie.index,
        "n_tweets": serie.values,
        "z_score": z_scores.values,
        "eh_pico": z_scores.values >= z_threshold,
    })

    n_picos = resultado["eh_pico"].sum()
    if n_picos > 0:
        print(f"[Picos] {n_picos} pico(s) de atividade detectado(s) (Z >= {z_threshold})")

    return resultado


# ---------------------------------------------------------------------------
# Métricas de velocidade de propagação
# ---------------------------------------------------------------------------

def calcular_tempo_para_n_tweets(
    df: pd.DataFrame,
    n_tweets: int = 100,
    coluna_tempo: str = "datetime",
    apenas_relevantes: bool = True,
) -> Tuple[float, pd.Timestamp]:
    """
    Calcula o tempo (em horas) desde o primeiro tweet até atingir n_tweets.

    Parâmetros
    ----------
    df : pd.DataFrame
    n_tweets : int
        Marco de quantidade de tweets
    coluna_tempo : str
    apenas_relevantes : bool

    Retorna
    -------
    Tuple[float, pd.Timestamp]:
        (horas_até_marco, timestamp_do_marco)
        Retorna (None, None) se não atingiu o marco.
    """
    df_work = df.copy()

    if apenas_relevantes and "relevante" in df_work.columns:
        df_work = df_work[df_work["relevante"]].copy()

    df_work = df_work.sort_values(coluna_tempo).reset_index(drop=True)

    if len(df_work) < n_tweets:
        print(f"[Timeline] Dataset tem apenas {len(df_work)} tweets (menos que o marco de {n_tweets})")
        return None, None

    t_inicio = df_work[coluna_tempo].iloc[0]
    t_marco = df_work[coluna_tempo].iloc[n_tweets - 1]

    delta_horas = (t_marco - t_inicio).total_seconds() / 3600

    print(f"[Timeline] Marco de {n_tweets} tweets atingido em {delta_horas:.1f}h após o início")

    return delta_horas, t_marco
