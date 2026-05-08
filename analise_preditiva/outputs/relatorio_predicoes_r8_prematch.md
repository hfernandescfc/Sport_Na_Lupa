# Previsões Pré-Jogo Rodada 8 — Série B 2026

**Data:** 2026-05-08
**Modelo:** LogisticRegression + FULL Features (18)
**Treino:** Rodadas 1-7 (70 partidas)
**Features:** Construídas via rolling proxies (window=3) do histórico R1-R7

---

## Metodologia

As features de R8 foram construídas usando médias móveis de R1-R7:

| Feature | Cálculo |
|---|---|
| `xg_h`, `xg_a`, `shots_diff`, `sot_diff`, etc. | rolling_mean(R1-R7, window=3) |
| `rolling_xg_diff_3`, `rolling_pts_diff_3` | Média dos últimos 3 jogos |
| `prog_ratio_h`, `prog_ratio_diff` | rolling_mean de progressive carries (player stats) |

Isto permite previsões **antes** dos jogos acontecerem, usando apenas histórico.

---

## Previsões Detalhadas

### Partida 1: Vila Nova FC × Goiás

| Resultado | Probabilidade |
|-----------|---------------|
| Away (A)  | 82.95% |
| Draw (D)  | 15.38% |
| Home (H)  | 1.66% |

**Previsão:** Away (83.0%)

### Partida 2: Cuiabá × Athletic Club

| Resultado | Probabilidade |
|-----------|---------------|
| Away (A)  | 67.08% |
| Draw (D)  | 25.50% |
| Home (H)  | 7.42% |

**Previsão:** Away (67.1%)

### Partida 3: Sport Recife × Ponte Preta

| Resultado | Probabilidade |
|-----------|---------------|
| Away (A)  | 35.20% |
| Draw (D)  | 35.19% |
| Home (H)  | 29.61% |

**Previsão:** Away (35.2%)

### Partida 4: Atlético Goianiense × Ceará

| Resultado | Probabilidade |
|-----------|---------------|
| Away (A)  | 68.55% |
| Draw (D)  | 26.97% |
| Home (H)  | 4.48% |

**Previsão:** Away (68.5%)

### Partida 5: Operário-PR × CRB

| Resultado | Probabilidade |
|-----------|---------------|
| Away (A)  | 40.21% |
| Draw (D)  | 33.95% |
| Home (H)  | 25.84% |

**Previsão:** Away (40.2%)

### Partida 6: Criciúma × Juventude

| Resultado | Probabilidade |
|-----------|---------------|
| Away (A)  | 65.40% |
| Draw (D)  | 19.46% |
| Home (H)  | 15.14% |

**Previsão:** Away (65.4%)

### Partida 7: São Bernardo × Londrina

| Resultado | Probabilidade |
|-----------|---------------|
| Away (A)  | 58.59% |
| Draw (D)  | 39.85% |
| Home (H)  | 1.57% |

**Previsão:** Away (58.6%)

### Partida 8: América Mineiro × Náutico

| Resultado | Probabilidade |
|-----------|---------------|
| Away (A)  | 27.49% |
| Draw (D)  | 22.85% |
| Home (H)  | 49.66% |

**Previsão:** Home (49.7%)

### Partida 9: Fortaleza × Avaí

| Resultado | Probabilidade |
|-----------|---------------|
| Away (A)  | 90.41% |
| Draw (D)  | 7.43% |
| Home (H)  | 2.16% |

**Previsão:** Away (90.4%)

### Partida 10: Botafogo-SP × Grêmio Novorizontino

| Resultado | Probabilidade |
|-----------|---------------|
| Away (A)  | 56.03% |
| Draw (D)  | 25.98% |
| Home (H)  | 17.99% |

**Previsão:** Away (56.0%)

### Partida 11: São Bernardo × Londrina

| Resultado | Probabilidade |
|-----------|---------------|
| Away (A)  | 58.59% |
| Draw (D)  | 39.85% |
| Home (H)  | 1.57% |

**Previsão:** Away (58.6%)

---

## Interpretação de Confiança

- **Alta (≥45%):** Resultado bem definido
- **Média (40-45%):** Resultado equilibrado
- **Baixa (<40%):** Incerteza elevada

