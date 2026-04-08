"""
Coleta de tweets via snscrape (ou ntscraper como alternativa).

ATENÇÃO: O snscrape original está QUEBRADO desde 2023 por mudanças na API do X.
Alternativas viáveis:
  - ntscraper: pip install ntscraper  (fork mais recente, pode ou não funcionar)
  - twint: depreciado
  - API oficial do X (paga, a partir de $100/mês)
  - Dados mock incluídos aqui para desenvolvimento e testes locais.

Quando snscrape/ntscraper falhar, o pipeline usa dados mock automaticamente.
"""

import datetime
import random
import warnings
from typing import Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Coleta via snscrape
# ---------------------------------------------------------------------------

def coletar_via_snscrape(
    query: str,
    max_tweets: int = 500,
    desde: Optional[str] = None,  # formato: "YYYY-MM-DD"
    ate: Optional[str] = None,
) -> pd.DataFrame:
    """
    Coleta tweets usando snscrape.

    Parâmetros
    ----------
    query : str
        Termos de busca (ex: "Sport Recife treinador")
    max_tweets : int
        Número máximo de tweets a coletar
    desde : str, opcional
        Data inicial no formato "YYYY-MM-DD"
    ate : str, opcional
        Data final no formato "YYYY-MM-DD"

    Retorna
    -------
    pd.DataFrame com colunas: tweet_id, text, datetime, username,
                               likes, replies, retweets, url
    """
    try:
        import snscrape.modules.twitter as sntwitter
    except ImportError:
        warnings.warn(
            "snscrape não instalado. Tente: pip install git+https://github.com/JustAnotherArchivist/snscrape"
            "\nUsando dados mock para desenvolvimento.",
            stacklevel=2,
        )
        return gerar_dados_mock(query, max_tweets)

    # Montar query com filtros de data
    if desde:
        query += f" since:{desde}"
    if ate:
        query += f" until:{ate}"

    registros = []
    try:
        scraper = sntwitter.TwitterSearchScraper(query)
        for i, tweet in enumerate(scraper.get_items()):
            if i >= max_tweets:
                break
            registros.append({
                "tweet_id": str(tweet.id),
                "text": tweet.rawContent,
                "datetime": tweet.date,
                "username": tweet.user.username,
                "likes": tweet.likeCount or 0,
                "replies": tweet.replyCount or 0,
                "retweets": tweet.retweetCount or 0,
                "url": tweet.url,
            })
    except Exception as e:
        warnings.warn(
            f"snscrape falhou ({e}). Usando dados mock para desenvolvimento.",
            stacklevel=2,
        )
        return gerar_dados_mock(query, max_tweets)

    if not registros:
        warnings.warn(
            "snscrape não retornou resultados. Usando dados mock.",
            stacklevel=2,
        )
        return gerar_dados_mock(query, max_tweets)

    df = pd.DataFrame(registros)
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df.sort_values("datetime", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


# ---------------------------------------------------------------------------
# Alternativa: ntscraper (fork mais recente, melhor chance de funcionar)
# ---------------------------------------------------------------------------

def coletar_via_ntscraper(
    query: str,
    max_tweets: int = 500,
) -> pd.DataFrame:
    """
    Coleta tweets usando ntscraper (alternativa ao snscrape).
    Instale com: pip install ntscraper
    """
    try:
        from ntscraper import Nitter
    except ImportError:
        warnings.warn(
            "ntscraper não instalado. Tente: pip install ntscraper\nUsando dados mock.",
            stacklevel=2,
        )
        return gerar_dados_mock(query, max_tweets)

    try:
        scraper = Nitter(log_level=1, skip_instance_check=False)
        tweets_raw = scraper.get_tweets(query, mode="term", number=max_tweets)
        registros = []
        for tweet in tweets_raw.get("tweets", []):
            registros.append({
                "tweet_id": tweet.get("link", "").split("/")[-1],
                "text": tweet.get("text", ""),
                "datetime": pd.to_datetime(tweet.get("date"), utc=True),
                "username": tweet.get("user", {}).get("username", ""),
                "likes": int(tweet.get("stats", {}).get("likes", 0)),
                "replies": int(tweet.get("stats", {}).get("comments", 0)),
                "retweets": int(tweet.get("stats", {}).get("retweets", 0)),
                "url": tweet.get("link", ""),
            })
        if not registros:
            raise ValueError("Sem resultados")
        df = pd.DataFrame(registros)
        df.sort_values("datetime", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df
    except Exception as e:
        warnings.warn(f"ntscraper falhou ({e}). Usando dados mock.", stacklevel=2)
        return gerar_dados_mock(query, max_tweets)


# ---------------------------------------------------------------------------
# Alternativa: twscrape (melhor opção atual — requer conta Twitter gratuita)
# ---------------------------------------------------------------------------

def coletar_via_twscrape(
    query: str,
    max_tweets: int = 500,
    db_path: str = "accounts.db",
) -> pd.DataFrame:
    """
    Coleta tweets usando twscrape.

    SETUP (uma única vez):
      pip install twscrape
      twscrape add_accounts contas.txt username:password:email:email_password
      twscrape login_accounts

    Parâmetros
    ----------
    query : str
        Query de busca (ex: "dal pozzo sport recife lang:pt")
    max_tweets : int
        Limite de tweets
    db_path : str
        Caminho do banco de contas twscrape (padrão: accounts.db no diretório atual)

    Retorna
    -------
    pd.DataFrame com a mesma estrutura dos outros coletores
    """
    try:
        import asyncio
        from twscrape import API, gather
    except ImportError:
        warnings.warn("twscrape não instalado. Execute: pip install twscrape", stacklevel=2)
        return gerar_dados_mock(query, max_tweets)

    async def _fetch():
        api = API(db_path)
        info = await api.pool.accounts_info()
        if not info:
            raise RuntimeError(
                "Nenhuma conta configurada no twscrape.\n"
                "Configure com:\n"
                "  echo 'usuario:senha:email:senha_email' > contas.txt\n"
                "  twscrape add_accounts contas.txt username:password:email:email_password\n"
                "  twscrape login_accounts"
            )

        registros = []
        async for tweet in api.search(query, limit=max_tweets):
            registros.append({
                "tweet_id": str(tweet.id),
                "text": tweet.rawContent,
                "datetime": tweet.date,
                "username": tweet.user.username,
                "likes": tweet.likeCount or 0,
                "replies": tweet.replyCount or 0,
                "retweets": tweet.retweetCount or 0,
                "url": tweet.url,
            })
        return registros

    try:
        registros = asyncio.run(_fetch())
    except RuntimeError as e:
        warnings.warn(str(e), stacklevel=2)
        return gerar_dados_mock(query, max_tweets)
    except Exception as e:
        warnings.warn(f"twscrape falhou ({e}). Usando dados mock.", stacklevel=2)
        return gerar_dados_mock(query, max_tweets)

    if not registros:
        warnings.warn("twscrape não retornou resultados. Usando dados mock.", stacklevel=2)
        return gerar_dados_mock(query, max_tweets)

    df = pd.DataFrame(registros)
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df.sort_values("datetime", inplace=True)
    df.reset_index(drop=True, inplace=True)
    print(f"[twscrape] {len(df)} tweets coletados para: '{query}'")
    return df


# ---------------------------------------------------------------------------
# Dados mock para desenvolvimento e testes locais
# ---------------------------------------------------------------------------

def gerar_dados_mock(query: str, n_tweets: int = 300) -> pd.DataFrame:
    """
    Gera dataset sintético realista para desenvolvimento local.

    Simula dois cenários misturados:
    - Início "orgânico": muitos usuários únicos com baixo engajamento
    - Pico "impulsionado": poucos usuários com alto engajamento

    Parâmetros
    ----------
    query : str
        Usada apenas para contextualizar mensagem de aviso
    n_tweets : int
        Número de tweets a simular

    Retorna
    -------
    pd.DataFrame com a mesma estrutura que coletar_via_snscrape()
    """
    warnings.warn(
        f"[MOCK] Usando dados sintéticos para query='{query}'. "
        "Para dados reais, configure snscraper/ntscraper.",
        stacklevel=2,
    )

    random.seed(42)

    # Cenário: narrativa começa orgânica, depois é amplificada por contas grandes
    inicio = datetime.datetime(2024, 4, 1, 18, 0, 0, tzinfo=datetime.timezone.utc)

    # Frases modelo de narrativas sobre Sport Recife
    frases_base = [
        "time sem vontade de ganhar",
        "o Sport não tem um projeto de jogo",
        "elenco apagado, falta liderança",
        "o treinador não sabe escalar",
        "Sport jogando muito mal essa temporada",
        "zero criatividade no meio-campo",
        "ataque estéril, sem finalizações",
        "precisamos de reforços urgente",
        "torcida na bronca com o desempenho",
        "Sport precisa acordar ou vai cair",
    ]

    # Perfis "comuns" -- muitos, baixo engajamento
    usuarios_comuns = [f"torcedor_{i}" for i in range(1, 150)]
    # Perfis "influentes" -- poucos, alto engajamento
    usuarios_influentes = ["jornalista_pe", "sport_news", "analista_futebol", "blog_sport", "podcast_leao"]

    registros = []
    for i in range(n_tweets):
        # Primeiros 15% são orgânicos (muitos usuários, baixo engajamento)
        if i < int(n_tweets * 0.15):
            username = random.choice(usuarios_comuns)
            likes = random.randint(0, 15)
            retweets = random.randint(0, 5)
            replies = random.randint(0, 8)
            delta = datetime.timedelta(minutes=random.randint(i * 2, i * 2 + 30))
        # Entre 15-40%: transição -- mistura
        elif i < int(n_tweets * 0.40):
            if random.random() < 0.3:
                username = random.choice(usuarios_influentes)
                likes = random.randint(50, 800)
                retweets = random.randint(10, 200)
                replies = random.randint(5, 80)
            else:
                username = random.choice(usuarios_comuns)
                likes = random.randint(5, 40)
                retweets = random.randint(0, 15)
                replies = random.randint(0, 20)
            delta = datetime.timedelta(hours=random.uniform(1, 6), minutes=random.randint(0, 60))
        # Acima de 40%: narrativa viralizada -- dominada por influentes e reações
        else:
            if random.random() < 0.15:
                username = random.choice(usuarios_influentes)
                likes = random.randint(200, 5000)
                retweets = random.randint(50, 1000)
                replies = random.randint(20, 500)
            else:
                username = random.choice(usuarios_comuns + [f"reage_{j}" for j in range(50)])
                likes = random.randint(0, 60)
                retweets = random.randint(0, 25)
                replies = random.randint(0, 30)
            delta = datetime.timedelta(hours=random.uniform(4, 72), minutes=random.randint(0, 120))

        ts = inicio + delta
        frase = random.choice(frases_base)
        variacao = random.choice(["", " demais", " nessa temporada", " no campeonato", " hoje"])
        texto = f"{frase}{variacao} #SportRecife"

        registros.append({
            "tweet_id": f"mock_{i:05d}",
            "text": texto,
            "datetime": ts,
            "username": username,
            "likes": likes,
            "replies": replies,
            "retweets": retweets,
            "url": f"https://x.com/{username}/status/mock_{i:05d}",
        })

    df = pd.DataFrame(registros)
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df.sort_values("datetime", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


# ---------------------------------------------------------------------------
# Função de entrada principal
# ---------------------------------------------------------------------------

def coletar_tweets(
    query: str,
    max_tweets: int = 500,
    desde: Optional[str] = None,
    ate: Optional[str] = None,
    modo: str = "snscrape",  # "snscrape" | "ntscraper" | "mock"
) -> pd.DataFrame:
    """
    Ponto de entrada para coleta de tweets.

    Parâmetros
    ----------
    query : str
        Termos de busca
    max_tweets : int
        Limite de tweets
    desde : str, opcional
        Data inicial "YYYY-MM-DD"
    ate : str, opcional
        Data final "YYYY-MM-DD"
    modo : str
        "snscrape" (padrão) | "ntscraper" | "mock"
    """
    if modo == "mock":
        return gerar_dados_mock(query, max_tweets)
    elif modo == "ntscraper":
        return coletar_via_ntscraper(query, max_tweets)
    elif modo == "twscrape":
        return coletar_via_twscrape(query, max_tweets)
    else:
        return coletar_via_snscrape(query, max_tweets, desde, ate)
