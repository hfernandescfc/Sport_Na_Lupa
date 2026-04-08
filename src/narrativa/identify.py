"""
Identificação de tweets que contêm a "ideia" analisada.

Duas abordagens:
  a) Filtro simples por palavras-chave (rápido, sem dependências extras)
  b) Similaridade semântica via sentence-transformers (mais preciso)

Ambas retornam um DataFrame com coluna `relevante` (bool) e `score` (float).
"""

import warnings
from typing import List, Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Abordagem A: Filtro por palavras-chave
# ---------------------------------------------------------------------------

def filtrar_por_palavras_chave(
    df: pd.DataFrame,
    palavras_chave: List[str],
    coluna_texto: str = "text_clean",
    requer_todas: bool = False,
) -> pd.DataFrame:
    """
    Marca tweets que contêm as palavras-chave fornecidas.

    Parâmetros
    ----------
    df : pd.DataFrame
        DataFrame pré-processado
    palavras_chave : List[str]
        Lista de termos (ex: ["vontade", "apagado", "sem jogo"])
    coluna_texto : str
        Coluna com texto limpo
    requer_todas : bool
        Se True, exige que TODAS as palavras estejam presentes (AND).
        Se False, basta uma (OR).

    Retorna
    -------
    pd.DataFrame com colunas `relevante_kw` (bool) e `score_kw` (float 0-1)
    """
    df = df.copy()

    def _checar(texto: str) -> tuple:
        hits = [kw.lower() in texto for kw in palavras_chave]
        n_hits = sum(hits)
        relevante = all(hits) if requer_todas else any(hits)
        score = n_hits / len(palavras_chave) if palavras_chave else 0.0
        return relevante, score

    resultados = df[coluna_texto].apply(_checar)
    df["relevante_kw"] = resultados.apply(lambda x: x[0])
    df["score_kw"] = resultados.apply(lambda x: x[1])

    return df


# ---------------------------------------------------------------------------
# Abordagem B: Similaridade semântica (sentence-transformers)
# ---------------------------------------------------------------------------

def filtrar_por_similaridade(
    df: pd.DataFrame,
    frase_base: str,
    coluna_texto: str = "text_clean",
    threshold: float = 0.45,
    modelo: str = "paraphrase-multilingual-MiniLM-L12-v2",
) -> pd.DataFrame:
    """
    Calcula similaridade semântica entre a frase-base e cada tweet.

    Usa sentence-transformers com um modelo multilíngue leve (~135MB).
    Instale com: pip install sentence-transformers

    Parâmetros
    ----------
    df : pd.DataFrame
        DataFrame pré-processado
    frase_base : str
        A ideia que queremos rastrear (ex: "time sem vontade de ganhar")
    coluna_texto : str
        Coluna com texto limpo
    threshold : float
        Mínimo de similaridade cosseno para classificar como relevante (0-1)
    modelo : str
        Modelo sentence-transformers a usar

    Retorna
    -------
    pd.DataFrame com colunas `relevante_sem` (bool) e `score_sem` (float 0-1)
    """
    df = df.copy()

    try:
        from sentence_transformers import SentenceTransformer, util
    except ImportError:
        warnings.warn(
            "sentence-transformers não instalado.\n"
            "Instale com: pip install sentence-transformers\n"
            "Usando score_sem=0 para todos os tweets.",
            stacklevel=2,
        )
        df["relevante_sem"] = False
        df["score_sem"] = 0.0
        return df

    print(f"[Semântica] Carregando modelo '{modelo}'...")
    model = SentenceTransformer(modelo)

    # Encoda a frase-base uma única vez
    emb_base = model.encode(frase_base, convert_to_tensor=True)

    # Encoda todos os tweets em batch (mais eficiente)
    textos = df[coluna_texto].tolist()
    print(f"[Semântica] Calculando embeddings para {len(textos)} tweets...")
    emb_tweets = model.encode(textos, convert_to_tensor=True, show_progress_bar=True)

    # Similaridade cosseno entre frase-base e cada tweet
    scores = util.cos_sim(emb_base, emb_tweets)[0].cpu().numpy()

    df["score_sem"] = scores.astype(float)
    df["relevante_sem"] = df["score_sem"] >= threshold

    return df


# ---------------------------------------------------------------------------
# Combinação das duas abordagens
# ---------------------------------------------------------------------------

def identificar_tweets_relevantes(
    df: pd.DataFrame,
    palavras_chave: List[str],
    frase_base: Optional[str] = None,
    coluna_texto: str = "text_clean",
    threshold_semantico: float = 0.45,
    usar_semantica: bool = True,
    modo_combinacao: str = "union",  # "union" | "intersection" | "kw_only" | "sem_only"
) -> pd.DataFrame:
    """
    Pipeline completo de identificação de tweets relevantes.

    Combina filtro por palavras-chave com similaridade semântica.

    Parâmetros
    ----------
    df : pd.DataFrame
        DataFrame pré-processado (com coluna text_clean)
    palavras_chave : List[str]
        Termos relacionados à ideia
    frase_base : str, opcional
        Frase representando a ideia para embeddings semânticos
    coluna_texto : str
        Coluna com texto limpo
    threshold_semantico : float
        Limiar de similaridade para abordagem semântica
    usar_semantica : bool
        Se False, usa apenas palavras-chave (mais rápido)
    modo_combinacao : str
        "union"        -> relevante se KW OU semântica
        "intersection" -> relevante se KW E semântica
        "kw_only"      -> apenas palavras-chave
        "sem_only"     -> apenas semântica

    Retorna
    -------
    pd.DataFrame com colunas: relevante_kw, score_kw,
                               relevante_sem, score_sem, relevante, score_final
    """
    # Filtro por palavras-chave
    df = filtrar_por_palavras_chave(df, palavras_chave, coluna_texto)

    # Filtro semântico (opcional)
    if usar_semantica and frase_base:
        df = filtrar_por_similaridade(df, frase_base, coluna_texto, threshold_semantico)
    else:
        df["relevante_sem"] = False
        df["score_sem"] = 0.0

    # Combinar resultados
    if modo_combinacao == "union":
        df["relevante"] = df["relevante_kw"] | df["relevante_sem"]
    elif modo_combinacao == "intersection":
        df["relevante"] = df["relevante_kw"] & df["relevante_sem"]
    elif modo_combinacao == "kw_only":
        df["relevante"] = df["relevante_kw"]
    elif modo_combinacao == "sem_only":
        df["relevante"] = df["relevante_sem"]
    else:
        df["relevante"] = df["relevante_kw"]

    # Score final: média dos dois scores (ou apenas um se semântica não usada)
    if usar_semantica and frase_base:
        df["score_final"] = (df["score_kw"] + df["score_sem"]) / 2
    else:
        df["score_final"] = df["score_kw"]

    n_relevantes = df["relevante"].sum()
    print(f"[Identificação] {n_relevantes}/{len(df)} tweets relevantes ({n_relevantes/len(df)*100:.1f}%)")

    return df
