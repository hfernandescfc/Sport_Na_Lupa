"""
Geração de relatório textual automático.

Formatos:
  - Resumo técnico (para análise interna)
  - Thread para o X -- pronto para publicar via @SportRecifeLab
  - Metadata JSON (para pasta pending_posts/)
"""

import datetime
import json
from pathlib import Path
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# Resumo técnico
# ---------------------------------------------------------------------------

def gerar_resumo_tecnico(
    tema: str,
    classificacao: Dict,
    resumo_origem: Dict,
    metricas_difusao: Dict,
    picos: Optional[object] = None,
) -> str:
    """
    Gera um relatório técnico completo em texto.

    Parâmetros
    ----------
    tema : str
        A narrativa analisada (ex: "time sem vontade")
    classificacao : dict
        Saída de classify.classificar_narrativa()
    resumo_origem : dict
        Saída de origin.resumo_origem()
    metricas_difusao : dict
        Saída de diffusion.calcular_metricas_difusao()
    picos : pd.DataFrame, opcional
        Saída de timeline.detectar_picos()

    Retorna
    -------
    str : relatório formatado
    """
    cls = classificacao["classificacao"]
    score = classificacao["score_impulsao"]
    confianca = classificacao["confianca"]
    descricao_cls = classificacao["descricao"]

    n_usuarios = resumo_origem["n_usuarios_unicos"]
    n_tweets = resumo_origem["n_tweets_analisados"]
    concentracao = resumo_origem["concentracao_top3_pct"]
    eng_medio = resumo_origem["engajamento_medio"]
    janela_h = resumo_origem.get("janela_horas", 0)

    eng_mediana = metricas_difusao["engajamento"]["p50_mediana"]
    eng_p90 = metricas_difusao["engajamento"]["p90"]
    gini_eng = metricas_difusao["engajamento"]["gini"]

    conc = metricas_difusao["concentracao"]
    n_usuarios_total = conc["n_usuarios_totais"]
    gini_tweets = conc["gini_tweets"]

    vel = metricas_difusao["velocidade"]

    # Picos
    n_picos = 0
    if picos is not None:
        try:
            n_picos = int(picos["eh_pico"].sum())
        except Exception:
            pass

    linhas = [
        "=" * 60,
        f"RELATÓRIO DE ANÁLISE DE NARRATIVA",
        f"Tema: \"{tema}\"",
        f"Gerado em: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "=" * 60,
        "",
        "-- CLASSIFICAÇÃO ------------------------------------------",
        f"  Classificação : {cls}",
        f"  Score         : {score:.0f}/100 (0=orgânico, 100=impulsionado)",
        f"  Confiança     : {confianca}",
        "",
        f"  {descricao_cls}",
        "",
        "-- ORIGEM (primeiros tweets) -------------------------------",
        f"  Tweets analisados : {n_tweets}",
        f"  Usuários únicos   : {n_usuarios}",
        f"  Concentração top3 : {concentracao:.1f}%",
        f"  Engajamento médio : {eng_medio:.1f} (likes + RTs)",
        f"  Janela temporal   : {janela_h:.1f}h",
        "",
        "-- DIFUSÃO (dataset completo) ------------------------------",
        f"  Total usuários    : {n_usuarios_total}",
        f"  Gini tweets       : {gini_tweets:.3f} (0=igualitário, 1=concentrado)",
        f"  Gini engajamento  : {gini_eng:.3f}",
        f"  Mediana eng/tweet : {eng_mediana:.0f}",
        f"  P90 eng/tweet     : {eng_p90:.0f}",
    ]

    # Velocidade
    linhas.append("")
    linhas.append("-- VELOCIDADE ----------------------------------------------")
    for chave, valor in vel.items():
        marco = chave.replace("horas_para_", "").replace("_tweets", " tweets")
        if valor is not None:
            linhas.append(f"  {marco:20s}: {valor:.1f}h")
        else:
            linhas.append(f"  {marco:20s}: (não atingido)")

    # Picos
    linhas.append("")
    linhas.append("-- PICOS DE ATIVIDADE --------------------------------------")
    linhas.append(f"  Picos detectados  : {n_picos}")

    # Fatores
    linhas.append("")
    linhas.append("-- FATORES DE CLASSIFICAÇÃO --------------------------------")
    for nome, fator in classificacao["fatores"].items():
        sinal = "↑ IMPULSIONADO" if fator["sinal_impulsionamento"] else "↓ ORGÂNICO"
        linhas.append(f"  [{sinal}] {fator['descricao']}")

    linhas.append("")
    linhas.append("=" * 60)

    return "\n".join(linhas)


# ---------------------------------------------------------------------------
# Thread para o X
# ---------------------------------------------------------------------------

def gerar_thread_x(
    tema: str,
    classificacao: Dict,
    resumo_origem: Dict,
    metricas_difusao: Dict,
    handle: str = "@SportRecifeLab",
) -> list[str]:
    """
    Gera uma thread de tweets prontos para publicar no X.

    Retorna
    -------
    list[str] : lista de tweets (cada item = 1 tweet da thread, <= 280 chars)
    """
    cls = classificacao["classificacao"]
    score = classificacao["score_impulsao"]
    n_usuarios = resumo_origem["n_usuarios_unicos"]
    n_tweets = resumo_origem["n_tweets_analisados"]
    concentracao = resumo_origem["concentracao_top3_pct"]
    eng_medio = resumo_origem["engajamento_medio"]
    conc = metricas_difusao["concentracao"]
    n_total = conc["n_usuarios_totais"]
    eng_p90 = metricas_difusao["engajamento"]["p90"]

    emoji_cls = "🌱" if cls == "Orgânico" else ("📢" if cls == "Impulsionado" else "🔀")

    thread = []

    # Tweet 1 -- gancho
    thread.append(
        f"{emoji_cls} Analisei a narrativa \"{tema}\" no X.\n\n"
        f"Ela é ORGÂNICA ou foi IMPULSIONADA por contas grandes?\n\n"
        f"🧵 Thread com os dados:"
    )

    # Tweet 2 -- classificação
    if cls == "Impulsionado":
        thread.append(
            f"📊 RESULTADO: a narrativa foi IMPULSIONADA.\n\n"
            f"Score de impulsionamento: {score:.0f}/100\n\n"
            f"Os primeiros {n_tweets} tweets foram dominados por apenas {n_usuarios} perfis -- "
            f"com top-3 respondendo por {concentracao:.0f}% do início."
        )
    elif cls == "Orgânico":
        thread.append(
            f"📊 RESULTADO: narrativa ORGÂNICA.\n\n"
            f"Score de impulsionamento: {score:.0f}/100\n\n"
            f"Os primeiros {n_tweets} tweets vieram de {n_usuarios} usuários distintos -- "
            f"sinal de que a ideia emergiu espontaneamente da torcida."
        )
    else:
        thread.append(
            f"📊 RESULTADO: narrativa MISTA.\n\n"
            f"Score: {score:.0f}/100\n\n"
            f"Começou com {n_usuarios} usuários distintos, mas os dados de engajamento "
            f"mostram possível amplificação por contas maiores depois."
        )

    # Tweet 3 -- engajamento
    thread.append(
        f"💡 Sobre o engajamento:\n\n"
        f"-> Média nos primeiros tweets: {eng_medio:.0f} likes+RTs\n"
        f"-> P90 do dataset completo: {eng_p90:.0f} likes+RTs\n"
        f"-> Total de usuários únicos identificados: {n_total}\n\n"
        f"Um alto engajamento no início = possível presença de influenciadores."
    )

    # Tweet 4 -- contexto e call to action
    thread.append(
        f"🔍 Saber se uma narrativa é orgânica ou fabricada importa.\n\n"
        f"Narrativas impulsionadas por poucos perfis grandes podem distorcer "
        f"a percepção da maioria sobre o clube, jogadores e comissão técnica.\n\n"
        f"Dado > achismo. {handle}"
    )

    return thread


# ---------------------------------------------------------------------------
# Salvar em pending_posts/
# ---------------------------------------------------------------------------

def salvar_pending_post(
    tema_slug: str,
    thread: list[str],
    resumo_tecnico: str,
    classificacao: Dict,
    pasta_raiz: str = "pending_posts",
    data: Optional[str] = None,
) -> Path:
    """
    Salva thread e metadata na estrutura pending_posts/.

    Estrutura criada:
      pending_posts/<YYYY-MM-DD_slug>/
        tweet.txt     -- thread completa (tweets separados por "---")
        resumo.txt    -- relatório técnico completo
        metadata.json -- metadata para controle de publicação

    Parâmetros
    ----------
    tema_slug : str
        Identificador da análise (ex: "time-sem-vontade")
    thread : list[str]
        Thread gerada por gerar_thread_x()
    resumo_tecnico : str
        Saída de gerar_resumo_tecnico()
    classificacao : dict
        Saída de classify.classificar_narrativa()
    pasta_raiz : str
        Pasta raiz (padrão: "pending_posts")
    data : str, opcional
        Data no formato "YYYY-MM-DD" (padrão: hoje)

    Retorna
    -------
    Path : caminho da pasta criada
    """
    if data is None:
        data = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    slug = f"{data}_{tema_slug}"
    pasta = Path(pasta_raiz) / slug
    pasta.mkdir(parents=True, exist_ok=True)

    # tweet.txt
    tweet_path = pasta / "tweet.txt"
    tweet_path.write_text(
        "\n\n---\n\n".join(thread),
        encoding="utf-8",
    )

    # resumo.txt
    resumo_path = pasta / "resumo.txt"
    resumo_path.write_text(resumo_tecnico, encoding="utf-8")

    # metadata.json
    metadata = {
        "slug": slug,
        "data_criacao": datetime.datetime.utcnow().isoformat() + "Z",
        "status": "pending",
        "classificacao": classificacao["classificacao"],
        "score_impulsao": classificacao["score_impulsao"],
        "confianca": classificacao["confianca"],
        "n_tweets_thread": len(thread),
    }
    metadata_path = pasta / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[Report] Post salvo em: {pasta}")
    return pasta
