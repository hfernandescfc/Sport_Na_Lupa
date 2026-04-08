"""
Pré-processamento de texto dos tweets.

Etapas:
  1. Lowercase
  2. Remoção de URLs, mentions (@), hashtags (opcional), pontuação
  3. Remoção de stopwords em português
  4. Tokenização
  5. Criação de colunas `text_clean` e `tokens`
"""

import re
import string
from typing import List

import pandas as pd

# ---------------------------------------------------------------------------
# Stopwords em português (lista estendida -- não depende de NLTK)
# ---------------------------------------------------------------------------

STOPWORDS_PT = {
    "a", "ao", "aos", "aquela", "aquelas", "aquele", "aqueles", "aquilo",
    "as", "até", "com", "como", "da", "das", "de", "dela", "delas", "dele",
    "deles", "depois", "do", "dos", "e", "ela", "elas", "ele", "eles", "em",
    "entre", "era", "eram", "essa", "essas", "esse", "esses", "esta", "estas",
    "este", "estes", "eu", "foi", "foram", "há", "isso", "isto", "já", "lhe",
    "lhes", "mais", "mas", "me", "mesmo", "meu", "meus", "minha", "minhas",
    "muito", "na", "nas", "nem", "no", "nos", "nossa", "nossas", "nosso",
    "nossos", "num", "numa", "o", "os", "ou", "outra", "outras", "outro",
    "outros", "para", "pela", "pelas", "pelo", "pelos", "por", "qual",
    "quando", "que", "quem", "se", "sem", "seu", "seus", "só", "sua", "suas",
    "também", "te", "tem", "têm", "tendo", "teu", "teus", "tua", "tuas",
    "tudo", "um", "uma", "umas", "uns", "você", "vocês", "vos", "à", "às",
    "é", "ser", "são", "foi", "ser", "ter", "estar", "vai", "vou", "pra",
    "pro", "pras", "pros", "né", "ta", "tá", "aí", "lá", "aqui", "agora",
    "ainda", "assim", "bem", "cada", "com", "contra", "então", "essa",
    "nessa", "nesse", "nela", "nele", "pela", "pelo", "numa", "num",
}


# ---------------------------------------------------------------------------
# Funções de limpeza
# ---------------------------------------------------------------------------

def _remover_urls(texto: str) -> str:
    """Remove URLs (http, https, t.co, etc.)."""
    return re.sub(r"https?://\S+|www\.\S+|t\.co/\S+", " ", texto)


def _remover_mentions(texto: str) -> str:
    """Remove @mentions."""
    return re.sub(r"@\w+", " ", texto)


def _remover_hashtags(texto: str, manter_texto: bool = True) -> str:
    """
    Processa hashtags.
    Se manter_texto=True, mantém o texto da hashtag sem o #.
    Se False, remove completamente.
    """
    if manter_texto:
        return re.sub(r"#(\w+)", r"\1", texto)
    return re.sub(r"#\w+", " ", texto)


def _remover_pontuacao(texto: str) -> str:
    """Remove pontuação e caracteres especiais."""
    # Mantém espaços e letras (inclui acentuados)
    return re.sub(r"[^\w\s]", " ", texto)


def _remover_numeros(texto: str) -> str:
    """Remove sequências puramente numéricas."""
    return re.sub(r"\b\d+\b", " ", texto)


def _normalizar_espacos(texto: str) -> str:
    """Colapsa múltiplos espaços em um único."""
    return re.sub(r"\s+", " ", texto).strip()


def limpar_texto(
    texto: str,
    manter_hashtag_texto: bool = True,
    remover_numeros: bool = True,
) -> str:
    """
    Pipeline completo de limpeza de um único texto.

    Parâmetros
    ----------
    texto : str
        Texto bruto do tweet
    manter_hashtag_texto : bool
        Se True, "#SportRecife" vira "SportRecife"
    remover_numeros : bool
        Se True, remove números isolados

    Retorna
    -------
    str : texto limpo em lowercase
    """
    texto = str(texto).lower()
    texto = _remover_urls(texto)
    texto = _remover_mentions(texto)
    texto = _remover_hashtags(texto, manter_texto=manter_hashtag_texto)
    texto = _remover_pontuacao(texto)
    if remover_numeros:
        texto = _remover_numeros(texto)
    texto = _normalizar_espacos(texto)
    return texto


def tokenizar(texto_limpo: str, remover_stopwords: bool = True) -> List[str]:
    """
    Tokeniza texto já limpo.

    Parâmetros
    ----------
    texto_limpo : str
        Texto após limpar_texto()
    remover_stopwords : bool
        Se True, filtra stopwords em português

    Retorna
    -------
    List[str] : lista de tokens
    """
    tokens = texto_limpo.split()
    if remover_stopwords:
        tokens = [t for t in tokens if t not in STOPWORDS_PT and len(t) > 2]
    return tokens


# ---------------------------------------------------------------------------
# Processamento em batch (DataFrame)
# ---------------------------------------------------------------------------

def preprocessar(
    df: pd.DataFrame,
    coluna_texto: str = "text",
    manter_hashtag_texto: bool = True,
    remover_stopwords: bool = True,
) -> pd.DataFrame:
    """
    Aplica pré-processamento completo ao DataFrame de tweets.

    Adiciona colunas:
      - `text_clean` : texto limpo (lowercase, sem URLs, pontuação, etc.)
      - `tokens`     : lista de tokens sem stopwords
      - `n_tokens`   : número de tokens (proxy de comprimento do tweet)

    Parâmetros
    ----------
    df : pd.DataFrame
        DataFrame com coluna de texto bruto
    coluna_texto : str
        Nome da coluna com texto bruto
    manter_hashtag_texto : bool
        Se True, mantém texto das hashtags
    remover_stopwords : bool
        Se True, filtra stopwords

    Retorna
    -------
    pd.DataFrame com colunas novas adicionadas (não modifica original)
    """
    df = df.copy()

    df["text_clean"] = df[coluna_texto].apply(
        lambda t: limpar_texto(t, manter_hashtag_texto=manter_hashtag_texto)
    )
    df["tokens"] = df["text_clean"].apply(
        lambda t: tokenizar(t, remover_stopwords=remover_stopwords)
    )
    df["n_tokens"] = df["tokens"].apply(len)

    return df
