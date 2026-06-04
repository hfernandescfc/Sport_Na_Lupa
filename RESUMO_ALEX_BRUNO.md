# RESUMO: Extração de Alex Bruno (ASA-AL)

## O Que Foi Coletado

O pipeline SportSofa coletou **1 partida** do Alex Bruno:

```
Copa do Nordeste — Fase Eliminatória (Rodada 27)
Data: 07/05/2026
Partida: Sport Recife 2 × 1 ASA
Posição: Visitante
Minutos: 90 (titular — posição F, camisa 9)

ESTATÍSTICAS:
├─ Rating: 6.7/10
├─ Passes: 22 totais / 14 acurados (63.6%)
├─ Passes longos: 0/0
├─ Chutes: 2
├─ Gols: 0
├─ Assistências: 0
├─ Duelos: 7 vencidos em 8 (87.5%)
├─ Toques: 38
├─ Recuperações: 4
├─ xG (chutes esperados): 0.02
└─ Posse perdida: 16
```

**Localização:** `data/processed/2026/players/alex_bruno/matches_collected.csv`

---

## Limitação

O pipeline **não coleta automaticamente** dados do ASA-AL porque:

- **Escopo do Pipeline:**
  - ✅ Sport Recife (todas as competições)
  - ✅ Série B 2026 (20 clubes)
  - ✅ Alguns adversários selecionados (Vila Nova, Avaí, Fortaleza, etc.)
  - ❌ **Campeonato Alagoano** (fora do escopo)
  - ❌ **ASA-AL** (não está no escopo)

- **Coleta Incidental:**
  - Alex Bruno foi capturado apenas quando **ASA jogou contra o Sport** na Copa do Nordeste

---

## Para Obter Histórico Completo

### ✅ Rápido (5 minutos) — Busca Manual

Acesse diretamente no SofaScore:
```
https://www.sofascore.com/pt/player/alex-bruno/1468444
```

Você verá:
- Todas as temporadas (2023, 2024, 2025, 2026)
- Todos os clubes pelos quais jogou
- Cada competição disputada
- Stats agregadas por torneio/season
- Histórico completo de partidas

**Copiar dados:**
1. Abra `F12` (DevTools)
2. Navegue até a tabela de stats
3. Copie para Excel/CSV

---

### ⚙️ Automatizado (Requer Setup) — Pipeline Customizado

**Pré-requisito:** Encontrar o `team_id` do ASA-AL

1. **Busque o team_id:**
   ```
   https://www.sofascore.com/search?q=asa
   ```
   Clique em "ASA" e copie o número da URL

2. **Execute extração:**
   ```bash
   python -m src.main sync-opponent \
     --team-key asa-al \
     --team-id [ID_AQUI] \
     --season 2026
   ```

3. **Resultado:**
   ```
   data/processed/2026/opponents/asa-al/
   ├─ matches.csv                 (todas as partidas)
   ├─ team_match_stats.csv        (stats de time)
   ├─ player_match_stats.csv      (scouts de TODOS os jogadores)
   ├─ attack_profile.json         (padrões ofensivos)
   └─ summary.json                (resumo estatístico)
   ```

   **Depois filtrar Alex Bruno:**
   ```bash
   grep "alex bruno" data/processed/2026/opponents/asa-al/player_match_stats.csv
   ```

---

## Dados Já Gerados

Todos os arquivos estão em: `data/processed/2026/players/alex_bruno/`

```
alex_bruno/
├── RELATORIO_ALEX_BRUNO.md          ← Relatório detalhado (1 partida)
├── matches_collected.csv            ← Dados brutos da partida
├── summary.json                     ← Resumo em JSON
├── player_info.json                 ← Info do jogador (tentativa)
├── INSTRUCOES_ALEX_BRUNO.md         ← Guia completo de opções
└── RESUMO_ALEX_BRUNO.md             ← Este arquivo
```

---

## Próximos Passos Recomendados

1. **Decisão rápida:** Acesse manualmente `sofascore.com/pt/player/alex-bruno/1468444`

2. **Decisão integrada:** Comente qual é o `team_id` do ASA-AL e eu rodo o pipeline para capturar todos os dados

3. **Compartilhe:**
   - O team_id do ASA-AL
   - Ou a URL completa do perfil do SofaScore

---

## Por Que Isso Aconteceu?

O pipeline SportSofa foi **desenhado especificamente para:**

```
Objetivo: Analisar Sport Recife na Série B 2026

├─ Sport Recife       (17 competições em 2026)
├─ Série B (20 clubes) (38 rodadas planejadas)
└─ Adversários-chave  (Vila Nova, Avaí, Ceará, etc.)
```

**ASA-AL** está fora porque:
- Não é Sport Recife
- Não joga Série B 2026
- Só aparece quando enfrenta o Sport

**Solução:** Estender o pipeline para incluir Campeonato Alagoano (seria novo módulo)

---

**Qual opção você prefere?**
