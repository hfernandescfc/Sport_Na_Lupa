# Análise de Overfitting — Train vs Test Performance

**Data:** 2026-05-08  
**Análise:** Diferença entre acurácia no treino vs teste (detector de overfitting)

---

## Resumo Executivo

| Modelo | Train | Test | Gap | Diagnóstico |
|---|---|---|---|---|
| **Baseline** | 41.2% | 35.6% | 5.6% | ✅ Aceitável |
| **LogisticRegression** | 61.8% | **50.8%** | 10.9% | ⚠️ Overfitting moderado |
| **RandomForest** | 77.6% | 50.8% | **26.8%** | ❌ Overfitting severo |
| **XGBoost** | 88.8% | 47.5% | **41.4%** | ❌ Overfitting severo |

---

## Análise Detalhada

### 1. **Baseline (41.2% → 35.6%)**
```
Train Accuracy: 41.2%  |  Test Accuracy: 35.6%  |  Gap: 5.6%
```

**Comportamento:** Train ligeiramente acima de test (esperado). O gap pequeno (5.6%) indica que o modelo não está aprendendo padrões espúrios do treino.

**Interpretação:** A baseline sempre prediz a classe majoritária (H). O test é menor porque a distribuição de classes em 2026 é ligeiramente diferente de 2025.

✅ **Robusto inter-temporada.**

---

### 2. **Logistic Regression (61.8% → 50.8%)**
```
Train Accuracy: 61.8%  |  Test Accuracy: 50.8%  |  Gap: 10.9%
```

**Comportamento:** 50.8% de acurácia real no teste, com um gap moderado de 10.9%.

**Interpretação:**
- O modelo aprende padrões reais (train 61.8% vs baseline 41.2% = +20.6 pp)
- Mas generaliza bem (test 50.8% vs baseline 35.6% = +15.2 pp)
- A perda de 11 pp entre treino e teste é **razoável** para um modelo linear com dados limitados

⚠️ **Overfitting moderado, mas aceitável. Modelo recomendado para produção.**

---

### 3. **Random Forest (77.6% → 50.8%)**
```
Train Accuracy: 77.6%  |  Test Accuracy: 50.8%  |  Gap: 26.8%
```

**Comportamento:** O modelo memoriza o treino (77.6%) mas falha completamente no teste (50.8%).

**Interpretação:**
- RF com `max_depth=5, min_samples_leaf=8` ainda é muito complexo para 170 amostras de treino
- O modelo aprende características muito específicas de 2025 que não generalizam para 2026
- Test accuracy = 50.8%, que é o **mesmo do Logistic Regression**, sugerindo que RF não agrega valor real

❌ **Overfitting severo. Não recomendado.**

---

### 4. **XGBoost (88.8% → 47.5%)**
```
Train Accuracy: 88.8%  |  Test Accuracy: 47.5%  |  Gap: 41.4%
```

**Comportamento:** Pior performer. O modelo praticamente memoriza o treino.

**Interpretação:**
- XGBoost treina para **88.8%** (praticamente perfeito) em apenas 170 amostras
- Mas test cai para 47.5% — **pior que a baseline** (35.6%)
- Este modelo está **anti-generalizando**: aprende padrões tão específicos do treino que os efeitos são negativos no teste

❌ **Overfitting severo e contraproducente. Rejeitado.**

---

## Walk-Forward: Validação Incremental

### Cross-Season vs Walk-Forward

| Split | Baseline | LR | RF | XGBoost |
|---|---|---|---|---|
| **Cross-Season** | 5.6% | 10.9% | 26.8% | 41.4% |
| **Walk-Forward (média)** | -5.8% | -10.3% | 20.3% | 37.7% |

**Walk-Forward R6 (surpresa positiva):**
```
Round 6:  LR test=70.0% (train=57.6%) → OUTPERFORMANCE
          RF test=80.0% (train=78.1%) → quase sem gap
```

Este resultado é anomalia (apenas 10 amostras/fold). Deve ser tratado com ceticismo.

---

## Por Que RF e XGBoost Falham?

### Problema 1: Complexidade vs Dados

- **Treino:** 170 partidas em 2025
- **Teste:** 59 partidas em 2026
- **Ratio:** ~2.9:1 (treino:teste)

Com apenas 170 amostras, um RF com 200 árvores tem **muito espaço para memorizar**.

### Problema 2: Mudanças Estruturais Inter-Temporada

As dinâmicas de 2025 → 2026 mudaram:
- **Novos técnicos, novas táticas** (alguns clubes)
- **Mercado: transferências, lesões**
- **Força relativa dos times muda** (alguns crescem, outros caem)

RF e XGBoost capturam a distribuição específica de 2025. Quando 2026 chega com dinâmicas diferentes, o modelo falha.

LR, sendo mais simples, captura apenas os padrões mais robustos e estáveis inter-temporada.

### Problema 3: Features Não-Estacionárias

Nossas features (xG, posse, chutes, etc.) têm **distribuições diferentes** entre 2025 e 2026:
- Alguns clubes melhoraram sua eficiência ofensiva
- Outros tiveram ataques piores
- A variância geral pode ter mudado

Modelos complexos tentam aprender a distribuição específica de 2025. Modelos simples aprendem apenas o padrão linear, que é mais robusto.

---

## Recomendação Final

### ✅ **Usar: Logistic Regression**

**Por quê:**
1. **10.9% de gap é aceitável** para um modelo simples com dados limitados
2. **Generaliza bem:** 50.8% no teste é 15.2 pp acima do baseline (40% melhora)
3. **Interpretável:** Coeficientes das features mostram relação com resultado
4. **Robusto:** Não memoriza, não aprende padrões espúrios específicos de uma temporada
5. **Simples:** StandardScaler + LogisticRegression = sem tuning complexo

### ❌ **Evitar: Random Forest e XGBoost**

**Por quê:**
1. RF: 26.8% gap, não melhor que LR em produção
2. XGBoost: 41.4% gap, **anti-generaliza**, pior que baseline
3. Ambos aprendem padrões espúrios de 2025 que não valem em 2026
4. Dataset pequeno (170 treino) não suporta complexidade destes modelos

---

## Próximas Etapas

### 1. **Implementar LR em Produção**
```python
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("model", LogisticRegression(C=0.1, max_iter=500)),
])

# Treinar em 2025, usar em 2026 prognósticos
pipeline.fit(X_train_2025, y_train_2025)
pred_2026 = pipeline.predict(X_test_2026)  # 50.8% acurácia esperada
```

### 2. **Monitorar Degradação em Tempo Real**
À medida que 2026 avança (R8+), medir acurácia real vs esperado:
- Se cair abaixo de 45%, investigar mudanças estruturais do campeonato
- Se subir acima de 55%, features podem estar se estabilizando

### 3. **Feature Selection**
Remover features com baixa estabilidade inter-temporada:
- `rolling_xg_diff_3` pode ser muito sensível a forma recente
- Preferir features agregadas ao longo da temporada

### 4. **Regularização Alternativa**
Se overfitting persistir com LR, tentar:
- L1 (Lasso) em vez de L2: `penalty='l1', solver='saga'`
- Aumentar C para 0.01 (mais regularização)

---

## Conclusão

A análise Train vs Test revelou uma **escolha crítica:**

- **LR: O vencedor silencioso** — 50.8% acurácia real, generaliza bem, sem overfitting severo
- **RF/XGBoost: Fáceis de enganar** — memorizam 2025, falham em 2026

**Para produção (R5+): Usar Logistic Regression. Período: 2025→2026.**
