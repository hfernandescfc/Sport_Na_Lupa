# Série B 2025 — Advanced Statistics Extraction In Progress

**Status**: 🔄 EXTRACTING ADVANCED STATS  
**Start Time**: 2026-05-07 ~14:15  
**Expected Duration**: ~30-60 minutes (200 matches × 2 teams = 400 XHR calls)

---

## 🔄 Pipeline de Extração

### Etapa 1: Resolver Event IDs (🔄 Running)
- **Job ID**: `bs4dcj7i5`
- **Tarefa**: Selenium + XHR para extrair event_id de cada match
- **Entrada**: 200 matches (data/curated/serie_b_2025/matches_clean.csv)
- **Saída**: event_ids.json (mapping match_code → event_id)
- **Tempo estimado**: 10-15 min

### Etapa 2: Fetch Advanced Stats (⏳ Queued)
- **Parte de**: Job `bs4dcj7i5` (mesmo job)
- **Tarefa**: XHR para `/api/v1/event/{id}/statistics` por match
- **Entrada**: event_ids.json + 200 matches
- **Saída**: team_match_stats.csv (400 team-match records)
- **Stats extraídas**: expected_goals, shots, passes, tackles, fouls, corners, cards, etc.
- **Tempo estimado**: 15-30 min

### Etapa 3: Transform & Normalize (⏳ Queued)
- **Job ID**: `bsexedd9m` (aguardando bs4dcj7i5)
- **Tarefa**: Normalizar stats para curated tables
- **Entrada**: team_match_stats.csv (raw)
- **Saída**: data/curated/serie_b_2025/team_match_stats.csv (normalized)
- **Tempo estimado**: 2 min

---

## 📊 Estatísticas que Serão Extraídas

Tipicamente, SofaScore fornece:

### Ataque
- ✅ expected_goals (xG)
- ✅ shots_total, shots_on_target
- ✅ goal_assist
- ✅ expected_assists (xA)

### Posse
- ✅ passes_total, passes_accurate
- ✅ pass_accuracy_pct
- ✅ possession_pct (se disponível)

### Defesa
- ✅ tackles_total
- ✅ tackles_won
- ✅ fouls (cometidos)
- ✅ yellow_cards, red_cards

### Outras
- ✅ corners
- ✅ cross_total, cross_accurate
- ✅ ball_recovery
- ✅ clearances
- ✅ interceptions

---

## 📈 Timeline

```
14:15 — Extração iniciada
14:30 — Event IDs sendo resolvidos (~50% em 15 min)
14:50 — Event IDs completos, fetching stats iniciado
15:20 — Stats extraction completo (400 team-match records)
15:22 — Transform executado
15:25 — COMPLETO: Advanced stats normalizadas
```

---

## 🎯 Arquivos Esperados

### Raw Data
```
data/processed/2025/matches/
  ├── event_ids.json (200-400 event_ids)
  └── team_match_stats.csv (400 rows: 200 matches × 2 teams)
```

### Curated Data (após transform)
```
data/curated/serie_b_2025/
  └── team_match_stats.csv (normalized)
```

---

## 🖥️ Jobs Monitorados

| Job ID | Task | Status |
|---|---|---|
| `bs4dcj7i5` | Extract event IDs + fetch stats | 🔄 Running |
| `bsexedd9m` | Consolidate + transform | ⏳ Waiting for bs4dcj7i5 |
| `bl2e1pg7x` | Monitor progress | 🔄 Running |

---

## 💡 O Que Fazer Enquanto Aguarda

### Opção 1: Verificar Progresso
```bash
tail -f logs/advanced_stats_extraction.log
# ou
wc -l data/processed/2025/matches/team_match_stats.csv
```

### Opção 2: Preparar Features para ML
```python
# Com matches_clean.csv que já temos
import pandas as pd

df = pd.read_csv('data/curated/serie_b_2025/matches_clean.csv')

# Features que vão usar as advanced stats:
# - home_xg, away_xg (quando tiver team_match_stats)
# - home_pass_accuracy, away_pass_accuracy
# - home_possession, away_possession
# etc.
```

### Opção 3: Design Modelo
- Arquitetura (Logistic Regression, XGBoost, Neural Net)
- Features (quais stats usar)
- Target (home win / draw / away win, ou placares exatos)

---

## ⚠️ Possíveis Delays

**Problema**: Selenium timeout ou API rate limiting  
**Solução**: Script detecta e continua (fail-soft)

**Problema**: Alguns matches não têm stats no SofaScore  
**Solução**: Serão pulados, dados parciais mesmo assim

**Problema**: XHR retorna estrutura diferente  
**Solução**: Script tenta parse, ignora se falhar

---

## Próximos Passos (Após Conclusão)

1. **Verificar dados**:
   ```bash
   wc -l data/curated/serie_b_2025/team_match_stats.csv
   head data/curated/serie_b_2025/team_match_stats.csv
   ```

2. **Mesclar com matches_clean.csv**:
   ```python
   matches = pd.read_csv('data/curated/serie_b_2025/matches_clean.csv')
   stats = pd.read_csv('data/curated/serie_b_2025/team_match_stats.csv')
   
   # Mesclar por match_code
   df = matches.merge(stats, left_on='match_id', right_on='match_code')
   ```

3. **Treinar modelo com advanced stats**:
   ```python
   from sklearn.ensemble import XGBClassifier
   
   X = df[['round', 'home_xg', 'away_xg', 'home_shots', 'away_shots', ...]]
   y = df['result']  # home_win / draw / away_win
   
   model = XGBClassifier().fit(X, y)
   ```

---

## 📞 Suporte

**Dúvida**: Por quê está demorando?  
**Resposta**: ~200 XHR calls × 0.5-2 sec cada = 100-400 seg = 2-7 min para stats. + event_id resolution.

**Dúvida**: E se falhar no meio?  
**Resposta**: Script faz fail-soft (continua) — você terá dados parciais.

**Dúvida**: Como saber quando terminou?  
**Resposta**: Você será notificado! Ou monitore: `wc -l data/processed/2025/matches/team_match_stats.csv`

---

**You will be notified when extraction completes!** 🔔

*ETA: ~1 hora*
