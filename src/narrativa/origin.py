"""
Detecção de origem: análise dos primeiros N tweets da narrativa.

Objetivo: identificar quem iniciou a narrativa e qual o perfil dos primeiros
usuários -- contas orgânicas (pouco engajamento, muitos usuários únicos)
ou contas influentes (alto engajamento, poucos usuários dominando).
"""

import pandas as pd
import numpy as np
from typing import Optional


# ---------------------------------------------------------------------------
# Extração dos primeiros N tweets
# ---------------------------------------------------------------------------

def extrair_primeiros_tweets(
    df: pd.DataFrame,
    n: int = 20,
    coluna_tempo: str = "datetime",
    apenas_relevantes: bool = True,
) -> pd.DataFrame:
    """
    Extrai os primeiros N tweets ordenados por timestamp.

    Parâmetros
    ----------
    df : pd.DataFrame
    n : int
        Quantidade de primeiros tweets a analisar
    coluna_tempo : str
    apenas_relevantes : bool
        Se True e coluna `relevante` existir, filtra apenas tweets relevantes

    Retorna
    -------
    pd.DataFrame dos N primeiros tweets
    """
    df_work = df.copy()

    if apenas_relevantes and "relevante" in df_work.columns:
        df_work = df_work[df_work["relevante"]].copy()

    df_work = df_work.sort_values(coluna_tempo).reset_index(drop=True)
    primeiros = df_work.head(n)

    print(f"[Origem] Analisando os primeiros {len(primeiros)} tweets")
    return primeiros


# ---------------------------------------------------------------------------
# Métricas dos usuários dos primeiros tweets
# ---------------------------------------------------------------------------

def calcular_metricas_usuarios(df_primeiros: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula métricas por usuário nos primeiros tweets.

    Métricas calculadas:
      - n_tweets      : frequência de postagem (quantas vezes aparece)
      - total_likes   : soma de likes recebidos
      - total_rts     : soma de retweets
      - media_likes   : média de likes (proxy de influência)
      - media_rts     : média de retweets
      - engajamento_medio : (total_likes + total_rts) / n_tweets
      - share_tweets  : % dos primeiros tweets que são deste usuário

    Parâmetros
    ----------
    df_primeiros : pd.DataFrame
        Resultado de extrair_primeiros_tweets()

    Retorna
    -------
    pd.DataFrame indexado por username, ordenado por engajamento_medio DESC
    """
    n_total = len(df_primeiros)

    agg = df_primeiros.groupby("username").agg(
        n_tweets=("text", "count"),
        total_likes=("likes", "sum"),
        total_rts=("retweets", "sum"),
        media_likes=("likes", "mean"),
        media_rts=("retweets", "mean"),
    ).reset_index()

    agg["engajamento_medio"] = (agg["total_likes"] + agg["total_rts"]) / agg["n_tweets"]
    agg["share_tweets"] = (agg["n_tweets"] / n_total * 100).round(1)

    agg = agg.sort_values("engajamento_medio", ascending=False).reset_index(drop=True)

    return agg


# ---------------------------------------------------------------------------
# Métricas agregadas do grupo inicial
# ---------------------------------------------------------------------------

def resumo_origem(
    df_primeiros: pd.DataFrame,
    metricas_usuarios: Optional[pd.DataFrame] = None,
) -> dict:
    """
    Retorna um dicionário com métricas agregadas dos primeiros tweets.

    Métricas:
      - n_tweets_analisados : total de tweets na janela inicial
      - n_usuarios_unicos   : usuários distintos
      - concentracao        : % de tweets dos top-3 usuários (concentração)
      - engajamento_medio   : média de (likes + rts) por tweet
      - mediana_engajamento : mediana de engajamento (menos sensível a outliers)
      - max_engajamento     : tweet mais viralizado do grupo inicial
      - t_inicio            : timestamp do primeiro tweet
      - t_fim               : timestamp do último dos N primeiros

    Parâmetros
    ----------
    df_primeiros : pd.DataFrame
    metricas_usuarios : pd.DataFrame, opcional
        Se não fornecido, calcula internamente

    Retorna
    -------
    dict com métricas de origem
    """
    if metricas_usuarios is None:
        metricas_usuarios = calcular_metricas_usuarios(df_primeiros)

    n = len(df_primeiros)
    n_usuarios = df_primeiros["username"].nunique() if n > 0 else 0

    # Guard: DataFrame vazio (sem tweets relevantes)
    if n == 0:
        print("[Origem] Nenhum tweet relevante encontrado — verifique palavras-chave ou coleta.")
        return {
            "n_tweets_analisados": 0,
            "n_usuarios_unicos": 0,
            "concentracao_top3_pct": 0.0,
            "engajamento_medio": 0.0,
            "mediana_engajamento": 0.0,
            "max_engajamento": 0,
            "t_inicio": None,
            "t_fim": None,
            "janela_horas": 0.0,
        }

    # Concentração: % do grupo inicial dos top-3 usuários
    top3_tweets = metricas_usuarios.head(3)["n_tweets"].sum()
    concentracao = (top3_tweets / n * 100) if n > 0 else 0

    # Engajamento por tweet
    df_primeiros = df_primeiros.copy()
    df_primeiros["engajamento"] = df_primeiros["likes"] + df_primeiros["retweets"]

    resumo = {
        "n_tweets_analisados": n,
        "n_usuarios_unicos": n_usuarios,
        "concentracao_top3_pct": round(concentracao, 1),
        "engajamento_medio": round(float(df_primeiros["engajamento"].mean()), 1),
        "mediana_engajamento": round(float(df_primeiros["engajamento"].median()), 1),
        "max_engajamento": int(df_primeiros["engajamento"].max()),
        "t_inicio": df_primeiros["datetime"].min(),
        "t_fim": df_primeiros["datetime"].max(),
    }

    janela_horas = (resumo["t_fim"] - resumo["t_inicio"]).total_seconds() / 3600
    resumo["janela_horas"] = round(janela_horas, 2)

    print(f"[Origem] {n_usuarios} usuários únicos nos primeiros {n} tweets")
    print(f"[Origem] Concentração top-3: {concentracao:.1f}% | Engajamento médio: {resumo['engajamento_medio']}")

    return resumo
