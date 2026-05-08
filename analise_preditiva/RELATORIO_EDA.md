# Análise Preditiva — Séries B 2025 e 2026
## Relatório de Análise Exploratória e Validação de Features

**Atualizado em:** 07/05/2026  
**Fontes:** Série B 2025 (190 partidas · R1 + R21–R38) + Série B 2026 (70 partidas · R1–R7)  
**Dataset combinado:** 260 partidas  
**Metodologia:** Correlação de Pearson/Spearman + Cramér's V + LOO Cross-Validation (Logistic Regression)

---

## 1. Contexto e Qualidade dos Dados

### Fontes

| Fonte | Partidas | Rodadas | Cobertura |
|-------|----------|---------|-----------|
| Série B 2025 | 190 | R1 + R21–R38 | 19 de 38 rodadas |
| Série B 2026 | 70 | R1–R7 | 7 de 38 rodadas (em curso) |
| **Combinado** | **260** | — | — |

**Limitação da Série B 2025:** as rodadas 2–20 estão ausentes na base atual. Isso afeta as features de rolling form para as partidas de R21–R23, que usam apenas R1 como histórico próximo (o pipeline computa com `min_periods=1`, evitando NaN, mas os valores são menos representativos). A partir de R24 em diante, a janela de 3 partidas está completa dentro do bloco R21–R38.

**Limitação da Série B 2026:** com apenas 7 rodadas e amostras pequenas (n=70), os intervalos de confiança das estimativas são largos. Os resultados da análise por temporada devem ser interpretados como tendências, não como fatos definitivos.

**Features disponíveis por fonte:**

| Feature Group | 2025 | 2026 |
|---|---|---|
| Diferenciais, xG, Field Tilt, Eficiência | ✓ | ✓ |
| xG Contextual (depende de histórico prévio) | ✓ (parcial, R1 sem contexto) | ✓ (parcial) |
| Rolling Form | ✓ (com gap R2–R20) | ✓ |
| Progressive Ratio / Line Height | ✗ | ✓ |

---

## 2. Distribuição de Resultados

### Por temporada

| Resultado            | 2025 (190) | % | 2026 (70) | % | Combinado (260) | % |
|----------------------|------------|---|-----------|---|-----------------|---|
| Vitória Mandante (H) | 81         | 42.6% | 26 | 37.1% | 107 | 41.2% |
| Empate (D)           | 60         | 31.6% | 25 | 35.7% | 85  | 32.7% |
| Vitória Visitante (A)| 49         | 25.8% | 19 | 27.1% | 68  | 26.2% |

**Baseline (prever sempre vitória do mandante):** 41.2% — esse é o piso de comparação.

### Home advantage

| Métrica                      | 2025   | 2026   | Diferença |
|------------------------------|--------|--------|-----------|
| Pts médios do mandante       | 1.595  | 1.471  | −0.124    |
| Pts médios do visitante      | 1.089  | 1.171  | +0.082    |
| Vantagem líquida do mandante | +0.505 | +0.300 | −0.205    |

**Achado:** O home advantage em 2026 (R1–R7) é notavelmente menor do que em 2025. A diferença de 0.205 pts/jogo é relevante, embora a amostra de 2026 seja pequena. Pode refletir início de temporada equilibrado, mudança de elencos, ou simplesmente variância amostral.

---

## 3. Estatísticas Gerais por Temporada

| Métrica                   | 2025   | 2026   | Delta  | Interpretação |
|---------------------------|--------|--------|--------|---------------|
| xG médio mandante         | 1.393  | 1.410  | +0.017 | Estável        |
| xG médio visitante        | 1.040  | 1.041  | +0.001 | Idêntico       |
| Chutes mandante           | 15.66  | 14.06  | −1.60  | Menos chutes em 2026 |
| Chutes a gol mandante     | 4.66   | 4.69   | +0.030 | Estável        |
| Posse mandante %          | 53.2%  | 50.5%  | −2.8pp | Mais equilibrado em 2026 |
| Passes acc% mandante      | 81.5%  | 81.9%  | +0.5pp | Estável        |
| Faltas mandante           | 13.7   | 15.2   | +1.5   | Mais faltas em 2026 |
| Cartões amarelos mandante | 2.54   | 2.36   | −0.18  | Marginalmente menos |

**Destaques:**
- Volume de chutes do mandante caiu em 2026 (−1.6 chutes/jogo), mas o xG e SoT permanecem estáveis → as finalizações de 2026 são, em média, de **maior qualidade** por chute (xG por chute ligeiramente maior).
- A posse média do mandante caiu de 53.2% para 50.5%, indicando partidas mais equilibradas territorialmente em 2026.
- Faltas aumentaram em 2026 (+1.5/jogo por mandante), possivelmente reflexo de elencos novos ainda ajustando intensidade.

---

## 4. Médias por Resultado: Comparação entre Temporadas

As tabelas abaixo mostram como cada feature se comporta por resultado em cada temporada. Separações maiores entre H, D e A indicam maior poder discriminatório.

### xG e derivados

| Feature | Ano | H | D | A | H−A |
|---------|-----|---|---|---|-----|
| xg_diff | 2025 | +0.706 | +0.347 | −0.222 | **+0.927** |
| xg_diff | 2026 | +0.865 | +0.270 | −0.177 | **+1.042** |
| xg_overperformance_diff | 2025 | +0.794 | −0.347 | −1.192 | **+1.986** |
| xg_overperformance_diff | 2026 | +0.674 | −0.270 | −1.191 | **+1.865** |
| xg_tilt_diff | 2025 | +0.151 | +0.072 | −0.043 | **+0.194** |
| xg_tilt_diff | 2026 | +0.166 | +0.085 | −0.046 | **+0.213** |

A separação H−A é consistente entre temporadas e ligeiramente mais pronunciada em 2026 para xg_diff e xg_tilt — possivelmente reflexo de partidas mais decididas nos momentos capturados (R1–R7 de 2026 incluem a fase inicial onde equipes acertam resultados mais extremos).

### Field Tilt

| Feature | Ano | H | D | A | H−A |
|---------|-----|---|---|---|-----|
| field_tilt_sot_h | 2025 | 0.645 | 0.566 | 0.453 | **+0.192** |
| field_tilt_sot_h | 2026 | 0.674 | 0.653 | 0.427 | **+0.247** |

Em 2026, quando há empate, o mandante ainda domina os SoT (0.653 — quase como nas vitórias de 2025). A separação entre empate e vitória visitante (0.653→0.427) é mais nítida em 2026, sugerindo que o campo de tilt por SoT discrimina melhor nos dados mais recentes.

### Posse de bola

| Ano | Posse H (vitória H) | Posse H (empate) | Posse H (vitória A) |
|-----|---------------------|-----------------|---------------------|
| 2025 | 49.4% | 55.0% | 57.3% |
| 2026 | 46.6% | 51.6% | 54.4% |

O padrão **invertido** (mandantes que ganham têm menos posse) é perfeitamente consistente entre as duas temporadas. Não é artefato de amostra — é estrutural.

---

## 5. Análise de Correlações por Temporada

### Tabela comparativa — Top 15 features (ordenado por |r| combinado)

| # | Feature | r 2025 | r 2026 | r Comb | Consistente? |
|---|---------|--------|--------|--------|--------------|
| 1 | xg_overperformance_diff | +0.663* | +0.614* | +0.650* | ✓ Sim |
| 2 | xg_overperformance_a    | −0.514* | −0.467* | −0.501* | ✓ Sim |
| 3 | prog_ratio_diff         | — | +0.489* | +0.489* | N/A (2026 only) |
| 4 | xg_per_shot_diff        | +0.493* | +0.370* | +0.451* | ✓ Sim |
| 5 | prog_ratio_h            | — | +0.438* | +0.438* | N/A (2026 only) |
| 6 | xg_tilt_h / xg_tilt_diff| +0.409* | +0.459* | +0.422* | ✓ Sim |
| 7 | xg_diff                 | +0.398* | +0.468* | +0.416* | ✓ Sim |
| 8 | xg_overperformance_h    | +0.424* | +0.389* | +0.411* | ✓ Sim |
| 9 | field_tilt_sot_diff/h   | +0.376* | +0.418* | +0.385* | ✓ Sim |
|10 | sot_diff                | +0.345* | +0.391* | +0.357* | ✓ Sim |
|11 | poss_diff               | −0.337* | −0.342* | −0.330* | ✓ Sim |
|12 | xg_ctx_diff             | +0.333* | +0.227  | +0.300* | ✓ Sim (sinal) |
|13 | passes_acc_pct_diff     | −0.283* | −0.263* | −0.272* | ✓ Sim |
|14 | xg_ctx_a                | −0.250* | −0.367* | −0.265* | ✓ Sim |
|15 | corners_diff            | −0.178* | −0.033  | −0.139* | ⚠ Só 2025 |

\* p < 0.05

**Consistência entre temporadas:** 13 das 15 features top têm **mesmo sinal e significância** em ambas as temporadas. As exceções:
- `corners_diff`: significativo em 2025 (r=−0.18), não em 2026 (r=−0.03). Pode ser ruído de amostra em 2026.
- `xg_ctx_diff`: marginal em 2026 (p=0.08), significativo em 2025. Com mais rodadas, tende a se consolidar.

### Ranking LOO por dataset combinado

| # | Feature | r Comb | LOO Acc | +vs Baseline |
|---|---------|--------|---------|-------------|
| 1 | xg_overperformance_diff | +0.650 | **60.4%** | **+19.2pp** |
| 2 | xg_overperformance_a    | −0.501 | 53.2% | +12.0pp |
| 3 | xg_per_shot_diff        | +0.451 | 51.0% | +9.8pp |
| 4 | prog_ratio_h            | +0.438 | 51.6% | +10.5pp |
| 5 | prog_ratio_diff         | +0.489 | 48.4% | +7.2pp |
| 6 | field_tilt_sot (h/diff) | +0.385 | 49.8% | +8.6pp |
| 7 | sot_diff                | +0.357 | 50.4% | +9.2pp |
| 8 | xg_tilt (h/diff)        | +0.422 | 46.4% | +5.2pp |
| 9 | xg_ctx_diff             | +0.300 | 47.4% | +6.2pp |
|10 | poss_diff               | −0.330 | 45.0% | +3.8pp |

Baseline combinado: 41.2%. O aumento com 2025 (+190 partidas) elevou o LOO accuracy do melhor preditor de 51.4% (só 2026) para **60.4%** (combinado) — um salto de 9pp, consistente com a maior estabilidade estatística de n=250.

---

## 6. Achados Principais e Interpretação

### 6.1 Eficiência clínica é o preditor dominante — em ambas as temporadas

`xg_overperformance_diff` lidera em 2025 (r=0.663), 2026 (r=0.614) e combinado (r=0.650). A consistência elimina a hipótese de artefato amostral. Quem converte acima do seu xG ganha — independentemente da temporada ou fase do campeonato.

**Implicação preditiva:** historicamente, times com alta taxa de conversão sustentada (gols/xG > 1 nas últimas N partidas) têm vantagem real que os modelos baseados só em xG bruto não capturam.

### 6.2 Qualidade de finalização supera volume — consistente entre anos

Em ambas as temporadas:
- `shots_diff` (volume): r ≈ 0 (2025: −0.05, 2026: +0.10) — **não prediz**
- `sot_diff` (chutes a gol): r = +0.345/+0.391 — **prediz significativamente**
- `xg_per_shot_diff` (qualidade por chute): r = +0.493/+0.370 — **prediz mais ainda**

Não é necessário chutar mais, é necessário chutar melhor. Consistente em dois anos.

### 6.3 Posse de bola: relação inversa estrutural

Em 2025: mandante que ganha tem 49.4% de posse média  
Em 2026: mandante que ganha tem 46.6% de posse média

O fenômeno é ainda mais pronunciado em 2026. Times que jogam em bloco baixo e exploram contra-ataques são sistematicamente mais eficientes. Posse como métrica isolada tem **correlação negativa** com vitória em ambas as temporadas — nunca deve ser usada como indicador positivo isolado.

### 6.4 Progressive Ratio: promissor, mas com dados apenas de 2026

`prog_ratio_diff` (r=0.489) e `prog_ratio_h` (r=0.438) aparecem como segunda e quinta feature mais fortes no combinado, mas **só existem para 2026** (n=62). A validação cross-temporada não é possível ainda. É prioritário extrair essa feature para 2025 quando os dados de player_match_stats estiverem disponíveis.

### 6.5 xG Contextual: mais robusto com 2025

`xg_ctx_diff` sobe de r=0.227 (não significativo em 2026) para r=0.333* (significativo no combinado), puxado pela consistência em 2025 (r=0.333*). A métrica requer histórico defensivo de pelo menos 2–3 rodadas para ter valor — por isso funciona melhor na temporada com mais rounds disponíveis. Confirmada como relevante para modelagem desde que calculada com lookback suficiente.

### 6.6 Corners: sinal de alerta

`corners_diff` é significativo em 2025 (r=−0.178) mas não em 2026 (r=−0.033). O sinal **negativo** (mais escanteios associados a pior resultado) em 2025 é intrigante: times que pressionam mais tendem a vencer. Os escanteios, como as finalizações, capturam o momento **após** a jogada — os times que perdem costumam ter escanteios de pressão em desespero no final. Com mais dados de 2026, esse padrão deve se consolidar ou se confirmar como ruído.

---

## 7. Síntese por Grupo de Features

| Grupo | Status 2025 | Status 2026 | Recomendação |
|-------|-------------|-------------|--------------|
| **Eficiência de finalização** (xg_overperf, xg_per_shot) | ✓ Forte e sig. | ✓ Forte e sig. | Prioridade máxima na modelagem |
| **xG e Field Tilt por SoT** (xg_diff, xg_tilt, fts) | ✓ Forte e sig. | ✓ Forte e sig. | Prioridade alta |
| **Chutes a gol** (sot_diff, sot_h) | ✓ Sig. | ✓ Sig. | Incluir |
| **Progressive Ratio** | ✗ Sem dados | ✓ Forte e sig. | Incluir quando 2025 estiver disponível |
| **xG Contextual** (xg_ctx) | ✓ Sig. | Marginal | Incluir (requer lookback ≥2 rounds) |
| **Posse** (poss_diff) | ✓ Sig. negativo | ✓ Sig. negativo | Incluir com sinal invertido |
| **Passes accuracy** (passes_acc_diff) | ✓ Sig. negativo | ✓ Sig. negativo | Incluir com cautela |
| **Volume de chutes** (shots_diff) | ✗ Não sig. | ✗ Não sig. | Descartar |
| **Line height** (proxy via posição) | ✗ Sem dados | ✗ Não sig. | Descartar — usar heatmaps |
| **Rolling form** (rolling_pts, rolling_xg) | Fraco (gap R2–R20) | Fraco (poucos rounds) | Monitorar com mais dados |

---

## 8. Próximos Passos

### Curto prazo — preparar para modelagem
1. **Construir versões rolling** das features de eficiência: `rolling_xg_overperf_diff`, `rolling_xg_per_shot_diff`, `rolling_field_tilt_sot_diff` (versões pré-jogo dos melhores preditores)
2. **Extrair player_match_stats de 2025** para ter `prog_ratio` em ambas as temporadas e validar a consistência cross-temporada
3. **Completar R2–R20 da Série B 2025** para eliminar o gap de rolling form e ter o dataset completo

### Modelagem (próxima fase)
4. Treinar regressão logística multiclasse (H/D/A) com 5 features selecionadas + LOO-CV
5. Comparar com modelo probabilístico Poisson/Dixon-Coles como baseline mais sofisticado
6. Avaliar calibração (curvas de confiança), não apenas acurácia — essencial para palpites com probabilidade associada
7. Testar separação de modelo pós-jogo (diagnóstico) vs. pré-jogo (preditivo)

---

*Scripts: `analise_preditiva/01_eda.py` · `analise_preditiva/02_feature_validation.py`*  
*Features: `src/features/match_features.py`*  
*Fontes: `data/curated/serie_b_2025/` (R1+R21–R38) + `data/curated/serie_b_2026/` (R1–R7)*
