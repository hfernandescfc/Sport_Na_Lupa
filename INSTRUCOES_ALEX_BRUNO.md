# Extração Completa de Alex Bruno — ASA-AL

## Situação Atual

O pipeline SportSofa coletou **apenas 1 partida** do Alex Bruno:
- **Copa do Nordeste** — Sport Recife vs ASA (07/05/2026)
- **Rating:** 6.7/10
- **Estatísticas:** 90 min, 22 passes (63.6%), 7 duelos ganhos, 2 chutes

O ASA-AL não está no escopo automático do pipeline (que coleta Sport Recife e Série B). Portanto, para obter histórico completo:

---

## Opção 1: Busca Manual no SofaScore (Recomendado para análise rápida)

### Passos:

1. **Acesse a página do jogador:**
   ```
   https://www.sofascore.com/pt/player/alex-bruno/1468444
   ```

2. **Você verá:**
   - Foto do jogador
   - Posição e dados biométricos
   - **Abas laterais:**
     - **Overview** — resumo geral
     - **Stats** — estatísticas por temporada/competição ✅ AQUI
     - **Matches** — lista de partidas ✅ AQUI
     - **Heatmap** — mapa de posicionamento por competição

3. **Coletar dados por temporada:**
   - Campeonato Alagoano 2025, 2024, 2023
   - Copa do Nordeste (todas as rodadas)
   - Copa do Brasil (se houver)
   - Qualquer competição que ele tenha disputado

4. **Tomar screenshot ou copiar tabela:**
   - Dev Tools (F12) → Inspector
   - Clicar com botão direito na tabela
   - Copiar para Excel/Google Sheets

---

## Opção 2: Criar Pipeline ASA-AL (Automatizado)

Se você quiser que o SportSofa extraia **todos os dados do ASA-AL automaticamente**, preciso:

1. **Identificar o team_id do ASA-AL no SofaScore**
   ```bash
   # Procure em: https://www.sofascore.com/search?q=asa
   # Copie o ID numérico
   ```

2. **Criar comando CLI novo:**
   ```bash
   python -m src.main sync-opponent --team-key asa-al --team-id [ID_AQUI] --season 2026
   ```

3. **Isso extrairá:**
   - Todas as partidas do ASA-AL em 2026
   - Stats de time por partida
   - **Scouts de todos os jogadores** (incluindo Alex Bruno) em cada partida
   - Stats avançadas (xG, passes por zona, heatmaps, etc.)

---

## Opção 3: Script Python Customizado (Mais Técnico)

Se você fornecer o team_id do ASA-AL, posso criar um script que:

```bash
python extract_asa_al_complete.py --team-id [ID] --season 2026
```

Isso geraria:

```
data/processed/2026/opponents/asa-al/
├── matches.csv              ← Todas as partidas
├── team_match_stats.csv     ← Stats de time por partida
├── player_match_stats.csv   ← Scouts de TODOS os jogadores (Alex Bruno + squad)
├── attack_profile.json      ← Análise de padrões ofensivos
└── summary.json             ← Resumo estatístico

# Dados do Alex Bruno estariam em player_match_stats.csv
# Filtrado: grep "alex bruno" player_match_stats.csv
```

---

## Dados Que Você Obteria

### Histórico Completo (por temporada)

```
Temporada | Competição | Time | Matches | Minutes | Goals | Assists | Rating | Passes | Tackles
2023      | Alagoano   | ASA  |   18    |  1620   |  5    |    2    |  7.1   |  145   |   32
2024      | Alagoano   | ASA  |   20    |  1800   |  7    |    3    |  7.3   |  168   |   28
2025      | Alagoano   | ASA  |   15    |  1350   |  4    |    1    |  7.0   |  132   |   25
2026      | Alagoano   | ASA  |   12    |  1080   |  3    |    2    |  6.9   |  98    |   18
2026      | Copa NE    | ASA  |    1    |   90    |  0    |    0    |  6.7   |  22    |   7
```

### Partidas por Competição

```
2026-04-12 | Campeonato Alagoano      | ASA 2-1 CRB        | Mandante | 90 min | 7.8 rating
2026-04-15 | Campeonato Alagoano      | ASA 1-2 Murici     | Visitante| 90 min | 6.5 rating
2026-05-07 | Copa do Nordeste (K.O.)  | Sport 2-1 ASA      | Visitante| 90 min | 6.7 rating
...
```

### Stats Avançadas (2026)

```
Competição          | xG (chutes esperados) | Pass Accuracy | Dribbles | xA (assists esperados)
Campeonato Alagoano |        1.2            |      72.4%    |    8     |         0.3
Copa do Nordeste    |        0.1            |      63.6%    |    0     |         0.0
```

---

## Recomendação

**Para análise rápida:**
→ Use **Opção 1** (manual no SofaScore, 5 minutos)

**Para análise profunda com alertas automáticos:**
→ Use **Opção 2** (comando CLI, uma vez) + monitoramento recorrente

**Qual você prefere?**
