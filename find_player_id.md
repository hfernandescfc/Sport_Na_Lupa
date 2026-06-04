# Como encontrar o ID do Alex Bruno

## Passo 1: Acessar a página de busca do SofaScore

Abra no navegador:
```
https://www.sofascore.com/search?q=alex+bruno
```

## Passo 2: Abrir Developer Tools

- Pressione `F12` ou `Ctrl+Shift+I` para abrir o DevTools
- Vá para a aba **Network**
- Procure por requisições para `/api/v1/player/...`

## Passo 3: Clicar no perfil do Alex Bruno (ASA)

Na página de resultados, clique no perfil do jogador do ASA-AL. A URL mudará para algo como:
```
https://www.sofascore.com/pt/player/alex-bruno/[PLAYER_ID]
```

O `[PLAYER_ID]` é o número que você precisa.

## Passo 4: Executar a extração

Abra um terminal na pasta do SportSofa e execute:

```bash
python -c "
from extract_player_career_dom import extract_by_id
extract_by_id(player_id=YOUR_PLAYER_ID, player_name='Alex Bruno')
"
```

Substitua `YOUR_PLAYER_ID` pelo ID encontrado.

## Alternativa: Procurar em matches.csv

Se o Alex Bruno jogou contra o Sport em 2026, você pode encontrar o ID dele:

```bash
grep -r 'alex bruno' data/processed/2026/ 2>/dev/null | head -20
```

Ou verificar os arquivos de player_match_stats se ele já foi coletado.
