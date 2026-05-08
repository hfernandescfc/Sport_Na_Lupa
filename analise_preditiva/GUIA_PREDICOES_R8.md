# Guia de Previsões — Rodada 8

**Status:** Script pronto, aguardando dados de R8  
**Data:** 2026-05-08  
**Modelo:** LogisticRegression + FULL Features (18)

---

## Situação Atual

### Dataset 2026
```
Total partidas: 70 (R1-R7)
Rodadas completas: 1, 2, 3, 4, 5, 6, 7
Partidas por rodada: 10
Próxima rodada: R8 (aguardando dados)
```

### Modelo Treinado
✅ **LogisticRegression + FULL Features (18 features)**

**Validação:**
- Cross-Season (2025→2026): 50.8% acurácia
- Intra-Season 2026 (R1-R7): 62.5% acurácia

**Status:** Pronto para fazer previsões assim que R8 estiver disponível

---

## Como Executar Previsões

### Prerequisito: Dados de R8

Os dados de R8 devem ser adicionados ao arquivo:
```
analise_preditiva/outputs/match_features.csv
```

Com as seguintes colunas:
```
season, round, home_team, away_team, 
xg_diff, xg_h, xg_a, xg_per_shot_diff, 
xg_tilt_h, xg_tilt_diff, field_tilt_sot_h, field_tilt_sot_diff,
sot_diff, shots_diff, poss_diff, rolling_xg_diff_3, rolling_pts_diff_3,
xg_ctx_diff, passes_acc_pct_diff, corners_diff,
prog_ratio_diff, prog_ratio_h
```

### Executar Script

```bash
python -X utf8 analise_preditiva/07_predicoes_rodada_8.py
```

### Output

Três arquivos serão gerados em `analise_preditiva/outputs/`:

#### 1. `predicoes_rodada_8.csv`
Dados estruturados para análise:
```
match_id, home_team, away_team, prob_away, prob_draw, prob_home, 
predicted_result, max_probability
```

#### 2. `predicoes_rodada_8.txt`
Formato legível para apresentação:
```
1. Away Team            × Home Team
   Away (A):  30.2%  │
   Draw (D):  35.1%  │  Predito: Draw    🟠 35.1%
   Home (H):  34.7%  │
```

#### 3. `relatorio_predicoes_r8.md`
Relatório completo com interpretação

---

## Estrutura de Previsões

### Exemplo de Output para Uma Partida

```
PARTIDA 1: Avaí × Sport Recife

PROBABILIDADES:
  Away (A):  38.5%
  Draw (D):  31.2%
  Home (H):  30.3%

PREVISÃO: Away (38.5%)
CONFIANÇA: 🟠 Moderada (38.5% — abaixo de 45%)
```

### Interpretação de Confiança

| Confiança | Emoji | Significado |
|-----------|-------|------------|
| ≥45% | 🔴 | **Alta** — Resultado bem definido |
| 40-45% | 🟠 | **Média** — Resultado equilibrado |
| <40% | 🟡 | **Baixa** — Incerteza elevada |

---

## Estrutura Completa da Saída

### CSV: predicoes_rodada_8.csv

```
match_id,home_team,away_team,prob_away,prob_draw,prob_home,predicted_result,max_probability
0,Sport Recife,Avaí,0.385,0.312,0.303,Away,0.385
1,Coritiba,Vila Nova,0.402,0.298,0.300,Away,0.402
...
```

**Colunas:**
- `match_id`: Índice da partida (0-9)
- `home_team`: Time mandante
- `away_team`: Time visitante
- `prob_away`: P(resultado = Away)
- `prob_draw`: P(resultado = Draw)
- `prob_home`: P(resultado = Home)
- `predicted_result`: Resultado mais provável
- `max_probability`: Confiança da previsão

### TXT: predicoes_rodada_8.txt

```
================================================================================
PREVISÕES RODADA 8 — SÉRIE B 2026
Modelo: LogisticRegression + FULL Features (18)
================================================================================

PARTIDA 1
Avaí                     × Sport Recife

  PROBABILIDADES:
    Away (A):  38.5%
    Draw (D):  31.2%
    Home (H):  30.3%

  PREVISÃO: Away (38.5%)
────────────────────────────────────────────────────────────────────────────────
```

### MD: relatorio_predicoes_r8.md

Contém:
- Performance do modelo (train accuracy)
- Tabela detalhada por partida
- Interpretação de confiança
- Metodologia usada

---

## Quando os Dados Estarão Disponíveis?

R8 ocorre **após R7**. Assim que as partidas de R8 forem concluídas e sincronizadas:

1. **Extract:** Dados coletados via SofaScore
2. **Transform:** Features calculadas
3. **Load:** Adicionadas ao CSV
4. **Predict:** Script executado

**Timeline Estimado:**
- R8 jogos ocorrem: ~2026-05-11
- Dados disponíveis: ~2026-05-12
- Previsões geradas: ~2026-05-12 (imediato após dados)

---

## Features Utilizadas

### 16 Features Pré-Match (CORE)
```python
[
    "xg_diff", "xg_h", "xg_a", "xg_per_shot_diff",
    "xg_tilt_h", "xg_tilt_diff", "field_tilt_sot_h", "field_tilt_sot_diff",
    "sot_diff", "shots_diff", "poss_diff", "rolling_xg_diff_3",
    "rolling_pts_diff_3", "xg_ctx_diff", "passes_acc_pct_diff", "corners_diff",
]
```

### 2 Features de Jogadores (FULL)
```python
[
    "prog_ratio_diff",  # Diferença em progressões (criação de oportunidades)
    "prog_ratio_h",     # Taxa de progressões do mandante
]
```

**Total:** 18 features para cada partida

---

## Comparação de Acurácia Esperada

Baseado em validações:

| Contexto | Acurácia | Confiança |
|----------|----------|-----------|
| Cross-Season (2025→2026) | 50.8% | ⭐⭐⭐⭐ (mais realista) |
| Intra-Season 2026 (R1-R7) | 62.5% | ⭐⭐⭐⭐⭐ (menos realista — intra-season) |

**Acurácia esperada para R8:** ~50-55% (entre cross-season e intra-season)

---

## Checklist Pré-Previsão

Antes de executar o script, verificar:

- [ ] Dados de R8 adicionados ao CSV
- [ ] Todas as 18 features presentes para R8
- [ ] Nenhum NaN nas features
- [ ] 10 partidas em R8 (uma por time)
- [ ] Script `07_predicoes_rodada_8.py` no diretório

---

## Interpretação dos Resultados

### Se P(A) = 38.5%, P(D) = 31.2%, P(H) = 30.3%

**Leitura:**
```
Em 100 partidas com este perfil:
├─ 38.5 resultam em Away (visitante vence)
├─ 31.2 resultam em Draw (empate)
└─ 30.3 resultam em Home (mandante vence)
```

**Previsão:** Away (resultado mais provável)  
**Confiança:** 38.5% (moderada, mas Away é ligeiramente favoritado)

### Decisão para Apostas (Exemplo Hipotético)

```
Se odds do Away = 2.5 (implícita 40%)
└─ Nossa previsão: 38.5%
└─ Decisão: Evitar — odds desfavorável

Se odds do Away = 3.0 (implícita 33%)
└─ Nossa previsão: 38.5%
└─ Decisão: Valor — odds favorável (38.5% > 33%)
```

---

## Troubleshooting

### Erro: "Nenhuma partida de R8 encontrada"

**Causa:** Dados de R8 não carregados no CSV  
**Solução:** Verificar se `match_features.csv` foi atualizado com R8

### Erro: "NaN values in features"

**Causa:** Features de R8 incompletas  
**Solução:** Sincronizar pipeline completo (sync → transform)

### Previsões parecem aleatórias (P(A)≈P(D)≈P(H)≈33%)

**Causa:** Features com valores muito similares entre times  
**Solução:** Normal em matches bem equilibrados; confiança será baixa

---

## Próximas Rodadas

Uma vez que o script esteja funcionando para R8, pode ser reutilizado para:

- R9, R10, ... R38

**Para cada rodada:**
```bash
# 1. Dados de nova rodada adicionados ao CSV
# 2. Treino atualizado (R1-Rn para prever Rn+1)
# 3. Execute: python 07_predicoes_rodada_8.py
# 4. Resultados salvos automaticamente
```

---

## Referência de Arquivos

| Arquivo | Descrição |
|---------|-----------|
| `07_predicoes_rodada_8.py` | Script principal (reutilizável) |
| `predicoes_rodada_8.csv` | Saída estruturada |
| `predicoes_rodada_8.txt` | Saída legível |
| `relatorio_predicoes_r8.md` | Saída detalhada |
| `analise_preditiva/outputs/match_features.csv` | Dataset (input) |

---

## Modelo Utilizado

**Algoritmo:** LogisticRegression (sklearn)  
**Hiperparâmetros:** C=0.1, max_iter=500  
**Pipeline:** StandardScaler → LogisticRegression  
**Features:** 18 (16 pré-match + 2 de jogadores)

**Razão da Escolha:**
- ✅ Robusto em cross-season (50.8%)
- ✅ Generaliza bem (+12.5% com prog_ratio)
- ✅ Interpretável (pesos das features)
- ✅ Overfitting controlado (10.9-15.9%)

---

## Contato & Próximas Ações

1. **Agora:** Aguardando dados de R8
2. **Quando R8 tiver dados:** Execute `python 07_predicoes_rodada_8.py`
3. **Após previsões:** Comparar com resultados reais para validar

**Script testado e pronto para executar!** ✅
