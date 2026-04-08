"""
Classificação heurística da origem da narrativa.

Regras:
  - "Orgânico"     -> muitos usuários únicos no início + baixo engajamento inicial
  - "Impulsionado" -> poucos usuários dominando o início + alto engajamento inicial
  - "Misto"        -> sinais contraditórios

A pontuação final é baseada em pesos de 3 fatores:
  1. Concentração de usuários nos primeiros N tweets (0-100)
  2. Engajamento médio inicial vs mediana geral (ratio)
  3. Gini do engajamento total (0-1)
"""

from typing import Dict, Literal, Tuple


# ---------------------------------------------------------------------------
# Parâmetros das heurísticas (ajustáveis)
# ---------------------------------------------------------------------------

# Limiar de concentração top-3 (% dos primeiros tweets)
# > THRESHOLD -> sinal de impulsionamento (poucos dominam início)
CONCENTRACAO_THRESHOLD = 40.0  # %

# Razão engajamento médio inicial / mediana global
# > THRESHOLD -> sinal de impulsionamento (influenciadores no início)
RATIO_ENGAJAMENTO_THRESHOLD = 3.0

# Gini do engajamento total
# > THRESHOLD -> distribuição desigual (impulsionado por poucos)
GINI_THRESHOLD = 0.70

# Mínimo de usuários únicos para considerar orgânico
MIN_USUARIOS_ORGANICO = 8  # nos primeiros N tweets


# ---------------------------------------------------------------------------
# Função principal de classificação
# ---------------------------------------------------------------------------

def classificar_narrativa(
    resumo_origem: Dict,
    metricas_difusao: Dict,
    n_primeiros: int = 20,
) -> Dict:
    """
    Classifica a narrativa como "Orgânico", "Impulsionado" ou "Misto".

    Parâmetros
    ----------
    resumo_origem : dict
        Saída de origin.resumo_origem()
    metricas_difusao : dict
        Saída de diffusion.calcular_metricas_difusao()
    n_primeiros : int
        N de tweets analisados na origem

    Retorna
    -------
    dict com:
        classificacao    : "Orgânico" | "Impulsionado" | "Misto"
        score_impulsao   : float 0-100 (0=orgânico, 100=fortemente impulsionado)
        confianca        : "Alta" | "Média" | "Baixa"
        fatores          : dict com cada fator e se aponta para impulsionamento
        descricao        : texto explicativo
    """
    fatores = {}
    pontos_impulsionamento = 0
    max_pontos = 0

    # -----------------------------------------------------------------------
    # Fator 1: Concentração dos primeiros tweets (peso 40)
    # -----------------------------------------------------------------------
    concentracao = resumo_origem.get("concentracao_top3_pct", 0)
    n_usuarios = resumo_origem.get("n_usuarios_unicos", 0)
    peso_f1 = 40

    if concentracao > CONCENTRACAO_THRESHOLD or n_usuarios < MIN_USUARIOS_ORGANICO:
        sinal_f1 = True  # aponta para impulsionamento
        pontos_impulsionamento += peso_f1
    else:
        sinal_f1 = False
    max_pontos += peso_f1

    fatores["concentracao_inicial"] = {
        "valor": concentracao,
        "threshold": CONCENTRACAO_THRESHOLD,
        "sinal_impulsionamento": sinal_f1,
        "descricao": f"Top-3 usuários: {concentracao:.0f}% dos primeiros {n_primeiros} tweets | "
                     f"{n_usuarios} usuários únicos",
    }

    # -----------------------------------------------------------------------
    # Fator 2: Engajamento médio inicial vs mediana global (peso 35)
    # -----------------------------------------------------------------------
    eng_medio_inicial = resumo_origem.get("engajamento_medio", 0)
    mediana_global = metricas_difusao.get("engajamento", {}).get("p50_mediana", 1)
    mediana_global = max(mediana_global, 0.1)  # evitar divisão por zero
    ratio_eng = eng_medio_inicial / mediana_global
    peso_f2 = 35

    if ratio_eng > RATIO_ENGAJAMENTO_THRESHOLD:
        sinal_f2 = True
        pontos_impulsionamento += peso_f2
    else:
        sinal_f2 = False
    max_pontos += peso_f2

    fatores["engajamento_inicial"] = {
        "valor": round(ratio_eng, 2),
        "threshold": RATIO_ENGAJAMENTO_THRESHOLD,
        "sinal_impulsionamento": sinal_f2,
        "descricao": f"Ratio engajamento inicial/mediana global: {ratio_eng:.1f}x "
                     f"({eng_medio_inicial:.0f} vs {mediana_global:.0f})",
    }

    # -----------------------------------------------------------------------
    # Fator 3: Gini do engajamento total (peso 25)
    # -----------------------------------------------------------------------
    gini_eng = metricas_difusao.get("engajamento", {}).get("gini", 0)
    peso_f3 = 25

    if gini_eng > GINI_THRESHOLD:
        sinal_f3 = True
        pontos_impulsionamento += peso_f3
    else:
        sinal_f3 = False
    max_pontos += peso_f3

    fatores["gini_engajamento"] = {
        "valor": gini_eng,
        "threshold": GINI_THRESHOLD,
        "sinal_impulsionamento": sinal_f3,
        "descricao": f"Gini do engajamento: {gini_eng:.3f} (0=igualitário, 1=concentrado)",
    }

    # -----------------------------------------------------------------------
    # Score final e classificação
    # -----------------------------------------------------------------------
    score_impulsao = (pontos_impulsionamento / max_pontos * 100) if max_pontos > 0 else 0
    n_sinais_impulsionamento = sum(v["sinal_impulsionamento"] for v in fatores.values())

    # Classificação
    if score_impulsao >= 65:
        classificacao = "Impulsionado"
    elif score_impulsao <= 35:
        classificacao = "Orgânico"
    else:
        classificacao = "Misto"

    # Confiança baseada em concordância dos fatores
    if n_sinais_impulsionamento == 3 or n_sinais_impulsionamento == 0:
        confianca = "Alta"
    elif n_sinais_impulsionamento == 2 or n_sinais_impulsionamento == 1:
        confianca = "Média"
    else:
        confianca = "Baixa"

    # Descrição textual
    descricao = _gerar_descricao(classificacao, score_impulsao, fatores, resumo_origem, n_primeiros)

    return {
        "classificacao": classificacao,
        "score_impulsao": round(score_impulsao, 1),
        "confianca": confianca,
        "fatores": fatores,
        "descricao": descricao,
    }


def _gerar_descricao(
    classificacao: str,
    score: float,
    fatores: Dict,
    resumo_origem: Dict,
    n_primeiros: int,
) -> str:
    """Gera texto explicativo humanizado da classificação."""
    n_usuarios = resumo_origem.get("n_usuarios_unicos", 0)
    concentracao = resumo_origem.get("concentracao_top3_pct", 0)
    eng_medio = resumo_origem.get("engajamento_medio", 0)

    if classificacao == "Orgânico":
        return (
            f"Narrativa de origem ORGÂNICA (score de impulsionamento: {score:.0f}/100). "
            f"Os primeiros {n_primeiros} tweets vieram de {n_usuarios} usuários distintos, "
            f"com concentração de apenas {concentracao:.0f}% nos top-3 perfis e "
            f"engajamento médio baixo de {eng_medio:.0f} interações. "
            "O padrão sugere que a ideia emergiu espontaneamente da base da torcida."
        )
    elif classificacao == "Impulsionado":
        return (
            f"Narrativa IMPULSIONADA por contas de alto alcance (score: {score:.0f}/100). "
            f"Os primeiros {n_primeiros} tweets foram dominados por {n_usuarios} perfis, "
            f"com top-3 respondendo por {concentracao:.0f}% do início e "
            f"engajamento médio de {eng_medio:.0f} interações -- muito acima da mediana. "
            "O padrão indica amplificação intencional por influenciadores ou veículos."
        )
    else:
        return (
            f"Narrativa de origem MISTA (score: {score:.0f}/100). "
            f"Iniciou com {n_usuarios} usuários e concentração de {concentracao:.0f}%, "
            "mas os sinais de engajamento são contraditórios. Pode ter emergido organicamente "
            "e sido amplificada depois, ou ter sido iniciada por influenciadores com pouca tração inicial."
        )
