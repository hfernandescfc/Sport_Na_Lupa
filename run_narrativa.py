"""
run_narrativa.py -- CLI para o pipeline de análise de narrativas no X.

Uso básico (dados mock para desenvolvimento):
    python run_narrativa.py --tema "time sem vontade" --mock

Uso com snscrape (pode não funcionar dependendo da versão):
    python run_narrativa.py \
        --tema "time sem vontade" \
        --query "Sport Recife sem vontade treinador" \
        --kw "vontade" "apagado" "liderança" "projeto" \
        --frase "elenco sem vontade e liderança" \
        --desde 2024-04-01 \
        --max 500

Uso com análise semântica:
    python run_narrativa.py --tema "critica treinador" --semantica --mock

Para ver todos os parâmetros:
    python run_narrativa.py --help
"""

import argparse
import sys
from pathlib import Path

# Adiciona a raiz do projeto ao path para importar src.narrativa
sys.path.insert(0, str(Path(__file__).parent))

from src.narrativa.pipeline import run


# ---------------------------------------------------------------------------
# Exemplos pré-configurados -- prontos para testar
# ---------------------------------------------------------------------------

EXEMPLOS = {
    "sem_vontade": {
        "tema": "time sem vontade",
        "query": "Sport Recife sem vontade treinador",
        "palavras_chave": ["vontade", "apagado", "largado", "sem jogo", "covarde"],
        "frase_base": "time jogando sem vontade e liderança",
    },
    "critica_tecnico": {
        "tema": "crítica ao técnico",
        "query": "Sport Recife técnico demissão treinador",
        "palavras_chave": ["demitir", "técnico", "treinador", "escalação", "tático", "time ruim"],
        "frase_base": "o treinador não sabe escalar e o time não tem tática",
    },
    "elenco_fraco": {
        "tema": "elenco fraco",
        "query": "Sport Recife elenco reforço fraco",
        "palavras_chave": ["elenco", "reforço", "fraco", "limitado", "contratação"],
        "frase_base": "elenco fraco precisando de reforços urgente",
    },
}


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pipeline de análise de propagação de narrativas no X",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Conteúdo da análise
    parser.add_argument(
        "--tema", type=str, default="time sem vontade",
        help="Nome legível da narrativa (ex: 'time sem vontade')"
    )
    parser.add_argument(
        "--query", type=str, default=None,
        help="Query de busca para snscrape. Padrão: usa o tema."
    )
    parser.add_argument(
        "--kw", nargs="+", default=None,
        help="Palavras-chave para filtro de relevância (ex: --kw vontade apagado)"
    )
    parser.add_argument(
        "--frase", type=str, default=None,
        help="Frase-base para similaridade semântica"
    )

    # Exemplo pré-configurado
    parser.add_argument(
        "--exemplo", choices=list(EXEMPLOS.keys()), default=None,
        help="Usar um exemplo pré-configurado"
    )

    # Coleta
    parser.add_argument(
        "--mock", action="store_true",
        help="Usar dados mock (para desenvolvimento local, sem snscrape)"
    )
    parser.add_argument(
        "--ntscraper", action="store_true",
        help="Usar ntscraper (instâncias Nitter -- frequentemente offline)"
    )
    parser.add_argument(
        "--twscrape", action="store_true",
        help="Usar twscrape (requer conta Twitter configurada via 'twscrape add_accounts')"
    )
    parser.add_argument(
        "--max", type=int, default=400,
        help="Número máximo de tweets a coletar (padrão: 400)"
    )
    parser.add_argument(
        "--desde", type=str, default=None,
        help="Data inicial (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--ate", type=str, default=None,
        help="Data final (YYYY-MM-DD)"
    )

    # Análise
    parser.add_argument(
        "--n-primeiros", type=int, default=20,
        help="Quantidade de primeiros tweets para análise de origem (padrão: 20)"
    )
    parser.add_argument(
        "--freq", type=str, default="2h",
        help="Frequência da série temporal (padrão: '2h'). Ex: '1h', '30min', '1D'"
    )

    # Semântica
    parser.add_argument(
        "--semantica", action="store_true",
        help="Ativar similaridade semântica (requer sentence-transformers)"
    )
    parser.add_argument(
        "--threshold-sem", type=float, default=0.45,
        help="Threshold de similaridade semântica (padrão: 0.45)"
    )
    parser.add_argument(
        "--modo-combinacao", type=str, default="kw_only",
        choices=["union", "intersection", "kw_only", "sem_only"],
        help="Como combinar filtro KW + semântico (padrão: kw_only)"
    )

    # Extras
    parser.add_argument(
        "--clustering", action="store_true",
        help="Ativar clustering de sub-narrativas (requer sentence-transformers + sklearn)"
    )
    parser.add_argument(
        "--n-clusters", type=int, default=5,
        help="Número de clusters para sub-narrativas (padrão: 5)"
    )
    parser.add_argument(
        "--grafo", action="store_true",
        help="Gerar grafo de propagação (requer networkx)"
    )

    # Output
    parser.add_argument(
        "--sem-csv", action="store_true",
        help="Não salvar CSV dos tweets processados"
    )

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = build_parser()
    args = parser.parse_args()

    # Usar exemplo pré-configurado se especificado
    if args.exemplo:
        ex = EXEMPLOS[args.exemplo]
        tema = ex["tema"]
        query = ex["query"]
        palavras_chave = ex["palavras_chave"]
        frase_base = ex["frase_base"]
        print(f"[Exemplo] Usando configuração: '{args.exemplo}'")
    else:
        tema = args.tema
        query = args.query or tema
        palavras_chave = args.kw or tema.split()
        frase_base = args.frase

    # Modo de coleta
    if args.mock:
        modo_coleta = "mock"
    elif args.ntscraper:
        modo_coleta = "ntscraper"
    elif args.twscrape:
        modo_coleta = "twscrape"
    else:
        modo_coleta = "snscrape"

    # Construir configuração
    config = {
        "modo_coleta": modo_coleta,
        "max_tweets": args.max,
        "desde": args.desde,
        "ate": args.ate,
        "n_primeiros": args.n_primeiros,
        "freq_serie": args.freq,
        "usar_semantica": args.semantica,
        "threshold_semantico": args.threshold_sem,
        "modo_combinacao": args.modo_combinacao,
        "usar_clustering": args.clustering,
        "n_clusters": args.n_clusters,
        "gerar_grafo": args.grafo,
        "salvar_csv": not args.sem_csv,
    }

    # Executar pipeline
    resultado = run(
        tema=tema,
        query=query,
        palavras_chave=palavras_chave,
        frase_base=frase_base,
        config=config,
        pasta_raiz=".",
    )

    print(f"\n[Concluído] Post salvo em: {resultado['pasta_post']}")


if __name__ == "__main__":
    main()
