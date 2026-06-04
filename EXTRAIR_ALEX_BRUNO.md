# Extrair Estatísticas de Alex Bruno (ASA-AL)

## Passo 1: Encontrar o ID do Jogador no SofaScore

### Opção A: Manual (Recomendado)

1. Abra o navegador e acesse:
   ```
   https://www.sofascore.com/search?q=alex+bruno
   ```

2. Procure por "Alex Bruno" da equipe **ASA-AL** ou **ASA** (Associação Atlética Social)

3. Clique no perfil dele - a URL será algo como:
   ```
   https://www.sofascore.com/pt/player/alex-bruno/2315723
   ```
   O número final (`2315723`) é o **PLAYER_ID**

4. Anote esse número

### Opção B: Verificar DevTools (Network)

1. Abra a página de busca acima
2. Pressione `F12` para abrir o DevTools
3. Vá para a aba **Network**
4. Procure por requisições para `/api/v1/...player`
5. Procure pelo ID do Alex Bruno nos payloads

---

## Passo 2: Executar a Extração

Abra um terminal na pasta `SportSofa` e execute:

```bash
python extract_alex_bruno.py --player-id [SEU_ID_AQUI]
```

**Exemplo:**
```bash
python extract_alex_bruno.py --player-id 2315723
```

---

## Passo 3: Acessar os Dados Extraídos

Os dados serão salvos em:
```
data/processed/2026/players/alex_bruno/
```

### Arquivos gerados:

1. **`player_info.json`** — Informações básicas do jogador
   - Nome, posição, altura, peso, data de nascimento
   - Time atual e história de clubes

2. **`career_statistics.json`** — Estatísticas detalhadas por torneio/temporada
   - Todos os torneios que disputou
   - Cada linha = 1 temporada em 1 competição
   - Campos: matches_played, goals, assists, rating, tackles, passes, etc.

3. **`tournament_summary.csv`** — Resumo formatado em tabela
   ```
   Tournament | Season | Team | Matches | Minutes | Goals | Assists | Rating | ...
   ```

4. **`matches_2026.json`** — Todas as partidas de 2026
   - Dados brutos de cada partida

5. **`matches_2026_summary.csv`** — Resumo das partidas 2026
   ```
   Date | Tournament | Team vs Opponent | Score | Status
   ```

---

## Passo 4: Analisar os Dados

### Ver resumo em terminal

```bash
# Mostrar histórico de carreira (tabela)
python -c "
import csv
with open('data/processed/2026/players/alex_bruno/tournament_summary.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(f\"{row['season']:15} {row['team']:25} {row['matches_played']:3}J {row['goals']:2}G {row['assists']:2}A Rating: {row['rating']:5}\")
"

# Mostrar partidas 2026
python -c "
import csv
with open('data/processed/2026/players/alex_bruno/matches_2026_summary.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(f\"{row['date']} | {row['tournament']:20} | {row['team']:15} vs {row['opponent']:15} | {row['score']}\")
"
```

---

## Campos das Estatísticas

### Tournament Summary (tournament_summary.csv)

| Campo | Descrição |
|---|---|
| tournament | Nome da competição (Série A, Série B, Campeonato Alagoano, etc.) |
| season | Temporada (2023, 2024, 2025, 2026) |
| team | Club disputado nessa temporada |
| matches_played | Jogos disputados |
| minutes_played | Minutos acumulados |
| goals | Gols marcados |
| assists | Assistências |
| rating | Média de desempenho (1-10) |
| tackles | Roubos de bola / combates vencidos |
| blocks | Bloqueios de chute |
| interceptions | Interceptações de passe |
| dribbles | Dribles realizados |
| passes | Passes completados |
| yellow_cards | Cartões amarelos |
| red_cards | Cartões vermelhos |

### Matches 2026 (matches_2026_summary.csv)

| Campo | Descrição |
|---|---|
| date | Data/hora da partida |
| tournament | Competição |
| team | Time de Alex Bruno |
| opponent | Adversário |
| position | "home" (mandante) ou "away" (visitante) |
| status | "finished", "in_progress", "scheduled" |
| score | Placar (ex: "2 - 1") |

---

## Se o ID não funcionar

### Tente esses nomes alternativos:
- `alex bruno`
- `alex-bruno`
- `alexbruno`
- Procure filtrar por **Posição**: Goleiro, Defensor, Meio-campista ou Atacante
- Procure filtrar por **País**: Brasil / Alagoas

### Ou procure em competições específicas:
- **Campeonato Alagoano 2026**:
  ```
  https://www.sofascore.com/pt/football/tournament/brazil/campeonato-alagoano/7772
  ```
  - Vá ao time **ASA-AL**
  - Procure Alex Bruno no elenco

---

## Dúvidas?

- O score, assists e rating vêm do SofaScore — a fonte de dados mais confiável do Brasil
- Dados de 2026 serão atualizados conforme novas partidas ocorrem
- Estatísticas avançadas (xG, passes por zona, heatmaps) podem ser extraídas separadamente se necessário
