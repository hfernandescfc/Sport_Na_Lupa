"""
Pipeline principal de análise de propagação de narrativas.

Orquestra todas as etapas em ordem:
  1. Coleta de tweets
  2. Pré-processamento
  3. Identificação de tweets relevantes
  4. Série temporal + detecção de picos
  5. Análise de origem
  6. Métricas de difusão
  7. Classificação heurística
  8. (Opcional) Clustering de sub-narrativas
  9. Visualizações
  10. Geração de relatório e thread para o X
"""

import datetime
from pathlib import Path
from typing import Optional, List, Dict

import pandas as pd

from .collect import coletar_tweets
from .preprocess import preprocessar
from .identify import identificar_tweets_relevantes
from .timeline import construir_serie_temporal, detectar_picos, calcular_tempo_para_n_tweets
from .origin import extrair_primeiros_tweets, calcular_metricas_usuarios, resumo_origem
from .diffusion import calcular_metricas_difusao
from .classify import classificar_narrativa
from .report import gerar_resumo_tecnico, gerar_thread_x, salvar_pending_post
from . import visualize


# ---------------------------------------------------------------------------
# Configuração padrão do pipeline
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = {
    # Coleta
    "modo_coleta": "mock",          # "snscrape" | "ntscraper" | "mock"
    "max_tweets": 400,
    "desde": None,
    "ate": None,

    # Identificação
    "palavras_chave": [],           # definidas por run()
    "frase_base": None,             # definida por run()
    "usar_semantica": False,        # True requer sentence-transformers
    "threshold_semantico": 0.45,
    "modo_combinacao": "kw_only",   # "union" | "kw_only"

    # Análise
    "n_primeiros": 20,              # tweets analisados na janela de origem
    "freq_serie": "2h",             # frequência da série temporal

    # Visualizações
    "gerar_grafo": False,           # requer networkx
    "usar_clustering": False,       # requer sentence-transformers + sklearn
    "n_clusters": 5,

    # Output
    "pasta_saida": "pending_posts",
    "salvar_csv": True,
    "pasta_csv": "data/processed/narrativas",
}


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------

def run(
    tema: str,
    query: str,
    palavras_chave: List[str],
    frase_base: Optional[str] = None,
    config: Optional[Dict] = None,
    pasta_raiz: str = ".",
) -> Dict:
    """
    Executa o pipeline completo de análise de narrativa.

    Parâmetros
    ----------
    tema : str
        Nome legível da narrativa (ex: "time sem vontade")
    query : str
        Query de busca para snscrape (ex: "Sport Recife sem vontade")
    palavras_chave : List[str]
        Termos para filtro de relevância
    frase_base : str, opcional
        Frase-base para similaridade semântica (ex: "elenco apagado sem liderança")
    config : dict, opcional
        Sobrescreve configurações do DEFAULT_CONFIG
    pasta_raiz : str
        Pasta raiz do projeto (padrão: diretório atual)

    Retorna
    -------
    dict com:
        df          : DataFrame completo pré-processado + relevante
        classificacao : resultado da classificação
        thread       : lista de tweets para publicar
        pasta_post   : caminho do pending_post gerado
    """
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    cfg["palavras_chave"] = palavras_chave
    cfg["frase_base"] = frase_base

    pasta_raiz = Path(pasta_raiz)

    print(f"\n{'='*60}")
    print(f"  NARRATIVA: \"{tema}\"")
    print(f"  Query: {query}")
    print(f"  Palavras-chave: {palavras_chave}")
    print(f"{'='*60}\n")

    # -----------------------------------------------------------------------
    # Etapa 1: Coleta
    # -----------------------------------------------------------------------
    print("[1/8] Coletando tweets...")
    df = coletar_tweets(
        query=query,
        max_tweets=cfg["max_tweets"],
        desde=cfg.get("desde"),
        ate=cfg.get("ate"),
        modo=cfg["modo_coleta"],
    )
    print(f"      {len(df)} tweets coletados\n")

    # -----------------------------------------------------------------------
    # Etapa 2: Pré-processamento
    # -----------------------------------------------------------------------
    print("[2/8] Pré-processando texto...")
    df = preprocessar(df)
    print(f"      Concluído. Colunas: {list(df.columns)}\n")

    # -----------------------------------------------------------------------
    # Etapa 3: Identificação de tweets relevantes
    # -----------------------------------------------------------------------
    print("[3/8] Identificando tweets relevantes...")
    df = identificar_tweets_relevantes(
        df,
        palavras_chave=cfg["palavras_chave"],
        frase_base=cfg["frase_base"],
        usar_semantica=cfg["usar_semantica"],
        threshold_semantico=cfg["threshold_semantico"],
        modo_combinacao=cfg["modo_combinacao"],
    )
    print()

    # -----------------------------------------------------------------------
    # Etapa 4: Série temporal e picos
    # -----------------------------------------------------------------------
    print("[4/8] Construindo série temporal...")
    serie = construir_serie_temporal(df, freq=cfg["freq_serie"])
    picos_df = detectar_picos(serie)
    calcular_tempo_para_n_tweets(df, n_tweets=100)
    print()

    # -----------------------------------------------------------------------
    # Etapa 5: Análise de origem
    # -----------------------------------------------------------------------
    print(f"[5/8] Analisando os primeiros {cfg['n_primeiros']} tweets...")
    primeiros = extrair_primeiros_tweets(df, n=cfg["n_primeiros"])
    metricas_usr = calcular_metricas_usuarios(primeiros)
    resumo_orig = resumo_origem(primeiros, metricas_usr)
    print()

    # -----------------------------------------------------------------------
    # Etapa 6: Métricas de difusão
    # -----------------------------------------------------------------------
    print("[6/8] Calculando métricas de difusão...")
    metricas_dif = calcular_metricas_difusao(df, n_primeiros=cfg["n_primeiros"])
    print()

    # -----------------------------------------------------------------------
    # Etapa 7: Classificação
    # -----------------------------------------------------------------------
    print("[7/8] Classificando narrativa...")
    resultado_cls = classificar_narrativa(resumo_orig, metricas_dif, n_primeiros=cfg["n_primeiros"])
    print(
        f"      -> {resultado_cls['classificacao']} "
        f"(score {resultado_cls['score_impulsao']:.0f}/100, "
        f"confiança {resultado_cls['confianca']})"
    )
    print()

    # -----------------------------------------------------------------------
    # Etapa 7b: Clustering (opcional)
    # -----------------------------------------------------------------------
    if cfg["usar_clustering"]:
        print("[7b] Clustering de sub-narrativas...")
        from .cluster import clusterizar_tweets
        df, _ = clusterizar_tweets(df, n_clusters=cfg["n_clusters"])
        print()

    # -----------------------------------------------------------------------
    # Etapa 8: Visualizações
    # -----------------------------------------------------------------------
    print("[8/8] Gerando visualizações...")

    # Slug para nomes de arquivo
    slug = tema.lower().replace(" ", "-").replace('"', "")
    data_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    # Pasta de saída das imagens
    pasta_imgs = pasta_raiz / "pending_posts" / f"{data_str}_{slug}"
    pasta_imgs.mkdir(parents=True, exist_ok=True)

    n_relevantes = int(df["relevante"].sum()) if "relevante" in df.columns else len(df)
    if n_relevantes > 0:
        dashboard_path = str(pasta_imgs / "dashboard.png")
        visualize.gerar_dashboard(
            df=df,
            serie_temporal=serie,
            picos=picos_df,
            metricas_usuarios=metricas_usr,
            classificacao=resultado_cls,
            tema=tema,
            output_path=dashboard_path,
        )
        if cfg["gerar_grafo"]:
            grafo_path = str(pasta_imgs / "grafo_propagacao.png")
            visualize.plot_grafo_propagacao(df, output_path=grafo_path)
    else:
        print("      [!] Sem tweets relevantes -- dashboard não gerado.")

    print()

    # -----------------------------------------------------------------------
    # Relatório e thread
    # -----------------------------------------------------------------------
    resumo_txt = gerar_resumo_tecnico(
        tema, resultado_cls, resumo_orig, metricas_dif, picos=picos_df
    )
    thread = gerar_thread_x(tema, resultado_cls, resumo_orig, metricas_dif)

    pasta_post = salvar_pending_post(
        tema_slug=slug,
        thread=thread,
        resumo_tecnico=resumo_txt,
        classificacao=resultado_cls,
        pasta_raiz=str(pasta_raiz / "pending_posts"),
        data=data_str,
    )

    # Salvar CSV (opcional)
    if cfg["salvar_csv"]:
        csv_dir = pasta_raiz / cfg["pasta_csv"]
        csv_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(csv_dir / f"{data_str}_{slug}.csv", index=False, encoding="utf-8")
        print(f"[CSV] Salvo em: {csv_dir / f'{data_str}_{slug}.csv'}")

    # -----------------------------------------------------------------------
    # Exibir resumo final
    # -----------------------------------------------------------------------
    print("\n" + resumo_txt)
    print("\n-- THREAD PARA O X ----------------------------------------")
    for i, tweet in enumerate(thread, 1):
        print(f"\n[{i}/{len(thread)}]\n{tweet}")

    return {
        "df": df,
        "classificacao": resultado_cls,
        "resumo_origem": resumo_orig,
        "metricas_difusao": metricas_dif,
        "serie_temporal": serie,
        "picos": picos_df,
        "thread": thread,
        "pasta_post": pasta_post,
    }
