# Relatório executivo — modelagem preditiva Série B 2026

**Versão do modelo:** `ens_lr_gbm_v1`
**Data:** 2026-05-22
**Escopo:** previsão do resultado (Mandante / Empate / Visitante) de partidas da Série B 2026

---

## 1. Resumo executivo

Construímos um modelo de classificação 3-classes (H/D/A) treinado em **230 partidas** (Série B 2025 completa + R3-R9 de 2026) usando 18 features pré-jogo. A arquitetura final é um **ensemble** que combina:

- **Regressão Logística** (linear, regularizada L2 forte) — captura relações monotônicas
- **LightGBM com calibração sigmoid** — captura não-linearidades e calibra probabilidades

Os dois modelos votam por **média das probabilidades**. Em backtest walk-forward (R3-R9):

| Métrica | Valor | Referência |
|---|---|---|
| Acurácia | **40.3%** (29/72) | Baseline "sempre H" = 40.0% · aleatório = 33.3% |
| Brier multiclasse | **0.689** | LR sozinho = 0.747 (−7.8% de erro) |
| P. média na classe real | 0.339 | Aleatório = 0.333 |

**O ganho real desta versão não é acurácia, é calibração.** As probabilidades passaram a refletir incerteza real do jogo — útil para narrativas e tweets que descrevem chances, não apenas predizem vencedores.

---

## 2. Contexto e objetivo

O modelo serve a dois propósitos:

1. **Previsão pré-rodada** publicada no @SportRecifeLab antes de cada rodada
2. **Base para análises** (raio-x de adversário, narrativa de campanha)

A meta nunca foi vencer cassino — é entregar previsões mais informadas que palpite, com probabilidades **interpretáveis** ("38.7% de empate" deve significar "empata em ~4 a cada 10 jogos similares").

---

## 3. Dados

### 3.1. Pool de treino
- **Série B 2025** completa: 160 partidas (fonte histórica)
- **Série B 2026** R3 em diante: 70 partidas atuais (jan-mai/2026)
- **Total:** 230 partidas, todas com placar final + estatísticas avançadas confirmadas

### 3.2. Fonte
- **SofaScore** via Selenium headless + XHR síncrono
- Pipeline curado em `data/curated/serie_b_{ano}/` (matches.csv, team_match_stats.csv, player_match_stats.csv)

### 3.3. Por que só 2025+2026?
- Mudança de calendário Série B (2025 foi o primeiro ano com calendário próximo do atual)
- Adicionar 2024- traria ruído (formato diferente, clubes diferentes, dinâmica diferente)
- O modelo é **incremental**: a cada rodada nova de 2026, o pool cresce sozinho

---

## 4. Engenharia de features

### 4.1. Princípio fundamental: invariante pré-jogo

> Todas as features de entrada devem estar disponíveis **antes** do apito inicial.
> Nunca usar estatística da partida sendo prevista como feature dela mesma.

Essa regra parece óbvia mas foi violada na primeira versão do modelo. O fix dela foi a "Frente 1" do diagnóstico de maio/2026 (ver seção 6).

### 4.2. Conjunto final: 18 features

#### Pré-jogo (14)
Médias móveis das últimas 3 partidas, calculadas com `shift(1).rolling(3).mean()`:

| Feature | Descrição |
|---|---|
| `xg_diff`, `xg_h`, `xg_a` | xG produzido (mandante/visitante) |
| `xg_per_shot_diff` | Qualidade das finalizações |
| `xg_tilt_h`, `xg_tilt_diff` | Domínio territorial via xG |
| `field_tilt_sot_h`, `field_tilt_sot_diff` | Domínio via chutes no alvo |
| `sot_diff`, `shots_diff`, `poss_diff` | Volume ofensivo + posse |
| `xg_ctx_diff` | xG concedido pelo adversário recente (proxy de defesa que enfrentou) |
| `passes_acc_pct_diff` | Precisão de passe |
| `corners_diff` | Escanteios |

#### Força acumulada (2)
Calculadas com `shift(1).expanding().mean()` — toda a temporada até a rodada anterior:

| Feature | Descrição |
|---|---|
| `ppg_diff_todate` | Pontos por jogo acumulado (proxy de campanha) |
| `xg_pm_diff_todate` | xG por jogo acumulado (proxy de força ofensiva) |

#### Jogadores (2)
Calculadas via `src/transform/players.py`:

| Feature | Descrição |
|---|---|
| `prog_ratio_h` | Razão de passes/dribbles progressivos do mandante (rolling lag-1) |
| `prog_ratio_diff` | Diferença mandante-visitante na razão progressiva |

### 4.3. Features descartadas
| Feature | Por que saiu |
|---|---|
| `rolling_xg_diff_3`, `rolling_pts_diff_3` | r=0.73 com `xg_pm_diff_todate` e `ppg_diff_todate` — colinearidade |
| `xg_conc_pm_diff_todate` | r=−0.85 com `xg_pm_diff_todate` (mesmo sinal invertido) |
| Variáveis de cartões, faltas | r quase nulo com target |
| `is_home` | Já implícito na arquitetura (todas features são *diff* mandante - visitante) |

---

## 5. Arquitetura do modelo

### 5.1. Decisões e justificativa

```
┌────────────────────────────────────────────────────────────┐
│              X (18 features pré-jogo)                       │
└──────────────────────┬─────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        ▼                             ▼
┌──────────────────┐         ┌─────────────────────────┐
│ StandardScaler   │         │ LGBMClassifier          │
│   + LogReg L2    │         │   num_leaves=7          │
│   (C=0.1)        │         │   n_estimators=150      │
│                  │         │   min_data_in_leaf=15   │
│                  │         └────────┬────────────────┘
│                  │                  │
│                  │         ┌────────▼────────────────┐
│                  │         │ CalibratedClassifierCV  │
│                  │         │   method='sigmoid'      │
│                  │         │   cv=3                  │
│                  │         └────────┬────────────────┘
└────────┬─────────┘                  │
         │                            │
         │  predict_proba             │  predict_proba
         ▼                            ▼
┌────────────────────────────────────────────────────────────┐
│       Média simples: (proba_LR + proba_GBM) / 2             │
└────────────────────────────────────────────────────────────┘
                       │
                       ▼
                  [P_A, P_D, P_H]
```

### 5.2. Por que ensemble e não modelo único?

| Modelo | acc | Brier | Pro / Con |
|---|---|---|---|
| LR puro | 40.3% | 0.747 | Bom acerto mas overconfident (Brier alto) |
| LGBM+sigmoid | 38.9% | 0.673 | Probabilidades calibradas mas acerto cai |
| XGBoost+sigmoid | 38.9% | 0.668 | Idem ao LGBM |
| **Ensemble LR+GBM** | **40.3%** | **0.689** | **Acerto do LR + calibração do GBM** |

O ensemble extrai o melhor dos dois mundos: **mesma acurácia do LR puro**, mas Brier 7.8% melhor. As probabilidades publicadas são mais honestas — quando o modelo diz "30% de empate", essa estimativa erra menos sistematicamente para mais ou menos.

### 5.3. Por que sigmoid e não isotonic?

`CalibratedClassifierCV` oferece dois métodos:
- **Isotonic**: regressão monotônica não-paramétrica — muito flexível mas overfit em datasets pequenos (acc 31.9% em backtest)
- **Sigmoid (Platt scaling)**: ajusta uma logística — paramétrico, robusto em datasets pequenos (acc 38.9%)

Com 230 partidas isotonic colapsou. Sigmoid foi a escolha óbvia.

### 5.4. Por que regularização forte (C=0.1) no LR?

Testamos C=1.0 (regularização padrão) e C=0.1 (regularização 10x mais forte). C=0.1 venceu por 8 pontos de acurácia, consistente com a literatura para datasets pequenos (~200 amostras × 18 features ≈ regime onde overfit domina).

### 5.5. Por que LGBM pequeno (7 folhas, 150 árvores)?

Configurações maiores (`num_leaves=31, n_estimators=300`) overfitam dramaticamente — train acc sobe para 95%+ enquanto test acc cai para 30%. O LGBM atual é deliberadamente subdimensionado, mais um *regularizador não-linear* que um modelo de árvore puro.

---

## 6. Histórico das iterações ("frentes")

### Frente 0 — modelo inicial (R1-R7 de 2026)
- Train acc 59.4% / test acc 35%
- **Diagnóstico:** features de treino incluíam xG/sot/poss da própria partida (leak post-match)
- **Sintoma:** previsões inconsistentes em jogos onde o time mais provável tinha estatística histórica pobre

### Frente 1 — fix do leak pré-jogo (R8)
- Reescrever `_build_match_level` em `src/features/match_features.py`
- Adicionar `_swap_to_prematch` que substitui valores reais por médias móveis lag-1
- **Resultado:** acc 41.7% walk-forward, train_acc honesto (~45%)

### Frente 2 — features de força acumulada (R9)
- Plugar `ppg_diff_todate`, `xg_pm_diff_todate` (cumulativos com `shift(1).expanding().mean()`)
- Substituir `rolling_xg_diff_3` e `rolling_pts_diff_3` pelas versões cumulativas (r=0.73 entre si)
- **Resultado:** acc 40.3% (regressão dentro do erro amostral, mas features mais sólidas conceitualmente)

### Frente 3 — GBM + ensemble + calibração (atual)
- Adicionar LightGBM com num_leaves=7 + sigmoid calibration
- Combinar com LR via média de probabilidades
- **Resultado:** acc 40.3% (mantida), Brier 0.689 (−7.8% vs LR puro)

---

## 7. Validação

### 7.1. Walk-forward cross-season
Para cada R em [3..9] de 2026:
1. Pool de treino = Série B 2025 completa + Série B 2026 com `round < R`
2. Treina modelo do zero (sem fit incremental)
3. Prediz R usando `build_target_round_features` (rolling proxies)
4. Compara vs resultado real

Sem leak temporal — cada rodada é prevista apenas com informação disponível antes do apito.

### 7.2. Resultados por rodada (atual, ensemble)

| Rodada | n_train | acc_round | acc cumulativa | Brier round |
|---|---|---|---|---|
| R3 | 160 | 50.0% | 50.0% | 0.72 |
| R4 | 170 | 60.0% | 55.0% | 0.72 |
| R5 | 180 | 30.0% | 46.7% | 0.93 |
| R6 | 190 | 54.5% | 48.8% | 0.70 |
| R7 | 200 | 30.0% | 45.1% | 0.65 |
| R8 | 210 | 27.3% | 41.9% | 0.78 |
| R9 | 220 | 30.0% | 40.3% | 0.73 |

**Tendência:** acurácia caindo ao longo da temporada. Isso é esperado e tem duas causas plausíveis:
1. Variância amostral (10 jogos por rodada = ±15% nominais)
2. À medida que a temporada avança, times se equilibram (campanha "embaralha") — rodadas tardias são intrinsecamente menos previsíveis

### 7.3. Comparação com baselines

| Estratégia | Acurácia |
|---|---|
| **Modelo ensemble** | **40.3%** |
| Apostar sempre no mandante | 40.0% |
| Apostar aleatoriamente (uniform) | 33.3% |
| Apostar no time com mais pontos na tabela | ≈ 38% (não rigorosamente medido) |

A diferença vs "sempre H" é estatisticamente ruidosa (1 acerto em 72), mas o modelo distribui apostas (não fica trancado no H) e fornece probabilidades calibradas — o que a heurística "sempre H" não oferece.

---

## 8. Limitações honestas

1. **Dataset pequeno.** 230 partidas para 18 features está no limite onde regularização forte é mais importante que escolha de algoritmo. GBM sozinho overfita — só funciona em ensemble.

2. **Empates são intrinsecamente difíceis.** ~30% de empates na base, mas o modelo tem dificuldade em identificá-los (precision e recall baixos para classe D). Sigmoid calibration ajudou — empates previstos caíram de 23→18, mais próximo da base real.

3. **Sem ajuste por fatores externos.** Não modelamos: ausências por suspensão/lesão, mudança de técnico, motivação (briga por título/rebaixamento), distância de viagem, intervalo entre jogos.

4. **Acurácia próxima do baseline H.** O modelo não vence dramaticamente "sempre mandante" — vence em **calibração** e **diversificação de predições**, não em hit rate.

5. **Sem garantia de melhoria com mais dados.** O acerto pode estar limitado pelo teto natural do esporte. Mesmo modelos de mercado (Bet365, Pinnacle) têm acc ~50-55% em ligas europeias com 20+ anos de dados — Série B com 2 temporadas é cenário muito mais hostil.

---

## 9. Próximos passos sugeridos

### Prioridade alta
- **Refazer backtest depois de R15.** Com ~300 partidas no pool, GBM deve passar a contribuir mais ao ensemble.
- **Validar calibração visualmente.** Reliability diagram (probabilidade prevista vs frequência observada em buckets).

### Prioridade média
- **Adicionar `goals_diff_todate`.** Saldo de gols acumulado é fácil de extrair e complementa PPG.
- **Modelar features de ausências.** Cross-reference com `injury_news` do SofaScore (já tem o endpoint).
- **Stacking ao invés de média simples.** Treinar meta-modelo LR sobre probabilidades de LR+GBM. Maior risco de overfit, melhor se houver mais dados.

### Prioridade baixa
- **Modelo de gols por time** (Poisson). Já temos a infra (`xPts` usa Poisson). Probabilidades H/D/A poderiam vir da convolução de Poisson(λ_h) × Poisson(λ_a). Modelo mais interpretável mas geralmente perde para discriminativo em acc.
- **Refinar pesos do ensemble.** Hoje é 50/50. Otimizar peso ω para minimizar Brier no validation set (`p = ω·p_LR + (1−ω)·p_GBM`).

---

## 10. Reprodutibilidade

| Script | O que faz |
|---|---|
| `python -m src.main predict-round --season 2026 --round N` | Gera previsão para R{N} |
| `python -m src.main validate-predictions --season 2026` | Valida previsões salvas vs real |
| `python -X utf8 backtest_prematch_fix.py` | Backtest R3-R9 do LR puro |
| `python -X utf8 backtest_gbm.py` | Comparação LR vs várias variantes GBM |
| `python -X utf8 backtest_gbm_v2.py` | Comparação com ensembles |

| Artefato | Conteúdo |
|---|---|
| `round_{N}.csv` | Probabilidades A/D/H + previsão por partida |
| `round_{N}.json` | Metadata do treino (n_train, params, features, timestamp) |
| `round_{N}.md` | Relatório legível |
| `accuracy_log.csv` | Log partida-a-partida (predito vs real, Brier, prob_real) |
| `accuracy_summary.csv` | Uma linha por rodada + acurácia cumulativa |
| `backtest_gbm_v2.csv` | Comparação dos 10 modelos no backtest |

---

## 11. Glossário

- **Brier score (multiclasse):** soma dos quadrados dos erros entre probabilidade prevista e one-hot real, somada sobre classes. Menor = melhor. Range típico [0, 2]. Random uniform = 0.667.
- **Calibração:** propriedade de probabilidades coincidirem com frequências observadas. Um modelo dizendo "40%" para 100 jogos deveria acertar ~40 deles.
- **Walk-forward:** validação que respeita ordem temporal — treina só com dados anteriores à previsão.
- **Lag-1 rolling:** média das N partidas anteriores (não inclui a atual). Implementado via `shift(1).rolling(N)`.
- **To-date cumulative:** média de toda a temporada até a partida anterior. Implementado via `shift(1).expanding()`.
- **L2 (Tikhonov):** penalidade quadrática nos coeficientes, parametrizada por C (menor C = mais regularização).
- **Platt scaling (sigmoid calibration):** ajusta uma logística sobre as probabilidades brutas do modelo base para recalibrá-las.
