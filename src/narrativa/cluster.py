"""
(Extra) Clustering de variações da mesma ideia.

Agrupa tweets por similaridade semântica usando K-Means sobre embeddings.
Permite identificar sub-narrativas e variações temáticas.

Requer: sentence-transformers, scikit-learn
"""

import warnings
from typing import Optional, Tuple

import numpy as np
import pandas as pd


def clusterizar_tweets(
    df: pd.DataFrame,
    coluna_texto: str = "text_clean",
    n_clusters: int = 5,
    apenas_relevantes: bool = True,
    modelo: str = "paraphrase-multilingual-MiniLM-L12-v2",
) -> Tuple[pd.DataFrame, Optional[object]]:
    """
    Agrupa tweets em clusters por similaridade semântica (K-Means).

    Parâmetros
    ----------
    df : pd.DataFrame
        DataFrame pré-processado
    coluna_texto : str
        Coluna com texto limpo
    n_clusters : int
        Número de clusters (sub-narrativas)
    apenas_relevantes : bool
        Se True, clusteriza apenas tweets relevantes
    modelo : str
        Modelo sentence-transformers

    Retorna
    -------
    Tuple[pd.DataFrame, kmeans]:
        DataFrame com coluna `cluster` (int) e modelo KMeans fitado
    """
    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import normalize
    except ImportError as e:
        warnings.warn(
            f"Dependência faltando para clustering: {e}\n"
            "Instale: pip install sentence-transformers scikit-learn",
            stacklevel=2,
        )
        df["cluster"] = -1
        return df, None

    df_work = df.copy()
    if apenas_relevantes and "relevante" in df_work.columns:
        mask = df_work["relevante"]
        df_idx = df_work[mask].index
    else:
        df_idx = df_work.index

    textos = df_work.loc[df_idx, coluna_texto].tolist()

    if len(textos) < n_clusters:
        warnings.warn(
            f"Apenas {len(textos)} tweets disponíveis -- menos que n_clusters={n_clusters}. "
            f"Reduzindo para {max(1, len(textos))} clusters.",
            stacklevel=2,
        )
        n_clusters = max(1, len(textos))

    print(f"[Clustering] Carregando modelo '{modelo}'...")
    model = SentenceTransformer(modelo)
    embeddings = model.encode(textos, show_progress_bar=True)
    embeddings = normalize(embeddings)  # normaliza para similaridade cosseno

    print(f"[Clustering] Agrupando {len(textos)} tweets em {n_clusters} clusters...")
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    labels = kmeans.fit_predict(embeddings)

    df_work["cluster"] = -1
    df_work.loc[df_idx, "cluster"] = labels

    # Mostrar tema de cada cluster (tweets mais centrais)
    _exibir_resumo_clusters(df_work, df_idx, labels, n_clusters, coluna_texto)

    return df_work, kmeans


def _exibir_resumo_clusters(
    df: pd.DataFrame,
    df_idx,
    labels: np.ndarray,
    n_clusters: int,
    coluna_texto: str,
) -> None:
    """Exibe os 3 tweets mais representativos de cada cluster."""
    print("\n[Clustering] Resumo dos clusters:")
    textos_arr = df.loc[df_idx, coluna_texto].values

    for k in range(n_clusters):
        idx_cluster = np.where(labels == k)[0]
        n = len(idx_cluster)
        exemplos = [textos_arr[i][:80] for i in idx_cluster[:3]]
        print(f"\n  Cluster {k} ({n} tweets):")
        for ex in exemplos:
            print(f"    * {ex}...")


def resumo_clusters_por_tempo(
    df: pd.DataFrame,
    coluna_tempo: str = "datetime",
    apenas_relevantes: bool = True,
) -> Optional[pd.DataFrame]:
    """
    Agrega a distribuição de clusters ao longo do tempo.

    Útil para ver quais sub-narrativas dominaram em cada fase.

    Parâmetros
    ----------
    df : pd.DataFrame
        DataFrame com coluna `cluster` (saída de clusterizar_tweets)

    Retorna
    -------
    pd.DataFrame pivot: índice = período, colunas = clusters, valores = contagem
    """
    if "cluster" not in df.columns:
        warnings.warn("Coluna 'cluster' não encontrada. Execute clusterizar_tweets() primeiro.")
        return None

    df_work = df.copy()
    if apenas_relevantes and "relevante" in df_work.columns:
        df_work = df_work[df_work["relevante"]].copy()

    df_work[coluna_tempo] = pd.to_datetime(df_work[coluna_tempo], utc=True)
    df_work = df_work.set_index(coluna_tempo)

    pivot = df_work.groupby([pd.Grouper(freq="6h"), "cluster"]).size().unstack(fill_value=0)
    return pivot
