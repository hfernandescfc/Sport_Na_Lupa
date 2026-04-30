# CLAUDE.md — SportSofa

Guia de contexto para o Claude Code. Leia antes de qualquer tarefa.

---

## Objetivo do projeto

Pipeline de dados em Python para extrair, normalizar e analisar:

1. **Todas as partidas do Sport Recife em 2026** — todas as competições disponíveis no SofaScore
2. **Todas as partidas da Série B 2026** — os 20 clubes participantes, com foco em estatísticas de time por partida
3. **Scouts individuais de jogadores** — Sport (todas as competições) + todos os clubes da Série B

Fonte de dados primária: **SofaScore** (via Selenium + Edge headless + XHR síncrono no domínio).
Fonte secundária: **CBF** (lista oficial dos 20 clubes).

---

## IDs críticos

| Entidade | ID | Observação |
|---|---|---|
| Série B 2026 — tournament | `390` | `https://www.sofascore.com/pt/football/tournament/brazil/brasileirao-serie-b/390` |
| Série B 2026 — season | `89840` | persistido em `data/raw/sofascore/competition/serie_b_2026_season_id.json` ✅ |
| Sport Recife — team | `1959` | `https://www.sofascore.com/pt/football/team/sport-recife/1959` |

---

## Decisões técnicas fixas

- **Sempre usar Edge** (`selenium.webdriver.Edge`) — não Chrome. O `network_sniffer.py` usa Chrome para captura de logs de performance; todo o restante usa Edge.
- Selenium em modo `--headless=new`. Criar um driver por operação lógica (fetch de rodada, fetch de stats), nunca reusar entre funções de alto nível.
- **XHR síncrono via `execute_script`** — NÃO usar `execute_async_script`. O SofaScore bloqueia callbacks assíncronos em headless. Padrão correto:
  ```python
  driver.execute_script("""
      var xhr = new XMLHttpRequest();
      xhr.open("GET", "/api/v1/...", false);  # false = síncrono
      xhr.send();
      return {status: xhr.status, body: xhr.responseText};
  """, arg1, arg2)
  ```
- Stats de partida: XHR síncrono → fallback DOM se falhar.
- Datas sempre em **UTC ISO 8601** com sufixo `Z` (ex: `"2026-03-21T23:30:00Z"`).
- IDs de partida: `match_code` = `customId` do SofaScore (ex: `"jOscJu"`), não o `id` numérico.
- `event_id` = ID numérico do SofaScore (ex: `15525993`).
- Scouts de jogadores: endpoint `/api/v1/event/{event_id}/lineups` — retorna todos os jogadores de ambos os times em uma única chamada.

---

## Estrutura do projeto

```
src/
  config.py                     — Settings dataclass + get_settings()
  main.py                       — CLI argparse, 9 comandos
  discover/
    network_sniffer.py          — Chrome DevTools, captura endpoints
    endpoint_registry.py        — discover_endpoints(), grava endpoint_registry.json
    team_mapper.py              — MANUAL_TEAM_MAPPINGS (20 clubes), build_team_mapping_stub()
  extract/
    cbf_competition.py          — CBF_SERIE_B_2026_CLUBS (seed), export_cbf_clubs_seed()
    sofascore_competition.py    — SÉRIE B: season_id, fetch por rodada (XHR síncrono)
    sofascore_match.py          — stats de time por partida via Selenium (XHR síncrono)
    sofascore_sport.py          — SPORT: fetch automático via /team/1959/events/ (XHR síncrono)
    sofascore_team.py           — metadados de clubes
    sofascore_player_stats.py   — scouts individuais via /event/{id}/lineups ✅
    sofascore_heatmap.py        — heatmap de posicionamento via /player/{id}/.../heatmap ✅
    sofascore_attack_map.py     — stats estendidas + shotmap por partida do adversário ✅
    sofascore_opponent.py       — extração completa de adversário: partidas + team stats + player stats ✅
    sofascore_serie_b_strength.py — valor de mercado + proxy de desempenho dos 20 clubes Série B ✅
    sofascore_logos.py          — download de escudos via Selenium XHR binary (base64) para data/cache/logos/ ✅
    sofascore_incidents.py      — extração de incidentes/gols por partida via /event/{id}/incidents ✅
    sofascore_player_heatmap_match.py — heatmap de jogador por partida específica ✅
  transform/
    matches.py                  — unifica + normaliza partidas e stats de time ✅
    players.py                  — normaliza scouts individuais ✅
    attack_map.py               — agrega extended_stats + shotmap → attack_profile.json + padrões ✅
    opponents.py                — normaliza dados do adversário: is_home_team + team_outcome ✅
    standings.py                — xPts (Poisson) + SOS + expected_points_table.csv ✅
    incidents.py                — normaliza incidentes de partida → goal_sequences.csv + match_incidents.csv ✅
    player_positions.py         — posições de jogadores na Série B → player_positions_serie_b.csv ✅
    clubs.py / events.py / lineups.py / shots.py — stubs
  validate/
    quality_checks.py           — 12 checks, gera validation_report.json
    reconciliation.py           — stub
  utils/
    http.py                     — get_json() com retry (tenacity)
    io.py                       — write_json(), write_csv(), ensure_project_structure()
    normalize.py                — normalize_team_name() + ALIASES (36 entradas)
    logging_utils.py            — configure_logging(), get_logger()

# Cards visuais (raiz do projeto)
generate_heatmap_card.py        — template genérico de mapa de calor (mplsoccer + KDE)
generate_pass_map_card.py       — template genérico de distribuição de passes por zona
generate_coach_cards.py         — cards comparativos de técnicos (dados Transfermarkt)
generate_habraao_card.py        — card de apresentação de jogador com foto + logo
generate_<adversário>_cards.py  — raio-x do adversário: 6 cards (cover, campanha, mandante, últimos5, xG, jogadores)
generate_xpts_table_card.py     — tabela xPts dos 20 clubes Série B com escudos, barras, dots SOS ✅
generate_xpts_scatter_card.py   — scatter xPts vs SOS com 4 quadrantes coloridos ✅
generate_como_joga_card.py      — card "Como Joga" do adversário: shotmap + zonas + padrões ✅
nivel_de_ataque.py              — quadro semanal "Nível de Ataque": dumbbell xG produzido vs contexto defensivo ✅
analise_ofensiva_serie_b.py     — script de análise exploratória (terminal): ranking completo + detalhe por rodada

# Curadoria de conteúdo
pending_posts/                  — posts aguardando revisão (→ posted/ ou rejected/)
  <YYYY-MM-DD_slug>/
    card.png
    tweet.txt
    metadata.json

# Skills do Claude Code
.claude/skills/
  canvas-design/SKILL.md        — criação de cards visuais
  image-enhancer/SKILL.md       — melhoria de qualidade de imagens
  twitter-algorithm-optimizer/SKILL.md — otimização para algoritmo do X
```

---

## Estado de implementação

### Completo e funcional

| Módulo | Status |
|---|---|
| Bootstrap (pastas, seeds, CLI) | ✅ |
| 20 clubes CBF + mapeamento SofaScore | ✅ |
| Resolução do `season_id` via Selenium + XHR síncrono | ✅ `season_id=89840` resolvido |
| Fetch de rodadas da Série B | ✅ XHR síncrono, `/unique-tournament/390/season/89840/events/round/{N}` |
| `sync-matches` dinâmico | ✅ rodada 1 executada — 10/10 `advanced_stats_confirmed` |
| Fetch automático de partidas do Sport | ✅ 57 partidas via API (16 concluídas) |
| `sync-sport` dinâmico | ✅ XHR síncrono, sem fallback necessário |
| Stats de time por partida (Selenium) | ✅ XHR síncrono + DOM fallback, 11 métricas |
| **Scouts individuais de jogadores** | ✅ `/event/{id}/lineups` — 1.124 linhas (365 Sport + 759 Série B) |
| **Transform — partidas + stats de time** | ✅ `transform/matches.py` — 4 CSVs curados |
| **Transform — scouts de jogadores** | ✅ `transform/players.py` — 2 CSVs curados |
| **Pipeline raio-x adversário** | ✅ extração + transform + 6 cards + thread — Vila Nova R2 concluído |
| Validação de qualidade (12 checks) | ✅ 11/11 aprovados, 1 info (cobertura incremental) |
| Normalização de nomes | ✅ |
| **Download de escudos (Selenium XHR binary)** | ✅ `sofascore_logos.py` — 20 clubes cacheados em `data/cache/logos/` |
| **Força dos adversários Série B** | ✅ `sofascore_serie_b_strength.py` — MV + proxy de desempenho |
| **Transform standings (xPts + SOS)** | ✅ `standings.py` — Poisson, SOS, KEY_ALIASES, `expected_points_table.csv` |
| **Cards xPts (tabela + scatter)** | ✅ `generate_xpts_table_card.py` + `generate_xpts_scatter_card.py` |
| **Post xPts R1-R3 Série B 2026** | ✅ `pending_posts/2026-04-08_xpts-serie-b/` — pronto para publicar |
| **Extração de incidentes por partida** | ✅ `sofascore_incidents.py` — goal_sequences + match_incidents |
| **Transform de incidentes e posições** | ✅ `incidents.py` + `player_positions.py` |
| **Quadro "Nível de Ataque"** | ✅ `nivel_de_ataque.py` — dumbbell xG produzido vs contexto defensivo, auto-rodada, tweet gerado |

### Parcial / dependente de execução

| Módulo | Status |
|---|---|
| Rodadas 2-38 da Série B | ⚠️ Implementado, aguardando ocorrência das rodadas |
| Partidas do Sport (futuras) | ⚠️ 41 partidas agendadas; API atualiza automaticamente |

### Stub / não iniciado

| Módulo | Status |
|---|---|
| Shotmap por partida (Série B completa) | ❌ |
| Snapshot de classificação (`/standings/total`) | ❌ |
| `transform/` restante (clubs, events, lineups, shots) | ❌ stubs |
| `validate/reconciliation.py` | ❌ stub |

---

## Dados disponíveis em `data/curated/`

| Arquivo | Linhas | Conteúdo |
|---|---|---|
| `serie_b_2026/matches.csv` | 40 | Partidas Série B R1-R4 com `match_label`, `team_key` normalizado |
| `serie_b_2026/team_match_stats.csv` | 80 | Stats de time + `passes_accuracy_pct`, `shots_on_target_pct` |
| `serie_b_2026/player_match_stats.csv` | ~1600 | Scouts individuais Série B R1-R4 |
| `serie_b_2026/expected_points_table.csv` | 20 | xPts, xW/D/L, pts_diff, SOS, sos_rank — R1-R4 (MP=4) |
| `serie_b_2026/goal_sequences.csv` | — | Sequências de gol com minuto, tipo, time — R1-R4 |
| `serie_b_2026/match_incidents.csv` | — | Incidentes por partida (gols, cartões, substituições) — R1-R4 |
| `sport_2026/matches.csv` | — | Todas partidas do Sport 2026 |
| `sport_2026/team_match_stats.csv` | — | Stats de time do Sport (partidas concluídas) |
| `sport_2026/player_match_stats.csv` | — | Scouts individuais do Sport (todas as competições) |
| `sport_2026/goal_sequences.csv` | — | Sequências de gol do Sport 2026 |
| `sport_2026/match_incidents.csv` | — | Incidentes das partidas do Sport 2026 |
| `sport_2026/player_positions_serie_b.csv` | — | Posições dos jogadores do Sport na Série B |
| `opponents_2026/vila-nova/matches.csv` | — | Partidas do Vila Nova 2026 com `is_home_team` + `team_outcome` |
| `opponents_2026/vila-nova/team_match_stats.csv` | — | Stats de time do Vila Nova por partida |
| `opponents_2026/vila-nova/player_match_stats.csv` | — | Scouts individuais do Vila Nova |

---

## Comandos CLI

```bash
# Primeira execução (cria pastas, seeds, mapeamento)
python -m src.main bootstrap

# Resolver season_id + seed rodada 1 da Série B
python -m src.main sync-competition --season 2026

# Buscar partidas de todas as rodadas já ocorridas
python -m src.main sync-matches --season 2026 --from-round 1 --to-round 38

# Atualizar partidas do Sport (todas as competições)
python -m src.main sync-sport --season 2026

# Buscar scouts individuais (Sport todas as comps + Série B todos os clubes)
python -m src.main sync-player-stats --season 2026

# Transformar dados processados em tabelas curadas
python -m src.main transform --season 2026

# Validar dados
python -m src.main validate --season 2026

# Baixar escudos dos 20 clubes Série B (Selenium XHR binary → data/cache/logos/)
python -m src.main sync-logos --season 2026

# Buscar valor de mercado + proxy de desempenho dos clubes Série B
python -m src.main sync-serie-b-strength --season 2026

# Gerar expected_points_table.csv (xPts Poisson + SOS)
python -m src.main transform-standings --season 2026
```

### Fluxo incremental (a cada nova rodada)

Comando único — executa extract + transform + validate + cards recorrentes (`nivel_de_ataque`, xPts table, xPts scatter):

```bash
python -m src.main update-round --season 2026
# --round N            → força rodada-alvo dos cards (default: auto-detect última completa)
# --skip-cards         → roda só pipeline de dados, pula geração de cards
# --strict             → aborta no primeiro erro (default: fail-soft, segue + log)
# --refresh-strength   → roda sync-serie-b-strength antes do transform-standings
#                        (custo Selenium ~5min). Recomendado quando MV estiver antigo
#                        ou faltar cobertura — janelas de transferência, p.ex.
```

**SOS / força do calendário:** o `transform-standings` agora calcula o `perf_score`
**ao vivo** do próprio `expected_points_table.csv` (Pts/MP da Série B), e combina
com o `mv_score` congelado do CSV de força. Em prática: PPG sempre fresco a cada
rodada; MV só atualiza com `--refresh-strength` (ou `python -m src.main sync-serie-b-strength`).

**Sequência interna** (13 passos, idempotentes):
1. extract: `sync-matches` (1-38) · `sync-sport` · `sync-player-stats` · `sync-incidents` · `sync-player-positions`
2. transform: `transform-matches` · `transform-players` · `transform-incidents` · `transform-player-positions` · `transform-standings`
3. validate: `run_quality_checks`
4. cards: `nivel_de_ataque.py --round N` · `generate_xpts_table_card.py` · `generate_xpts_scatter_card.py`

**Comandos individuais (para debug de etapa isolada):**

```bash
python -m src.main sync-matches --season 2026 --from-round N --to-round N
python -m src.main sync-sport --season 2026
python -m src.main sync-player-stats --season 2026
python -m src.main sync-incidents --season 2026
python -m src.main transform --season 2026
python -m src.main transform-incidents --season 2026
python -m src.main transform-standings --season 2026
python -m src.main validate --season 2026
```

### Fluxo Nível de Ataque (quadro semanal — a cada rodada)

```bash
# 1. Sincronizar nova rodada
python -m src.main sync-matches --season 2026 --from-round N --to-round N
python -m src.main transform --season 2026

# 2. Gerar card + tweet + metadata automaticamente
python -X utf8 nivel_de_ataque.py
# → pending_posts/{hoje}_nivel-de-ataque-r{N}/card.png + tweet.txt + metadata.json

# Forçar rodada específica (reprocessar):
python -X utf8 nivel_de_ataque.py --round N
```

**O script auto-detecta** a última rodada completa nos dados, gera o dumbbell chart com escudos,
e preenche o tweet com top-3/bottom-3 e posição do Sport calculados em tempo real.

---

### Fluxo xPts semanal (a cada bloco de rodadas)

```bash
# 1. Sincronizar rodadas novas
python -m src.main sync-matches --season 2026 --from-round N --to-round N
python -m src.main transform --season 2026

# 2. (opcional — só necessário se novos clubes entraram ou MV mudou muito)
python -m src.main sync-serie-b-strength --season 2026

# 3. Gerar tabela xPts atualizada
python -m src.main transform-standings --season 2026

# 4. Gerar cards
python generate_xpts_table_card.py
python generate_xpts_scatter_card.py
```

### Fluxo raio-x do próximo adversário

```bash
# 1. Extrair dados do adversário
python -m src.main sync-opponent --team-key <key> --team-id <id> --season 2026

# 2. Normalizar em tabelas curadas
python -m src.main transform-opponent --team-key <key> --season 2026

# 3. Gerar cards visuais (criar script generate_<key>_cards.py baseado em generate_vila_nova_cards.py)
python generate_<key>_cards.py

# Exemplo — Vila Nova (R2):
python -m src.main sync-opponent --team-key vila-nova --team-id 2021 --season 2026
python -m src.main transform-opponent --team-key vila-nova --season 2026
python generate_vila_nova_cards.py
```

---

## Convenções de campos

### Status de partida (`status`)
- `"completed"` — partida encerrada
- `"in_progress"` — em andamento
- `"scheduled"` — agendada
- `"postponed"` / `"canceled"`

### Status de dados (`data_status`)
- `"score_confirmed"` — placar confirmado
- `"advanced_stats_confirmed"` — todas as 7 métricas obrigatórias presentes
- `"advanced_stats_partial"` — ao menos 1 métrica presente
- `"advanced_stats_missing"` — nenhuma métrica
- `"fixture_only"` / `"scheduled"` — sem resultado ainda

### Métricas obrigatórias de time (`REQUIRED_ADVANCED_FIELDS`)
`expected_goals`, `shots_total`, `corners`, `fouls`, `passes_total`, `tackles_total`, `yellow_cards`

### Métricas de scout individual (`PLAYER_STAT_FIELDS`)
`minutes_played`, `rating`, `total_pass`, `accurate_pass`, `total_long_balls`, `accurate_long_balls`,
`total_shots`, `goal_assist`, `saves`, `touches`, `possession_lost_ctrl`, `ball_recovery`,
`expected_assists`, `pass_value_normalized`, `dribble_value_normalized`,
`defensive_value_normalized`, `goalkeeper_value_normalized`

### Resultado do Sport (`sport_outcome`)
`"win"` / `"loss"` / `"draw"` — calculado automaticamente por `_determine_sport_outcome()`

---

## Regras de desenvolvimento

- **Não usar Chrome** fora do `network_sniffer.py`. Todo Selenium novo usa Edge.
- **Nunca usar `execute_async_script`** — SofaScore bloqueia em headless. Sempre XHR síncrono via `execute_script`.
- **Não reescrever os seeds** (`ROUND_1_MATCHES`, `SPORT_2026_MATCH_SEED`, etc.) — são fallback e registro histórico.
- **Não remover `SPORT_2026_RESULT_SEED`** — ainda usado como fallback quando a API não retorna scores.
- Seeds são dados de bootstrapping, não fonte de verdade. A API do SofaScore é a fonte autoritativa.
- Funções de extração devem sempre ter: `try/except` no import do Selenium, `finally: driver.quit()`, log de warning em caso de falha (nunca raise).
- `write_json()` e `write_csv()` já criam diretórios — não chamar `mkdir` manualmente antes.
- Timestamp de auditoria: `datetime.datetime.utcnow().isoformat() + "Z"`.
- `write_csv()` usa pandas internamente — não aceita parâmetro `fieldnames`.

---

## Análise de próximo adversário

Pipeline para geração de posts sobre o próximo adversário do Sport.

### Módulos

| Módulo | Descrição |
|---|---|
| `src/extract/sofascore_opponent.py` | Extração completa de um adversário: partidas + stats de time + scouts individuais |
| `src/transform/opponents.py` | Normaliza dados processados em tabelas curadas |

### Comandos

```bash
# Extrair todos os dados do adversário (partidas + stats de time + player stats)
python -m src.main sync-opponent --team-key vila-nova --team-id 2021 --season 2026

# Normalizar em tabelas curadas
python -m src.main transform-opponent --team-key vila-nova --season 2026
```

### Estrutura de saída

```
data/processed/2026/opponents/vila-nova/
  matches.csv           — todas as partidas do adversário em 2026 (todas as competições)
  team_match_stats.csv  — stats de time (ambos os times) por partida concluída
  player_match_stats.csv — scouts individuais (ambos os times) por partida concluída

data/curated/opponents_2026/vila-nova/
  matches.csv           — partidas enriquecidas com team_outcome + is_home_team
  team_match_stats.csv  — idem ao processed (passthrough)
  player_match_stats.csv — idem ao processed (passthrough)
```

### IDs de adversários confirmados

| Time | team_key | team_id | Rodada | Status |
|---|---|---|---|---|
| Vila Nova | `vila-nova` | `2021` | R2 | ✅ cards + thread gerados |
| Avaí | `avai` | `7315` | R4 | 🔜 próximo (11/04/2026) |

### Fluxo raio-x completo (com card "Como Joga")

```bash
# 1. Extrair partidas + stats de time + player stats
python -m src.main sync-opponent --team-key avai --team-id 7315 --season 2026

# 2. Normalizar partidas
python -m src.main transform-opponent --team-key avai --season 2026

# 3. Extrair estatísticas estendidas + shotmap (NOVO)
python -m src.main sync-attack-map --team-key avai --season 2026

# 4. Agregar + detectar padrões (NOVO)
python -m src.main transform-attack-map --team-key avai --season 2026

# 5. Gerar os 6 cards principais (baseado em generate_vila_nova_cards.py)
python generate_avai_cards.py

# 6. Gerar card "Como Joga" (NOVO — card 07)
python generate_como_joga_card.py \
  --team-key avai --team-name "AVAÍ FC" \
  --team-id 7315 --round 4 --date 2026-04-11 --season 2026
```

---

## Pipeline de narrativas (`src/narrativa/`)

Análise de propagação de ideias no X — detecta se uma narrativa é orgânica ou impulsionada.

### Módulos

| Módulo | Descrição |
|---|---|
| `collect.py` | Coleta via snscrape / ntscraper / mock |
| `preprocess.py` | Limpeza de texto, tokenização, stopwords PT |
| `identify.py` | Filtro por palavras-chave + similaridade semântica |
| `timeline.py` | Série temporal, picos (Z-score burst detection) |
| `origin.py` | Análise dos primeiros N tweets, métricas de usuário |
| `diffusion.py` | Gini, concentração, velocidade de propagação |
| `classify.py` | Heurística: Orgânico / Impulsionado / Misto |
| `cluster.py` | (Extra) K-Means de sub-narrativas via embeddings |
| `visualize.py` | Dashboard (série temporal + engajamento + top users) |
| `report.py` | Resumo técnico + thread para o X + pending_post |
| `pipeline.py` | Orquestração completa das etapas |

### Comandos

```bash
# Desenvolvimento local (dados mock, sem dependências externas)
PYTHONUTF8=1 python run_narrativa.py --mock --exemplo sem_vontade

# Outros exemplos pré-configurados
PYTHONUTF8=1 python run_narrativa.py --mock --exemplo critica_tecnico
PYTHONUTF8=1 python run_narrativa.py --mock --exemplo elenco_fraco

# Tema customizado com palavras-chave
PYTHONUTF8=1 python run_narrativa.py \
  --mock \
  --tema "crítica ao goleiro" \
  --kw "goleiro" "falha" "horrível" "substituir"

# Com análise semântica (requer: pip install sentence-transformers)
PYTHONUTF8=1 python run_narrativa.py --mock --semantica \
  --tema "time sem vontade" \
  --frase "elenco apagado jogando sem vontade"

# Com snscrape/ntscraper (podem falhar por restrições da API do X)
PYTHONUTF8=1 python run_narrativa.py \
  --tema "Sport Recife" \
  --query "Sport Recife treinador ruim" \
  --kw "ruim" "péssimo" "demitir" \
  --desde 2026-04-01 --max 500

# Ver todos os parâmetros
python run_narrativa.py --help
```

### Output gerado

```
pending_posts/<YYYY-MM-DD_slug>/
  dashboard.png    — 3 gráficos (série temporal + engajamento + top users)
  tweet.txt        — thread pronta para o X (4 tweets)
  resumo.txt       — relatório técnico completo
  metadata.json    — classificação + score + confiança

data/processed/narrativas/
  <YYYY-MM-DD_slug>.csv  — DataFrame completo com todas as métricas
```

### Dependências opcionais

```bash
pip install sentence-transformers   # análise semântica + clustering
pip install networkx                # grafo de propagação (--grafo)
pip install ntscraper               # coleta real sem API paga (alternativa ao snscrape)
```

---

## Próximas prioridades

1. Publicar "Nível de Ataque R1-R4" (`pending_posts/2026-04-16_nivel-de-ataque-r4/`)
2. Executar pipeline raio-x para o próximo adversário do Sport (R5+)
3. Atualizar xPts para R1-R4 e publicar (`generate_xpts_table_card.py` + `generate_xpts_scatter_card.py`)
4. Implementar snapshot de classificação (`/api/v1/unique-tournament/390/season/89840/standings/total`)
5. Integrar X API via MCP para postagem direta a partir da pasta `pending_posts/`

---

## Arquivos de referência

| Arquivo | Conteúdo |
|---|---|
| `SERIE_B_2026_EXTRACTION_PLAN.md` | Plano técnico completo: modelo de dados, fases, riscos |
| `data/raw/sofascore/competition/serie_b_2026_season_id.json` | `season_id=89840` resolvido ✅ |
| `data/curated/serie_b_2026/validation_report.json` | Resultado dos 12 checks de qualidade |
| `data/curated/sport_2026/player_match_stats.csv` | Scouts individuais do Sport 2026 |
| `data/curated/serie_b_2026/player_match_stats.csv` | Scouts Série B R1 (todos os clubes) |
| `gustavo_maia_card_v4.png` | Card visual do Gustavo Maia (referência de estilo) |
| `habraao_sofascore_stats.json` | Stats do Habraão em todos os torneios/temporadas |
| `habraao_heatmap_serie_b_2025.json` | Heatmap de posicionamento — Série B 2025 (855 pts) |
| `habraao_heatmap_per_match.json` | Heatmap agregado por partida — Série B 2025 (1018 pts) |
| `card_habraao_v2.png` | Card de apresentação do Habraão |
| `card_habraao_heatmap.png` | Card de mapa de calor do Habraão |
| `card_habraao_passes.png` | Card de distribuição de passes por zona do Habraão |
| `card_tencati.png` / `card_baptista.png` / `card_luizinho.png` | Cards comparativos de técnicos |
| `generate_vila_nova_cards.py` | Raio-X R2 — template de referência para próximos adversários |
| `generate_xpts_table_card.py` | Card 01 xPts — tabela 20 times com escudos, barras, dots SOS |
| `generate_xpts_scatter_card.py` | Card 02 xPts — scatter xPts vs SOS, 4 quadrantes |
| `nivel_de_ataque.py` | Quadro recorrente — dumbbell xG produzido vs contexto defensivo; auto-detecta rodada; gera card + tweet + metadata |
| `analise_ofensiva_serie_b.py` | Análise exploratória em terminal — ranking completo + detalhe por partida por rodada |
| `data/cache/logos/` | Escudos dos 20 clubes Série B (PNG, fundo removido via BFS) |
| `data/processed/2026/matches/serie_b_2026_team_strength.csv` | MV + proxy de desempenho dos 20 clubes |
| `pending_posts/2026-04-01_raio-x-vila-nova/` | Thread R2 (Vila Nova): 6 cards + tweet.txt + metadata.json |
| `pending_posts/2026-04-08_xpts-serie-b/` | Thread xPts R1-R3: 2 cards + tweet.txt + metadata.json — pronto |

---

## Contexto @SportRecifeLab

Página de análise de dados do Sport Recife criada em paralelo ao pipeline.

- **Handle:** `@SportRecifeLab`
- **Bio:** *O Leão analisado dado por dado. Scouts, métricas e contexto para entender o Sport além do placar.*
- **Paleta visual:** fundo `#0d0d0d`, amarelo ouro `#F5C400`, campo `#0e3d1f` / `#2a7a3a`
- **Fonte:** Franklin Gothic Heavy (títulos) + Arial (subtítulos)
- **Logo:** `sportrecifelab_avatar.png` (400×400) — sempre no footer, posição `(0.09, 0.028)` figura

### Criação de cards visuais

**Sempre usar a skill `canvas-design`** ao criar ou modificar qualquer card visual — seja um novo `generate_*.py`, seja ajuste de layout, paleta, tipografia ou composição de elementos existentes.

A skill deve ser invocada antes de escrever código de card, para alinhar as decisões de design com os padrões visuais do @SportRecifeLab.

### Tipos de card produzidos

| Tipo | Template | Gatilho |
|---|---|---|
| Apresentação de jogador | `generate_habraao_card.py` (adaptar) | Contratação / destaque pontual |
| Mapa de calor | `generate_heatmap_card.py` | Análise de posicionamento |
| Distribuição de passes | `generate_pass_map_card.py` | Lupa em jogador específico |
| Card de técnico | `generate_coach_cards.py` | Especulações / mudança de treinador |
| Raio-X do adversário | `generate_<adversário>_cards.py` | Antes de cada rodada da Série B |
| xPts semanal (tabela) | `generate_xpts_table_card.py` | A cada bloco de rodadas da Série B |
| xPts semanal (scatter) | `generate_xpts_scatter_card.py` | A cada bloco de rodadas da Série B |
| **Nível de Ataque** (quadro recorrente) | `nivel_de_ataque.py` | Após cada rodada — dumbbell xG produzido vs contexto defensivo dos 20 clubes |

### Cards do raio-x (6 cards por adversário)

| # | Nome | Conteúdo |
|---|---|---|
| 01 | `cover` | Escudo do adversário com fundo transparente (BFS flood fill) + "RAIO-X" |
| 02 | `campanha` | Campanha geral: P/V/E/D, gols, xG, posse |
| 03 | `mandante_vis` | Stats como **mandante** ou **visitante** (conforme contexto da partida) |
| 04 | `ultimos5` | Forma recente: últimas 5 partidas com placares |
| 05 | `xg` | Análise xG: gols esperados vs reais, eficiência |
| 06 | `jogadores` | Destaque individual: artilheiro, assistências, melhor rating |

### Download de escudos (logos)

SofaScore CDN (`api.sofascore.app/api/v1/team/{id}/image`) bloqueia `urllib` com 403. Solução: Selenium + XHR binary com `overrideMimeType` e `btoa`:

```javascript
xhr.overrideMimeType("text/plain; charset=x-user-defined");
// após xhr.send(): retorna btoa(responseText) como string base64
```

Python: `base64.b64decode(b64_str)` → salva PNG em `data/cache/logos/{team_id}.png`.

Card generators leem **somente do cache local** — nunca fazem download em tempo de execução.

### Remoção de fundo de escudos (logos)

Sempre usar BFS flood fill (não threshold global) para preservar branco interior:

```python
def _remove_bg_floodfill(img, thresh=25):
    # Seeds nos 4 bordas da imagem; apenas pixels brancos conectados ao exterior
    # são removidos — branco interno (escudo, textos, estrelas) é preservado
    ...
```

Referência de implementação: `generate_vila_nova_cards.py` e `generate_xpts_table_card.py`.

### Cards xPts — parâmetros visuais

| Card | figsize | DPI | Resolução |
|---|---|---|---|
| `01_xpts_table.png` | 10 × 9.5 | 120 | 1200 × 1140 px |
| `02_xpts_scatter.png` | 11 × 7.5 | 120 | 1320 × 900 px |

**Tabela (card 01)**:
- Colunas: rank, escudo (24px zoom 0.70), time, barra xPts, xPts, Pts, Δ, SOS dots (5 níveis)
- Dots SOS: sos_rank 1-4 → 5 bolinhas vermelhas; 17-20 → 1 bolinha verde
- Sport: `FancyBboxPatch` amarelo alpha=0.07 + borda amarela
- Fallback sem logo: círculo com iniciais do time

**Scatter (card 02)**:
- X: SOS (0=fácil, 1=difícil); Y: xPts acumulados
- Cor dos pontos: `pts_diff` via colormap RED→GRAY→GREEN, `TwoSlopeNorm(vmin=-3, vcenter=0, vmax=3)`
- Quadrantes: RED alpha=0.12 (fácil+baixo), GREEN alpha=0.10 (difícil+alto), GRAY alpha=0.06
- Sport: anel amarelo (s=560) + OffsetImage logo 44px zoom=1.0 + annotation amarela

### Workflow de curadoria

Posts gerados ficam em `pending_posts/<YYYY-MM-DD_slug>/` com `card.png`, `tweet.txt` e `metadata.json`.
Após revisão: mover para `posted/` (com data de publicação em metadata) ou `rejected/`.

### Geração de tweets

**Sempre usar a skill `twitter-algorithm-optimizer`** ao redigir ou revisar o `tweet.txt` de qualquer post.

Restrições obrigatórias:
- **Limite de 280 caracteres por tweet** (conta free do X — não há acesso a Twitter Blue / X Premium)
- Cada tweet da thread deve ser contado individualmente — imagens e links encurtados consomem ~23 caracteres
- Incluir contagem de caracteres real em cada tweet do arquivo `tweet.txt` (ex: `[1/4 — card: 01.png — 247 chars]`)
- Não ultrapassar 280 chars em nenhum tweet, incluindo hashtags e menções do rodapé

### IDs SofaScore relevantes

| Jogador | player_id | tournament_id | season_id |
|---|---|---|---|
| Habraão | `1142185` | `390` (Série B) | `63814` (2025) |
