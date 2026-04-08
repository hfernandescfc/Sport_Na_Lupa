# SportSofa

Pipeline em Python para extrair, normalizar e validar dados dos clubes da Serie B 2026 a partir de fontes oficiais e do SofaScore.

Escopo atual:

- `Sport Recife`: todas as partidas de 2026 em todas as competicoes disponiveis.
- `Demais clubes da Serie B`: dados somente no contexto da Serie B 2026.

## Comandos

```bash
python -m src.main bootstrap
python -m src.main discover-endpoints
python -m src.main sync-competition --season 2026
python -m src.main sync-sport --season 2026
python -m src.main sync-teams --season 2026
python -m src.main sync-matches --season 2026 --from-round 1 --to-round 38
python -m src.main validate --season 2026
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Estrutura

- `src/`: codigo da pipeline
- `data/raw/`: payloads brutos
- `data/processed/`: dados processados por temporada
- `data/curated/`: datasets consolidados
- `logs/`: logs de execucao
