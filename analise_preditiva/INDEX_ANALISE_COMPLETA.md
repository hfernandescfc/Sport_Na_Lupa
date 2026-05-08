# Índice Completo — Análise Preditiva Série B 2026

**Análise Finalizada:** 2026-05-08  
**Total de Documentos:** 6 relatórios + 6 gráficos + 3 CSVs

---

## 📋 Documentos Principais

### 1. **RESUMO_EXECUTIVO_FINAL.md** ⭐ (LEIA PRIMEIRO)
- Comparação dos 3 contextos de validação
- Rankings de modelos por cenário
- Recomendações estratégicas
- Matriz de decisão (qual modelo para qual caso)
- Limitações e caveats

### 2. **EXEC_SUMMARY_1PAGE.md** (QUICK READ)
- Uma página apenas
- Números-chave
- Decisão final (LR é o recomendado)
- Roadmap de implementação

### 3. **RELATORIO_REMEDIACAO_V2.md**
- Descoberta de target leakage em v1
- Comparação v1 (com leakage) vs v2 (sem leakage)
- Impacto: -32.3 pp (83.1% → 50.8%)
- Conclusão: v2 é realista e confiável

### 4. **RELATORIO_OVERFITTING.md**
- Análise detalhada de overfitting (Cross-Season)
- Train vs Test em 2025→2026
- Por que RandomForest falha em produção
- Recomendação: LR mais confiável

### 5. **RELATORIO_INTRA_SEASON_2025.md**
- Validação em 2025 apenas (R22-R35 vs R36-R38)
- RandomForest vence com 70.6% (gap 2.9%)
- Explicação: dinâmicas estáveis, RF aprende bem
- Backtesting histórico (NOT para produção)

### 6. **RELATORIO_2026_FULL_FEATURES.md**
- Impacto de prog_ratio (features de jogadores)
- LR + FULL: 62.5% (vs 50.0% CORE) = +12.5%
- Overfitting diminui: 20.3% → 15.9%
- Conclusão: prog_ratio é transformador para LR

---

## 📊 Gráficos

### Visualizações Principais

| # | Arquivo | Contexto | Insights |
|---|---|---|---|
| 11 | `11_model_comparison_v2.png` | Cross-Season (v2) | Acurácia + F1-macro, 4 modelos |
| 12 | `12_confusion_matrices_v2.png` | Cross-Season | Matrizes de confusão (v2) |
| 13 | `13_xgboost_importance_v2.png` | Cross-Season | Feature importance (v2) |
| 14 | `14_train_test_comparison.png` | Cross-Season | Train vs Test (v1) |
| 15 | `15_overfitting_risk.png` | Cross-Season | Gap de overfitting análise |
| 16 | `16_intra_season_train_test.png` | Intra-2025 | R22-R35 vs R36-R38 |
| 17 | `17_intra_season_confusion.png` | Intra-2025 | Matrizes de confusão |
| 18 | `18_intra_season_overfitting.png` | Intra-2025 | Risco de overfitting |
| 19 | `19_2026_core_vs_full.png` | Intra-2026 | CORE vs FULL features |
| 20 | `20_2026_full_train_test.png` | Intra-2026 | Train (R1-R5) vs Test (R6-R7) |
| 21 | `21_2026_full_overfitting.png` | Intra-2026 | Risco de overfitting FULL |
| 22 | `22_2026_full_confusion.png` | Intra-2026 | Matrizes de confusão FULL |
| **23** | **`23_resumo_tres_contextos.png`** | **TODOS** | **Comparação lado-a-lado 3 contextos** ⭐ |
| **24** | **`24_overfitting_todos_contextos.png`** | **TODOS** | **Overfitting em todos os cenários** ⭐ |

---

## 📄 Dados (CSV)

| Arquivo | Conteúdo | Linhas |
|---|---|---|
| `model_results_v2.csv` | Métricas v2 (sem target leakage) | 21 |
| `train_test_comparison.csv` | Métricas train vs test cross-season | 22 |
| `train_test_walkforward.csv` | Walk-forward R5-R7 treino-teste | 12 |
| `intra_season_2025_results.csv` | Resultados 2025 R22-R38 | 21 |
| `2026_full_validation_results.csv` | Resultados 2026 R1-R7 (CORE+FULL) | 21 |

---

## 🔬 Scripts Python

| Script | Propósito | Linhas |
|---|---|---|
| `03_modelagem_v2.py` | Modelagem com features pré-match (sem leakage) | ~350 |
| `04_train_test_comparison.py` | Análise de overfitting cross-season | ~300 |
| `05_intra_season_validation.py` | Validação intra-2025 (R22-R38) | ~350 |
| `06_season_2026_validation.py` | Validação 2026 CORE vs FULL features | ~400 |

---

## 🎯 Recomendação Final

### Para Produção (2026 R5+)

```python
model = LogisticRegression(C=0.1, max_iter=500)
features = [
    # 16 pré-match
    "xg_diff", "xg_h", "xg_a", "xg_per_shot_diff",
    "xg_tilt_h", "xg_tilt_diff", "field_tilt_sot_h", "field_tilt_sot_diff",
    "sot_diff", "shots_diff", "poss_diff", "rolling_xg_diff_3",
    "rolling_pts_diff_3", "xg_ctx_diff", "passes_acc_pct_diff", "corners_diff",
    # 2 de jogadores (2026 only)
    "prog_ratio_diff", "prog_ratio_h"
]

# Acurácia esperada: 50.8% (cross-season, conservador)
#                    62.5% (intra-2026, otimista)
# Overfitting gap:  10.9-15.9% (aceitável)
```

---

## 📈 Resumo de Performance

### Contexto 1: Cross-Season (2025→2026)

```
┌─────────────────────────────────────┐
│ MELHOR: LogisticRegression          │
│ Acurácia: 50.8%                     │
│ Gap: 10.9% (aceitável)              │
│ Interpretável: Sim                  │
└─────────────────────────────────────┘

Alternativas:
  RandomForest    50.8% (gap 26.8% - evitar)
  XGBoost         47.5% (gap 41.4% - rejeitar)
```

### Contexto 2: Intra-Season 2025 (R22→R38)

```
┌─────────────────────────────────────┐
│ MELHOR: RandomForest                │
│ Acurácia: 70.6%                     │
│ Gap: 2.9% (praticamente perfeito)   │
│ Uso: Backtesting histórico ONLY     │
└─────────────────────────────────────┘

NÃO use em produção (será diferente em 2026)
```

### Contexto 3: Intra-Season 2026 (R1→R7, FULL)

```
┌─────────────────────────────────────┐
│ MELHOR: LogisticRegression          │
│ Acurácia: 62.5% (com prog_ratio)    │
│ Gap: 15.9% (moderado)               │
│ Ganho vs CORE: +12.5%               │
└─────────────────────────────────────┘

Convergência: LR=RF=XGB em 62.5% (teto)
Diferença: LR chega com gap menor
```

---

## 🔑 Key Takeaways

1. **LogisticRegression é universal** — funciona em todos os cenários (50-68%)

2. **RandomForest é contexto-específico** — excelente em intra-season (70.6%), falha em cross-season (50.8%)

3. **Target leakage foi fatal** — v1 com features derivadas de gols: 83.1% fictício → v2 sem leakage: 50.8% realista

4. **Prog_ratio agrega +12.5%** — dados de jogadores são essenciais para LR em 2026

5. **Dinâmicas mudam entre temporadas** — RF perde 19.8 pp (70.6% → 50.8%) ao ir de 2025 para 2026

6. **50.8% é realista para produção** — prever resultado é inerentemente difícil em esportes

---

## 📚 Leitura Recomendada

1. **Rápida (5 min):** `EXEC_SUMMARY_1PAGE.md`
2. **Média (15 min):** `RESUMO_EXECUTIVO_FINAL.md` + gráficos 23-24
3. **Completa (60 min):** Todos os 6 relatórios + scripts

---

## ✅ Checklist de Implementação

- [ ] Ler EXEC_SUMMARY_1PAGE.md
- [ ] Revisar gráficos 23-24
- [ ] Validar features em dataset 2026
- [ ] Treinar LR + FULL em dados históricos
- [ ] Deploy em produção para R5+
- [ ] Monitorar acurácia real em R6-R7
- [ ] Coletar dados para R8+ revalidação
- [ ] Documentar performance em cada rodada

---

**Análise Completada:** 2026-05-08  
**Confiança:** Alta (3 contextos validados, padrões consistentes)  
**Próximo Review:** 2026-05-15 (após R6-R7 reais)
