# Plano Tecnico Executavel - Extracao de Dados da Serie B 2026

## 1. Objetivo

Construir uma pipeline em Python para extrair, normalizar e armazenar:

- todas as partidas do Sport Recife em 2026 em todas as competicoes disponiveis no SofaScore
- dados dos demais clubes da Serie B apenas no contexto da Serie B 2026

A abordagem tecnica continua baseada no video: abrir paginas com Selenium, capturar requisicoes de rede do navegador e consumir os JSONs internos retornados pelos endpoints do site.

## 2. Escopo da Entrega

### Entrega minima

- Cadastro dos 20 clubes participantes da Serie B 2026
- Mapeamento `clube -> sofascore_team_id`
- Calendario da Serie B 2026
- Todas as partidas do Sport Recife em 2026, em todas as competicoes
- Dados basicos de cada partida
- Estatisticas de time por partida no recorte correto

### Entrega recomendada

- Eventos detalhados por partida
- Shotmap por partida
- Escalacoes
- Tecnicos
- Snapshot da classificacao ao longo da competicao

## 3. Fonte Mestra dos Clubes

Usar a pagina oficial da CBF como referencia para os participantes da competicao. Em 23/03/2026, os clubes listados sao:

- America-MG
- Athletic Club
- Atletico-GO
- Avai
- Botafogo-SP
- Ceara
- CRB
- Criciuma
- Cuiaba
- Fortaleza
- Goias
- Gremio Novorizontino
- Juventude
- Londrina
- Nautico
- Operario-PR
- Ponte Preta
- Sao Bernardo
- Sport
- Vila Nova

Fonte: https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-b/2026

## 4. Arquitetura da Solucao

### Componentes

1. `discover`
- Descobre endpoints e identifica IDs do SofaScore.

2. `extract`
- Coleta JSONs de competicao, clubes e partidas.

3. `transform`
- Normaliza payloads heterogeneos em tabelas consistentes.

4. `validate`
- Executa checks de cobertura, duplicidade e integridade.

5. `load`
- Salva datasets em `csv`, `parquet` ou SQLite.

### Estrategia tecnica

- Selenium para abrir paginas e capturar trafego de rede.
- Chrome DevTools Protocol para ler o corpo das respostas.
- `requests` para consumo direto dos endpoints, apos descoberta.
- `pandas` para transformacao.
- `pydantic` opcional para validacao de schema.
- `tenacity` ou retry manual para tolerancia a falhas.

## 5. Estrutura de Pastas

```text
SportSofa/
  README.md
  requirements.txt
  .env.example
  data/
    raw/
      cbf/
      sofascore/
        competition/
        teams/
        matches/
    processed/
      2026/
        clubs/
        matches/
        events/
    curated/
      serie_b_2026/
  logs/
  notebooks/
  src/
    config.py
    main.py
    utils/
      http.py
      io.py
      logging_utils.py
      normalize.py
    discover/
      network_sniffer.py
      endpoint_registry.py
      team_mapper.py
    extract/
      cbf_competition.py
      sofascore_competition.py
      sofascore_team.py
      sofascore_match.py
    transform/
      clubs.py
      matches.py
      lineups.py
      players.py
      events.py
      shots.py
      standings.py
    validate/
      quality_checks.py
      reconciliation.py
  tests/
    test_normalize_names.py
    test_team_mapper.py
    test_match_schema.py
```

## 6. Modelo de Dados

### 6.1 `clubs`

Uma linha por clube.

Campos recomendados:

- `season`
- `competition`
- `cbf_name`
- `canonical_name`
- `sofascore_team_id`
- `sofascore_slug`
- `country`
- `state`
- `city`
- `venue_name`
- `venue_capacity`
- `coach_name`
- `founded_year`
- `source_url`
- `ingested_at`

### 6.2 `players`

Uma linha por jogador no contexto do clube/temporada.

- `season`
- `competition`
- `team_id`
- `player_id`
- `player_name`
- `short_name`
- `position`
- `shirt_number`
- `date_of_birth`
- `preferred_foot`
- `height_cm`
- `nationality`
- `market_status`
- `source_url`
- `ingested_at`

### 6.3 `matches`

Uma linha por partida.

- `season`
- `competition`
- `match_id`
- `round`
- `match_date_utc`
- `home_team_id`
- `away_team_id`
- `home_team_name`
- `away_team_name`
- `home_score`
- `away_score`
- `status`
- `venue_name`
- `referee_name`
- `source_url`
- `ingested_at`

### 6.4 `team_match_stats`

Uma linha por time por partida.

- `season`
- `competition`
- `match_id`
- `team_id`
- `is_home`
- `possession`
- `shots_total`
- `shots_on_target`
- `shots_off_target`
- `big_chances`
- `corners`
- `offsides`
- `fouls`
- `yellow_cards`
- `red_cards`
- `passes_total`
- `passes_accurate`
- `expected_goals`
- `expected_goals_on_target`
- `ingested_at`

### 6.5 `lineups`

Uma linha por jogador escalado por partida.

- `season`
- `competition`
- `match_id`
- `team_id`
- `player_id`
- `player_name`
- `starter`
- `position`
- `shirt_number`
- `minutes_played`
- `sub_in_minute`
- `sub_out_minute`
- `rating`
- `ingested_at`

### 6.6 `events`

Uma linha por evento.

- `season`
- `competition`
- `match_id`
- `event_id`
- `team_id`
- `player_id`
- `event_type`
- `minute`
- `added_time`
- `period`
- `outcome`
- `x`
- `y`
- `extra_json`
- `ingested_at`

### 6.7 `shots`

Uma linha por finalizacao.

- `season`
- `competition`
- `match_id`
- `shot_id`
- `team_id`
- `player_id`
- `minute`
- `added_time`
- `situation`
- `shot_type`
- `body_part`
- `xg`
- `xgot`
- `is_goal`
- `x`
- `y`
- `goalmouth_x`
- `goalmouth_y`
- `goalmouth_z`
- `ingested_at`

### 6.8 `standings_snapshots`

Uma linha por clube por momento de coleta.

- `season`
- `competition`
- `snapshot_at`
- `round`
- `team_id`
- `position`
- `points`
- `matches_played`
- `wins`
- `draws`
- `losses`
- `goals_for`
- `goals_against`
- `goal_diff`

## 7. Ordem de Implementacao

### Fase 1 - Bootstrap do projeto

Objetivo: deixar a base pronta para desenvolvimento.

Tarefas:

1. Criar estrutura de pastas.
2. Criar `requirements.txt`.
3. Configurar `logging`.
4. Criar `config.py` para paths, timeouts e user-agent.
5. Criar `.env.example` com configuracoes basicas.

Dependencias recomendadas:

```text
pandas
requests
selenium
webdriver-manager
python-dotenv
tenacity
pyarrow
pydantic
pytest
```

### Fase 2 - Cadastro dos clubes e mapeamento para SofaScore

Objetivo: garantir o relacionamento entre nomes oficiais e IDs internos.

Tarefas:

1. Extrair os 20 clubes da pagina da CBF.
2. Implementar normalizacao de nomes:
- remover acentos
- padronizar `SAF`
- padronizar siglas estaduais
- resolver aliases
3. Encontrar a pagina de cada clube no SofaScore.
4. Salvar tabela `club_mapping`.

Saida esperada:

- `data/processed/2026/clubs/club_mapping.csv`

Schema minimo:

- `cbf_name`
- `canonical_name`
- `sofascore_team_id`
- `sofascore_slug`
- `sofascore_url`
- `mapping_status`
- `mapping_notes`

### Fase 3 - Descoberta de endpoints

Objetivo: listar e classificar os endpoints JSON uteis.

Tarefas:

1. Abrir uma pagina de competicao, uma de time e uma de partida no Chrome com logs de performance.
2. Filtrar requests contendo `/api/v1/`.
3. Registrar:
- path
- tipo de entidade
- pagina de origem
- parametros necessarios
4. Testar se o endpoint responde via `requests` sem browser.
5. Criar um `endpoint_registry.json`.

Saida esperada:

- `data/raw/sofascore/endpoint_registry.json`

Campos do registro:

- `name`
- `url_pattern`
- `entity_type`
- `method`
- `requires_browser`
- `notes`

### Fase 4 - Extracao da competicao

Objetivo: obter a estrutura da Serie B 2026 para os 20 clubes.

Tarefas:

1. Descobrir `tournament_id` e `season_id` da Serie B 2026.
2. Extrair tabela/classificacao.
3. Extrair calendario completo.
4. Gerar lista canonica de `match_id`.

Saidas:

- `competition_metadata.json`
- `standings_raw.json`
- `matches_raw.json`
- `match_ids.csv`

### Fase 5 - Extracao por clube

Objetivo: enriquecer cadastro dos 20 clubes da Serie B e abrir uma trilha separada para o Sport.

Tarefas:

1. Extrair metadados do clube.
2. Extrair elenco.
3. Extrair tecnico atual, se disponivel.
4. Conciliar jogadores duplicados por transliteracao ou nome curto.

Saidas:

- `clubs.csv`
- `players.csv`
- `sport_2026_competitions.csv`
- `sport_2026_matches.csv`

### Fase 6 - Extracao por partida

Objetivo: formar duas bases principais:

- Sport Recife em todas as competicoes de 2026
- Serie B 2026 para todos os clubes

Tarefas:

1. Para cada `match_id`, baixar payload bruto.
2. Extrair informacoes gerais da partida.
3. Extrair estatisticas de time.
4. Extrair lineups.
5. Extrair eventos.
6. Extrair shotmap.

Saidas:

- `matches.csv`
- `team_match_stats.csv`
- `lineups.csv`
- `events.csv`
- `shots.csv`

### Fase 7 - Transformacao e padronizacao

Objetivo: deixar os dados prontos para uso analitico.

Tarefas:

1. Converter datas para UTC ISO 8601.
2. Padronizar nomes de colunas em `snake_case`.
3. Garantir IDs como string ou inteiro de forma consistente.
4. Armazenar campos nao modelados em `extra_json`.
5. Exportar `csv` e `parquet`.

### Fase 8 - Validacao e reconciliacao

Objetivo: garantir confiabilidade do dataset.

Checks obrigatorios:

1. Existem 20 clubes unicos.
2. Todo clube possui `sofascore_team_id`.
3. Nao ha `match_id` duplicado.
4. Toda partida tem exatamente 2 times.
5. Todo `home_team_id` e `away_team_id` existe em `clubs`.
6. As 38 rodadas estao cobertas.
7. `home_score` e `away_score` batem com eventos de gol quando houver eventos completos.
8. O total de pontos da classificacao e compativel com os resultados.

Saida:

- `validation_report.json`
- `validation_summary.md`

### Fase 9 - Operacao recorrente

Objetivo: manter a base atualizada durante a competicao.

Janelas recomendadas:

- carga inicial antes da 1a rodada
- coleta diaria do calendario e classificacao
- coleta apos cada rodada para resultados e estatisticas
- reprocessamento de partidas das ultimas 72 horas para corrigir ajustes tardios

## 8. Fluxo de Execucao

### Modo bootstrap

```bash
python -m src.main bootstrap
```

Cria pastas, arquivos base e configuracoes.

### Modo discover

```bash
python -m src.main discover-endpoints
```

Captura requests de rede e atualiza o registro de endpoints.

### Modo sync competition

```bash
python -m src.main sync-competition --season 2026
```

Baixa tabela, calendario e metadados da competicao.

### Modo sync teams

```bash
python -m src.main sync-teams --season 2026
```

Atualiza metadados e elenco dos clubes.

### Modo sync matches

```bash
python -m src.main sync-matches --season 2026 --from-round 1 --to-round 38
```

Atualiza partidas e artefatos derivados.

### Modo validate

```bash
python -m src.main validate --season 2026
```

## 9. Regras de Implementacao

### Normalizacao de nomes

Criar uma funcao central:

```python
normalize_team_name(name: str) -> str
```

Responsabilidades:

- remover acentos
- converter para minusculas
- remover sufixos irrelevantes
- resolver casos como:
  - `Botafogo` -> `botafogo-sp` quando o contexto for Serie B 2026
  - `Sport Recife` -> `sport`
  - `Atletico Goianiense Saf` -> `atletico-go`
  - `Gremio Novorizontino - Saf` -> `novorizontino`
  - `Operario` -> `operario-pr`

### Persistencia

Preferencia:

1. `raw json`
2. `processed parquet`
3. `curated csv`

Motivo:

- `raw` preserva a fonte original
- `parquet` melhora custo de leitura e processamento
- `csv` facilita auditoria e compartilhamento

### Logs

Cada execucao deve registrar:

- inicio e fim
- total de entidades processadas
- falhas por entidade
- endpoints acionados
- tempo medio por requisicao

## 10. Riscos e Mitigacoes

### Mudanca de endpoint

Risco:
- o SofaScore muda paths ou estrutura do JSON.

Mitigacao:
- manter `endpoint_registry`
- isolar parse por endpoint
- adicionar fallback para Selenium quando `requests` falhar

### Limitacao por volume

Risco:
- excesso de requests pode bloquear ou degradar a coleta.

Mitigacao:
- rate limit
- retries exponenciais
- cache local de respostas

### Ambiguidade de nomes

Risco:
- time errado no mapeamento.

Mitigacao:
- tabela manual de aliases
- validacao por cidade, estadio ou escudo

### Incompletude de dados por partida

Risco:
- algumas partidas podem nao ter todos os eventos disponiveis.

Mitigacao:
- marcar `coverage_status`
- nao quebrar pipeline por ausencia de subpayload

## 11. Cronograma Sugerido

### Sprint 1

- bootstrap do projeto
- extracao da lista de clubes da CBF
- mapeamento `clube -> team_id`
- descoberta inicial dos endpoints

### Sprint 2

- extracao da competicao
- geracao de `match_ids`
- extracao de metadados de clubes e elenco

### Sprint 3

- extracao por partida
- transformacao para tabelas
- validacoes principais

### Sprint 4

- automacao recorrente
- endurecimento contra falhas
- documentacao final

## 12. Definicao de Pronto

O projeto sera considerado pronto quando:

1. Os 20 clubes da Serie B 2026 estiverem mapeados com `sofascore_team_id`.
2. Todas as partidas da competicao estiverem presentes em `matches`.
3. Cada partida tiver, no minimo, placar, data, mandante, visitante e status.
4. Os arquivos `clubs`, `players`, `matches` e `team_match_stats` estiverem gerados.
5. As validacoes obrigatorias passarem.
6. Houver um comando unico reproduzivel para atualizar os dados.

## 13. Proximo Passo Recomendado

Implementar nesta ordem:

1. `requirements.txt`
2. estrutura `src/`
3. `normalize_team_name`
4. scraper da pagina da CBF
5. mapeador de clubes no SofaScore
6. descoberta automatizada de endpoints
7. extracao da competicao
