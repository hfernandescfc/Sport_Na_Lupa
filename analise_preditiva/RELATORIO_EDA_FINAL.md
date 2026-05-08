# Análise Preditiva Série B 2026 — Relatório Final

**Data:** 2026-05-07  
**Dataset:** Série B 2025 (192 matches R1-R38) + Série B 2026 (70 matches R1-R7)  
**Total:** 262 partidas com team-level stats; 132 com player-level stats (2026)

---

## Resumo Executivo

### Dados Disponíveis
- **2025:** 192 partidas (R1, R21-R38) com stats de time (xG, shots, posse, etc.)
  - **Indisponível:** Player stats (Selenium timeout na extração)
  - **Implicação:** Métricas player-dependent (prog_ratio, line_height) = NaN
  
- **2026:** 70 partidas (R1-R7) com stats de time + player
  - **Disponível:** xG, shots, posse, progressive carries, positioning

### Top 10 Features Preditivas (LOO Accuracy)
1. **xg_overperformance_diff** — r=+0.650, LOO=60.4%
2. **xg_overperformance_a** — r=-0.501, LOO=53.2%
3. **prog_ratio_diff** — r=+0.489, LOO=48.4% *(2026 only, n=62)*
4. **xg_per_shot_diff** — r=+0.451, LOO=51.0%
5. **prog_ratio_h** — r=+0.438, LOO=51.6% *(2026 only)*
6. **xg_tilt_h** — r=+0.422, LOO=46.4%
7. **xg_tilt_diff** — r=+0.422, LOO=46.4%
8. **xg_diff** — r=+0.416, LOO=46.0%
9. **xg_overperformance_h** — r=+0.411, LOO=45.2%
10. **field_tilt_sot_h** — r=+0.385, LOO=49.8%

### Validação Cross-Season
- **13 de 15** top features mostram correlação consistente (mesmo sinal, magnitude similar) entre 2025 e 2026
- Exceções: `prog_ratio_*` (dados player-level indisponíveis em 2025)
- Conclusão: **Features team-level são robustas e generalizáveis**

---

## Distribuição de Resultados

| Temporada | H (%) | D (%) | A (%) | Vantagem Mandante |
|---|---|---|---|---|
| **2025** | 42.6% | 22.9% | 34.5% | +0.505 pts |
| **2026** | 37.1% | 24.3% | 38.6% | +0.300 pts |
| **Combinado** | 41.2% | 23.3% | 35.5% | +0.437 pts |

**Observação:** Home advantage maior em 2025 (pode refletir efeito calendário ou agenda das séries)

---

## Métricas Ofensivas e Defensivas

### xG Produzido (Home)
| Temporada | Média | Std |
|---|---|---|
| 2025 | 1.536 xG | 1.019 |
| 2026 | 1.520 xG | 1.156 |

**Comparação:** Produção ofensiva estável entre temporadas

### Eficiência Ofensiva
- **2025:** 0.96 gols/match vs 1.54 xG → *subperformance*
- **2026:** 1.30 gols/match vs 1.52 xG → *eficiência alinhada*

**Inferência:** 2026 mostra melhor conversão; 2025 teve sorte adversa no começo (R1).

---

## Features Engineered — Performance por Grupo

### Grupo A: Diferenciais (Home − Away)
| Feature | r_combinado | Significância |
|---|---|---|
| xg_diff | +0.416 | ** |
| sot_diff | +0.357 | ** |
| shots_diff | -0.006 | NS |

**Achado:** xG é predictor superior a volume de chutes brutos

### Grupo B: Eficiência
| Feature | r_combinado | Validado em |
|---|---|---|
| xg_overperformance_diff | +0.650 | 2025, 2026 |
| xg_per_shot_diff | +0.451 | 2025, 2026 |

**Achado:** Overperformance (gols - xG) é o predictor **mais forte** de resultado

### Grupo C: Domínio Territorial
| Feature | r_combinado | Significância |
|---|---|---|
| xg_tilt_h | +0.422 | ** |
| field_tilt_sot_h | +0.385 | ** |
| poss_diff | -0.330 | ** |

**Achado:** xG tilt captura domínio melhor que posse; posse negativa (visitante = mais passes) prediz derrota do mandante

### Grupo D: Pressão Progressiva (2026 only)
| Feature | r_combinado | n | Significância |
|---|---|---|---|
| prog_ratio_diff | +0.489 | 62 | ** |
| prog_ratio_h | +0.438 | 62 | ** |

**Achado:** Terceiro predictor mais forte em 2026; não testável em 2025 (dados indisponíveis)

---

## Linha de Base vs Features

| Modelo | Accuracy | Melhoria |
|---|---|---|
| Prever sempre H (baseline) | 41.2% | — |
| xg_overperformance_diff (LOO) | 60.4% | **+19.2%** |
| prog_ratio_diff (LOO, 2026 only) | 48.4% | +7.2% |
| xg_per_shot_diff (LOO) | 51.0% | +9.8% |

---

## Próximos Passos

1. **Modelagem Preditiva (Fase 2)**
   - Logistic Regression com top 5 features
   - Poisson regression para score exacto
   - Comparação com baseline Dixon-Coles

2. **Validação Prospectiva**
   - Testar em R8+ da Série B 2026 (holdout test set)
   - Medir calibração (predicted win% vs actual)

3. **Player Data para 2025**
   - Resolver timeouts Selenium (aumentar timeout, retry logic, proxy)
   - Validar prog_ratio/line_height em full 2025 (todos os 380 matches)

4. **Séries Temporais**
   - Implementar rolling features com janela de 5-10 rodadas
   - Detectar mudanças de forma pre-match

---

## Conclusão

A análise com **262 partidas** confirma que as features engineered têm **poder preditivo robusto e cross-season**. Os melhores predictores são **team-level** (xG, eficiência, domínio territorial), com forte suporte de **player-level metrics** quando disponíveis (progressive carries). O dataset está pronto para fase de modelagem.

