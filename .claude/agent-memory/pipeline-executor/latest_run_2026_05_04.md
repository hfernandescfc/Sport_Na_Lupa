---
name: Latest Pipeline Run (2026-05-04)
description: update-round completado com 6 rodadas de Série B (R1-R6), 3 cards visuais gerados
type: project
---

## Execução de 2026-05-04

**Data/Hora:** 09:43:46 a 10:03:00 UTC (~20 minutos total)

### Estado Final

**Séries B 2026:**
- 380 partidas distribuídas em 38 rodadas
- 60 partidas completadas (R1-R6 = 100% cobertura)
- 138 rows de team_match_stats
- 2.824 rows de player_match_stats (196 jogadores únicos)
- Validação: 12/12 checks ✓

**Sport Recife 2026:**
- 58 partidas totais
- 26 completadas
- 52 rows de team stats
- 590 rows de scouts individuais

**Cards Gerados:**
1. Nível de Ataque R7 (dumbbell xG) → `/pending_posts/2026-05-04_nivel-de-ataque-r7/`
2. xPts Tabela (20 clubes) → `/pending_posts/2026-05-04_xpts-serie-b/01_xpts_table.png`
3. xPts Scatter (4 quadrantes) → `/pending_posts/2026-05-04_xpts-serie-b/02_xpts_scatter.png`

### Problemas Reportados

1. **Avaí x Grêmio Novorizontino (R37)** — advanced_stats_missing
   - Causa: Selenium crash durante XHR de stats
   - Impacto: Menor (partida futura, não afeta R1-R6)

2. **Timeout Selenium em 1 event_id** — Sport Recife
   - Causa: Timeout de 30s durante extração de incidentes
   - Modo: fail-soft (continuou com próximas partidas)
   - Impacto: Menor (incidentes são complementares)

### Próximas Ações

1. Publicar os 3 cards em /pending_posts/
2. Aguardar R7 completar (2-3 semanas) — re-executar update-round
3. Para próximo adversário: usar fluxo sync-opponent + transform-opponent + generate_<key>_cards.py

**Última Rodada Completa:** R6 (60/60 partidas)  
**Status:** PRONTO PARA PUBLICAÇÃO
