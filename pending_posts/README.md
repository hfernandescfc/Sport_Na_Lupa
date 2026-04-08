# Curadoria @SportRecifeLab

Cada post sugerido vive em uma subpasta com slug `YYYY-MM-DD_tipo_assunto`.

## Estrutura de cada post

```
pending_posts/
  2026-03-27_apresentacao_habraao/
    card.png        ← imagem para anexar no X
    tweet.txt       ← texto do post (dentro de 280 chars)
    metadata.json   ← contexto, métricas, fonte
```

## Fluxo de curadoria

| Etapa | Ação |
|---|---|
| **Revisar** | Leia `tweet.txt` e veja `card.png` |
| **Aprovar** | Mova a pasta para `../posted/` |
| **Rejeitar** | Mova a pasta para `../rejected/` |
| **Ajustar** | Edite `tweet.txt` antes de mover |

## Tipos de post (`type` no metadata)

- `apresentacao_jogador` — novo reforço com scout de carreira
- `scout_partida` — destaque individual pós-jogo
- `analise_tecnico` — candidatos à comissão técnica
- `recorte_serie_b` — comparativo de desempenho na B
- `thread_abertura` — tweet de abertura de thread temática
