"""
generate_player_card.py — gera card PNG de analise de jogador a partir de dados estruturados.

Uso:
    python generate_player_card.py          # gera exemplo Edson Lucas
    from generate_player_card import render_card, CardData, Stat
"""
import base64, io, os, pathlib, time
from dataclasses import dataclass, field


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class Stat:
    label: str
    value: str
    delta: str            # ex: "+67%", "-5%", "ss"
    positive: bool = True
    base_label: str = ""  # ex: "vs media de laterais"
    featured: bool = False


@dataclass
class CardData:
    # Jogador
    player_name: str
    first_name: str
    last_name: str
    position: str
    photo_path: str
    rating: str

    # Partida
    home_team: str
    away_team: str
    score: str
    competition: str
    round_info: str
    minutes: int = 90

    # Stats
    stats: list = field(default_factory=list)
    compare_label: str = "vs media dos titulares anteriores"

    # Assets
    escudo_path: str = "data/cache/logos/1959.png"
    avatar_path: str = "sportrecifelab_avatar.png"
    source: str = "Dados: SofaScore"

    # Output
    output_path: str = "card_output.png"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _b64_src(path: str) -> str:
    data = pathlib.Path(path).read_bytes()
    ext = pathlib.Path(path).suffix.lower().lstrip(".")
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    return f"data:image/{mime};base64,{base64.b64encode(data).decode()}"


def _stat_html(stat: Stat) -> str:
    delta_cls = "pos" if stat.positive else "neg"
    base = f'<span class="base">{stat.base_label}</span>' if stat.base_label else ""
    if stat.featured:
        return (
            '<div class="stat-featured">'
            f'<div class="value">{stat.value}</div>'
            '<div class="info">'
            f'<div class="label">{stat.label}</div>'
            f'<div class="delta {delta_cls}">{stat.delta}</div>'
            f'{base}'
            '</div></div>'
        )
    return (
        '<div class="stat-compact">'
        f'<div class="value">{stat.value}</div>'
        f'<div class="label">{stat.label}{base}</div>'
        f'<div class="delta {delta_cls}">{stat.delta}</div>'
        '</div>'
    )


def _build_html(data: CardData) -> str:
    template = (
        pathlib.Path(__file__).parent / "templates" / "player_card.html"
    ).read_text(encoding="utf-8")

    stats_html = "\n".join(_stat_html(s) for s in data.stats)

    subs = {
        "{{HOME_TEAM}}":     data.home_team,
        "{{SCORE}}":         data.score,
        "{{AWAY_TEAM}}":     data.away_team,
        "{{COMPETITION}}":   data.competition,
        "{{ROUND}}":         data.round_info,
        "{{MINUTES}}":       str(data.minutes),
        "{{PHOTO_SRC}}":     _b64_src(data.photo_path),
        "{{PLAYER_NAME}}":   data.player_name,
        "{{FIRST_NAME}}":    data.first_name,
        "{{LAST_NAME}}":     data.last_name,
        "{{POSITION}}":      data.position,
        "{{RATING}}":        data.rating,
        "{{ESCUDO_SRC}}":    _b64_src(data.escudo_path),
        "{{AVATAR_SRC}}":    _b64_src(data.avatar_path),
        "{{COMPARE_LABEL}}": data.compare_label,
        "{{STATS_HTML}}":    stats_html,
        "{{SOURCE}}":        data.source,
    }
    for k, v in subs.items():
        template = template.replace(k, v)
    return template


# ── Renderer ──────────────────────────────────────────────────────────────────

def render_card(data: CardData) -> str:
    """Renderiza CardData em PNG. Retorna caminho do arquivo gerado."""
    from selenium import webdriver
    from selenium.webdriver.edge.options import Options
    from PIL import Image

    html_content = _build_html(data)
    wrapper = pathlib.Path("_card_render_tmp.html")
    wrapper.write_text(html_content, encoding="utf-8")

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--force-device-scale-factor=1")
    driver = webdriver.Edge(options=options)

    try:
        html_path = os.path.abspath(str(wrapper)).replace("\\", "/")
        driver.get("file:///" + html_path)
        time.sleep(2)
        driver.set_window_size(2000, 2000)
        time.sleep(0.3)
        png_bytes = driver.get_screenshot_as_png()
    finally:
        driver.quit()
        wrapper.unlink(missing_ok=True)

    img = Image.open(io.BytesIO(png_bytes))
    card = img.crop((0, 0, 1080, 1080))

    pathlib.Path(data.output_path).parent.mkdir(parents=True, exist_ok=True)
    card.save(data.output_path)
    print(f"Card salvo: {data.output_path}")
    return data.output_path


# ── Exemplo: Edson Lucas · Copa do Nordeste R4 ───────────────────────────────

EDSON_LUCAS_R4 = CardData(
    player_name="Edson Lucas",
    first_name="EDSON",
    last_name="LUCAS",
    position="Lateral Esquerdo  #96",
    photo_path="edson_lucas_foto.jpg",
    rating="7.5",

    home_team="Sport Recife",
    away_team="Maranho AC",
    score="5 - 0",
    competition="Copa do Nordeste 2026",
    round_info="Rodada 4",
    minutes=90,

    compare_label="vs media dos laterais esquerdos anteriores (Felipinho - Rafinha)",

    stats=[
        Stat("PASSES",          "80",     "+67%",  True,  "vs media de laterais", featured=True),
        Stat("ACERTO DE PASSE", "91.3%",  "+14%",  True,  "vs media de laterais", featured=True),
        Stat("NO TERCO FINAL",  "38",     "+93%",  True,  "vs media de laterais"),
        Stat("CHUTES NO GOL",   "3",      "+350%", True,  "vs media de laterais"),
        Stat("DUELOS GANHOS",   "8",      "+71%",  True,  "vs media de laterais"),
        Stat("TOQUES NA BOLA",  "103",    "+74%",  True,  "vs media de laterais"),
        Stat("RECUPERACOES",    "9",      "--",    True,  ""),
    ],

    output_path="card_output_test.png",
)


if __name__ == "__main__":
    render_card(EDSON_LUCAS_R4)
