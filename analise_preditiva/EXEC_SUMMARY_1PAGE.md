# Executive Summary — Uma Página

## O Desafio
Prever resultado de partidas (Home/Draw/Away) da Série B 2026 com features estatísticas pré-match.

---

## O Que Descobrimos

### 🎯 Três Cenários de Validação

| Cenário | Train | Test | Vencedor | Acurácia |
|---|---|---|---|---|
| **Cross-Season** (2025→2026) | 2025 completo | 2026 completo | **LR** | **50.8%** ✅ |
| **Intra-2025** (R22-R38) | Rodadas iniciais | Rodadas finais | RF | 70.6% |
| **Intra-2026** (R1-R7) | R1-R5 | R6-R7 | **LR** | **62.5%** ✅ |

**O mais importante:** Cross-season = produção real = **LR 50.8%**

---

## O Achado Crítico: Rankings Mudam

```
Intra-temporada (dinâmicas estáveis):  RF vence (70.6%, praticamente sem overfitting)
Cross-season (dinâmicas mudam):        LR vence (50.8%, confiável, gap 10.9%)
```

**Por quê?** RandomForest memoriza distribuições de 2025 (técnicos, táticas, força relativa). Quando 2026 chega com configurações diferentes, o modelo falha (-19.8 pp).

---

## Modelo Recomendado

### ✅ LogisticRegression + FULL Features (18)

```
Deploy para 2026 R5+ com confiança

Acurácia esperada:   50-62% (conservador: 50.8%)
Overfitting gap:     10-16% (aceitável)
Interpretabilidade:  Excelente (ver pesos)
Robustez:            Funciona em todos os cenários
```

### ❌ Evitar

- **RandomForest:** Vence em intra-season (70.6%), mas falha em produção (50.8%). Gap severo (26.8%).
- **XGBoost:** Memoriza agressivamente (gap 24-41%). Nunca use em cross-season.

---

## Features

### CORE (16 — suficiente)
xG, posse, chutes, forma recente, contexto, passes, escanteios

### FULL (18 — melhor em 2026)
CORE + prog_ratio_diff + prog_ratio_h (dados de jogadores)

**Ganho:** +12.5% para LR em intra-2026 (50% → 62.5%)

---

## Roadmap

| Fase | Ação | Quando |
|---|---|---|
| **Fase 1** | Deploy LR + FULL em produção | Agora (R5+) |
| **Fase 2** | Monitorar acurácia real vs esperado | R8-R15 |
| **Fase 3** | Revalidar se dinâmicas convergem | R16+ |

---

## Números-Chave

| Métrica | Valor |
|---|---|
| Datasets analisados | 3 contextos |
| Total partidas | 452 (em validações cruzadas) |
| Modelos testados | 4 (Baseline, LR, RF, XGB) |
| Melhor cross-season | LR 50.8% |
| Melhor intra-season | RF 70.6% (histórico) |
| Features utilizadas | 16-18 pré-match + player-derived |

---

## Risco e Mitigação

| Risco | Mitigação |
|---|---|
| Dinâmicas mudam (lesões, técnicos) | LR é robusto a mudanças |
| Dataset pequeno (53 partidas em 2026) | Usar validação crescente (R1-R5, R1-R6, etc.) |
| Classe desbalanceada | Monitorar F1-macro, não só acurácia |
| Features retrospectivas | Aceitar like: não capturam estado real |

---

## Conclusão

**LogisticRegression com CORE features é o modelo universal:** funciona em todos os cenários (50-68% acurácia), resiste a mudanças de temporada, interpelável e com overfitting controlado.

**FULL features (prog_ratio) agregam +12.5%** para LR em 2026, ideal quando dados de jogadores estão disponíveis.

**Confiança:** Alta. Validado em 3 contextos temporalmente distintos.

---

## Próximas Ações

1. ✅ **Deploy LR + FULL para prognósticos R5-R7**
2. ⏳ **Coletar dados reais de acurácia em R6-R7**
3. 🔄 **Revalidar com crescimento incremental de dados (R1-R8, R1-R9, etc.)**
4. 🎯 **Considerar ensemble se performance degradar**

---

**Data:** 2026-05-08  
**Documentação Completa:** Ver `RESUMO_EXECUTIVO_FINAL.md`  
**Gráficos:** 23_resumo_tres_contextos.png, 24_overfitting_todos_contextos.png
