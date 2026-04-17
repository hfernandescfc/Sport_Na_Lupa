"""
Gerador de cards Raio-X v2 — design system novo.

Renderiza HTML/CSS via Selenium Edge headless → PNG 1080×1350 (portrait 4:5).

Design system:
  - Fontes: Archivo (números/títulos) + JetBrains Mono (labels/dados)
  - Paleta: #0B0B0E bg | #F5F1E8 ink | #F2C230 yellow | #E63946 red | #3DA35D green
  - Estrutura: header fixo (brand + meta) | rule | conteúdo | footer fixo
  - Cards sem bordas coloridas — cor como acento tipográfico

Uso:
  python -X utf8 generate_raio_x_v2.py --team-key america-mg --round 5

Ou como módulo:
  from generate_raio_x_v2 import RaioXCards
  cards = RaioXCards(data, out_dir="pending_posts/...")
  cards.render_all()
"""

import os
import sys
import time
import base64
import tempfile
import argparse
import textwrap
from pathlib import Path
from typing import Any

try:
    from selenium import webdriver
    from selenium.webdriver.edge.options import Options as EdgeOptions
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False


# ─── Design tokens (espelham o CSS do design de referência) ──────────────────
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Archivo:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900;1,400&family=Archivo+Narrow:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

:root {
  --bg:       #0B0B0E;
  --bg-2:     #13131A;
  --bg-3:     #1A1A22;
  --ink:      #F5F1E8;
  --ink-2:    #B8B4AB;
  --ink-3:    #6E6B64;
  --line:     #26262F;
  --line-2:   #34343F;
  --yellow:   #F2C230;
  --yellow-dim:#8A6F1C;
  --red:      #E63946;
  --red-dim:  #7A1F26;
  --green:    #3DA35D;
  --green-dim:#1F5330;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{
  width:1080px; height:1350px; overflow:hidden;
  background:var(--bg); color:var(--ink);
  font-family:'Archivo',sans-serif;
  -webkit-font-smoothing:antialiased;
  text-rendering:optimizeLegibility;
}
.card{
  width:1080px; height:1350px;
  background:var(--bg); color:var(--ink);
  position:relative; overflow:hidden;
}

/* ── Header ── */
.cap{
  display:flex; align-items:center; justify-content:space-between;
  padding:44px 56px 0; height:110px;
}
.cap-brand{ display:flex; align-items:center; gap:14px; }
.cap-brand img{ width:56px; height:56px; border-radius:50%; object-fit:cover; }
.cap-brand .wordmark { line-height:1; }
.cap-brand .wordmark .h{
  font-family:'Archivo',sans-serif; font-weight:800; font-size:22px;
  letter-spacing:-0.01em; color:var(--ink);
}
.cap-brand .wordmark .s{
  font-family:'JetBrains Mono',monospace; font-weight:500; font-size:13px;
  color:var(--ink-3); letter-spacing:0.04em; margin-top:4px;
}
.cap-meta{
  text-align:right; font-family:'JetBrains Mono',monospace;
  font-size:14px; letter-spacing:0.1em; text-transform:uppercase;
  color:var(--yellow); font-weight:500; line-height:1.5;
}
.cap-meta .dim{ color:var(--ink-3); }
.rule{ height:1px; background:var(--line); margin:20px 56px 0; }

/* ── Footer ── */
.foot{
  position:absolute; left:56px; right:56px; bottom:36px;
  display:flex; justify-content:space-between; align-items:center;
  font-family:'JetBrains Mono',monospace; font-size:13px;
  letter-spacing:0.08em; text-transform:uppercase; color:var(--ink-3);
}
.foot .src b{ color:var(--ink-2); font-weight:500; }
.foot .pg{ display:flex; align-items:center; gap:10px; }
.foot .pg .n{ color:var(--ink); }
.foot .pg .t{ color:var(--ink-3); }

/* ── Kicker / Card title block ── */
.kicker{
  font-family:'JetBrains Mono',monospace; font-size:13px;
  letter-spacing:0.16em; text-transform:uppercase;
  color:var(--yellow); font-weight:500;
}
.card-title-block{ padding:8px 56px 0; }
.card-title-block .kicker{ margin-top:8px; }
.card-title-block h1{
  margin-top:14px; font-family:'Archivo',sans-serif; font-weight:900;
  font-size:88px; line-height:0.9; letter-spacing:-0.025em; color:var(--ink);
}
.card-title-block h1 em{ font-style:normal; color:var(--yellow); }
.card-title-block .sub{
  margin-top:10px; font-family:'JetBrains Mono',monospace;
  color:var(--ink-2); font-size:18px; letter-spacing:0.04em;
}

/* ── P1 CAPA ── */
.p1 .hero{ padding:48px 56px 0; margin-top:8px; }
.p1 .hero .kicker{ margin-bottom:22px; }
.p1 .hero h1{
  font-family:'Archivo',sans-serif; font-weight:900;
  font-size:220px; line-height:0.84; letter-spacing:-0.04em; color:var(--yellow);
}
.p1 .hero h1 .x{ color:var(--ink); }
.p1 .hero h2{
  margin-top:18px; font-family:'Archivo',sans-serif; font-weight:800;
  font-size:62px; line-height:0.95; letter-spacing:-0.015em; color:var(--ink);
}
.p1 .hero .sub{
  margin-top:14px; font-family:'JetBrains Mono',monospace;
  color:var(--ink-2); font-size:20px; letter-spacing:0.04em;
}
.p1 .body{
  margin-top:48px; padding:0 56px;
  display:grid; grid-template-columns:420px 1fr; gap:40px; align-items:center;
}
.p1 .badge-wrap{
  width:420px; height:420px;
  background:radial-gradient(ellipse at center, rgba(29,110,61,0.22), transparent 62%);
  display:flex; align-items:center; justify-content:center; position:relative;
}
.p1 .badge-wrap::before{
  content:""; position:absolute; inset:40px;
  border:1px dashed var(--line-2); border-radius:50%; opacity:0.6;
}
.p1 .badge-wrap img{
  width:300px; height:300px; object-fit:contain;
  filter:drop-shadow(0 20px 40px rgba(0,0,0,0.6));
}
.p1 .kpis{ display:flex; flex-direction:column; border-top:1px solid var(--line); }
.p1 .kpi{
  padding:22px 0; border-bottom:1px solid var(--line);
  display:grid; grid-template-columns:1fr auto; align-items:baseline; gap:20px;
}
.p1 .kpi .l{
  font-family:'JetBrains Mono',monospace; font-size:14px;
  color:var(--ink-3); text-transform:uppercase; letter-spacing:0.1em;
}
.p1 .kpi .v{
  font-family:'Archivo',sans-serif; font-weight:800;
  font-size:56px; line-height:1; letter-spacing:-0.02em; color:var(--ink);
}
.p1 .kpi .v.warn{ color:var(--red); }
.p1 .kpi .v.ok{ color:var(--yellow); }
.p1 .kpi .v small{
  font-size:24px; color:var(--ink-3); font-weight:500; margin-left:6px; letter-spacing:0;
}

/* ── P2 CAMPANHA ── */
.p2 .record{
  margin:48px 56px 0; display:flex; align-items:stretch;
  height:120px; border:1px solid var(--line);
}
.p2 .record .seg{
  flex:var(--f,1); display:flex; align-items:center;
  justify-content:center; gap:16px; position:relative;
}
.p2 .record .seg+.seg{ border-left:1px solid var(--line); }
.p2 .record .seg .n{
  font-family:'Archivo',sans-serif; font-weight:900;
  font-size:72px; line-height:1; letter-spacing:-0.025em;
}
.p2 .record .seg .l{
  font-family:'JetBrains Mono',monospace; font-size:13px;
  text-transform:uppercase; color:var(--ink-2); letter-spacing:0.12em;
}
.p2 .record .v .n{ color:var(--green); }
.p2 .record .e .n{ color:var(--yellow); }
.p2 .record .d .n{ color:var(--red); }
.p2 .stack{
  margin:20px 56px 0; height:12px; display:flex;
  border-radius:2px; overflow:hidden;
}
.p2 .stack .bar{ height:100%; }
.p2 .summary{
  margin:36px 56px 0; display:flex; align-items:baseline;
  justify-content:space-between; padding-bottom:28px;
  border-bottom:1px solid var(--line);
}
.p2 .summary .item{ display:flex; flex-direction:column; gap:6px; }
.p2 .summary .item .n{
  font-family:'Archivo',sans-serif; font-weight:800;
  font-size:56px; line-height:1; color:var(--ink); letter-spacing:-0.02em;
}
.p2 .summary .item .l{
  font-family:'JetBrains Mono',monospace; font-size:12px;
  color:var(--ink-3); text-transform:uppercase; letter-spacing:0.12em;
}
.p2 .goals{
  margin:36px 56px 0; display:grid;
  grid-template-columns:1fr 1fr 1fr; gap:16px;
  padding-bottom:24px; border-bottom:1px solid var(--line);
}
.p2 .goals .n{
  font-family:'Archivo',sans-serif; font-weight:800;
  font-size:88px; line-height:1; letter-spacing:-0.03em;
}
.p2 .goals .n.neg{ color:var(--red); }
.p2 .goals .n.for{ color:var(--ink); }
.p2 .goals .l{
  margin-top:10px; font-family:'JetBrains Mono',monospace; font-size:13px;
  color:var(--ink-2); text-transform:uppercase; letter-spacing:0.1em;
}
.p2 .breakdown{ margin:32px 56px 0; }
.p2 .breakdown h3{
  font-family:'JetBrains Mono',monospace; font-size:12px;
  color:var(--ink-3); text-transform:uppercase; letter-spacing:0.14em; margin-bottom:18px;
}
.p2 .breakdown .row{
  display:grid; grid-template-columns:26px 1fr 80px 120px; gap:18px;
  align-items:center; padding:14px 0; border-bottom:1px solid var(--line);
}
.p2 .breakdown .row:last-child{ border-bottom:none; }
.p2 .breakdown .row .tick{ width:10px; height:10px; background:var(--yellow); border-radius:1px; }
.p2 .breakdown .row .name{
  font-family:'Archivo',sans-serif; font-weight:600; font-size:22px; color:var(--ink);
}
.p2 .breakdown .row .n{
  font-family:'Archivo',sans-serif; font-weight:700;
  font-size:26px; color:var(--ink); text-align:right; letter-spacing:-0.01em;
}
.p2 .breakdown .row .n small{
  font-family:'JetBrains Mono',monospace; font-size:14px; color:var(--ink-3); margin-left:6px;
}
.p2 .breakdown .bar{ height:8px; background:var(--bg-3); position:relative; }
.p2 .breakdown .bar i{
  position:absolute; inset:0 auto 0 0; background:var(--yellow); display:block;
}

/* ── P3 MANDANTE ── */
.p3 .big{
  margin:48px 56px 0; display:flex; align-items:baseline; gap:24px;
  padding-bottom:30px; border-bottom:1px solid var(--line);
}
.p3 .big .num{
  font-family:'Archivo',sans-serif; font-weight:900;
  font-size:220px; line-height:0.85; letter-spacing:-0.04em; color:var(--yellow);
}
.p3 .big .num small{ font-size:120px; color:var(--yellow-dim); }
.p3 .big .caption{
  flex:1; font-family:'JetBrains Mono',monospace;
  color:var(--ink-2); font-size:16px; line-height:1.5; letter-spacing:0.03em;
}
.p3 .big .caption b{
  color:var(--ink); font-weight:500; text-transform:uppercase; letter-spacing:0.1em;
  display:block; font-size:13px; margin-bottom:8px;
}
.p3 .split{
  margin:32px 56px 0; display:grid; grid-template-columns:1fr 1fr;
  gap:0; border:1px solid var(--line);
}
.p3 .split .col{ padding:28px 32px; }
.p3 .split .col+.col{ border-left:1px solid var(--line); }
.p3 .split .col .head{
  font-family:'JetBrains Mono',monospace; font-size:12px;
  color:var(--ink-3); text-transform:uppercase; letter-spacing:0.14em; margin-bottom:20px;
}
.p3 .split .col .head b{ color:var(--ink); font-weight:500; }
.p3 .split .line{
  display:flex; justify-content:space-between; align-items:baseline;
  padding:12px 0; border-bottom:1px solid var(--line);
}
.p3 .split .line:last-child{ border:none; }
.p3 .split .line .l{
  font-family:'JetBrains Mono',monospace; font-size:13px;
  color:var(--ink-2); text-transform:uppercase; letter-spacing:0.1em;
}
.p3 .split .line .v{
  font-family:'Archivo',sans-serif; font-weight:700;
  font-size:30px; color:var(--ink); letter-spacing:-0.01em;
}
.p3 .split .line .v.warn{ color:var(--red); }
.p3 .split .line .v.ok{ color:var(--green); }
.p3 .split .line .v.acc{ color:var(--yellow); }
.p3 .insight{
  margin:36px 56px 0; padding:28px 32px;
  background:var(--bg-2); border-left:3px solid var(--yellow);
}
.p3 .insight .k{
  font-family:'JetBrains Mono',monospace; font-size:12px;
  color:var(--yellow); text-transform:uppercase; letter-spacing:0.14em;
}
.p3 .insight .t{
  margin-top:10px; font-family:'Archivo',sans-serif; font-weight:700;
  font-size:28px; line-height:1.2; color:var(--ink); letter-spacing:-0.01em;
}
.p3 .insight .s{
  margin-top:10px; font-family:'Archivo',sans-serif;
  font-size:18px; color:var(--ink-2); line-height:1.45;
}

/* ── P4 ÚLTIMOS 5 ── */
.p4 .streak{
  margin:48px 56px 0; display:grid; grid-template-columns:repeat(5,1fr); gap:14px;
  padding-bottom:36px; border-bottom:1px solid var(--line);
}
.p4 .streak .s{
  aspect-ratio:1; display:flex; align-items:center; justify-content:center;
  font-family:'Archivo',sans-serif; font-weight:900;
  font-size:72px; letter-spacing:-0.02em; border:2px solid;
}
.p4 .streak .s.v{ color:var(--green); border-color:var(--green-dim); background:rgba(61,163,93,0.08); }
.p4 .streak .s.e{ color:var(--yellow); border-color:var(--yellow-dim); background:rgba(242,194,48,0.06); }
.p4 .streak .s.d{ color:var(--red); border-color:var(--red-dim); background:rgba(230,57,70,0.06); }
.p4 .streak-meta{
  margin:16px 56px 0; font-family:'JetBrains Mono',monospace;
  font-size:13px; color:var(--ink-3); text-transform:uppercase; letter-spacing:0.12em;
  display:flex; justify-content:space-between;
}
.p4 .matches{ margin:30px 56px 0; }
.p4 .match{
  display:grid; grid-template-columns:86px 1fr auto 1fr 52px;
  gap:20px; align-items:center; padding:22px 0;
  border-bottom:1px solid var(--line);
}
.p4 .match:first-child{ border-top:1px solid var(--line); }
.p4 .match .date{ font-family:'JetBrains Mono',monospace; font-size:14px; line-height:1.3; }
.p4 .match .date .d{ color:var(--ink); font-weight:700; font-size:20px; letter-spacing:0.02em; }
.p4 .match .date .c{ color:var(--ink-3); display:block; margin-top:4px; text-transform:uppercase; font-size:11px; letter-spacing:0.08em; }
.p4 .match .team{ font-family:'Archivo',sans-serif; font-weight:600; font-size:28px; letter-spacing:-0.01em; color:var(--ink-2); }
.p4 .match .team.home{ text-align:right; }
.p4 .match .team.me{ color:var(--ink); font-weight:800; }
.p4 .match .score{
  font-family:'Archivo',sans-serif; font-weight:900; font-size:36px;
  color:var(--ink); letter-spacing:-0.02em; min-width:120px; text-align:center;
}
.p4 .match .score .x{ color:var(--ink-3); font-weight:500; margin:0 10px; }
.p4 .match .chip{
  width:44px; height:44px; border-radius:50%;
  display:flex; align-items:center; justify-content:center;
  font-family:'Archivo',sans-serif; font-weight:900; font-size:22px; justify-self:end;
}
.p4 .match .chip.v{ background:var(--green); color:#06210F; }
.p4 .match .chip.e{ background:var(--yellow); color:#2A1F02; }
.p4 .match .chip.d{ background:var(--red); color:#2A0609; }

/* ── P5 xG ── */
.p5 .metrics{
  margin:40px 56px 0; display:grid; grid-template-columns:repeat(3,1fr);
  border-top:1px solid var(--line); border-bottom:1px solid var(--line);
}
.p5 .metrics .m{ padding:28px 8px; }
.p5 .metrics .m+.m{ border-left:1px solid var(--line); }
.p5 .metrics .m .n{
  font-family:'Archivo',sans-serif; font-weight:900;
  font-size:88px; line-height:1; letter-spacing:-0.03em; color:var(--ink);
}
.p5 .metrics .m .n .u{ color:var(--ink-3); font-size:48px; margin-left:4px; }
.p5 .metrics .m .l{
  margin-top:14px; font-family:'JetBrains Mono',monospace; font-size:13px;
  color:var(--ink-2); text-transform:uppercase; letter-spacing:0.1em;
}
.p5 .metrics .m .t{ margin-top:6px; font-family:'Archivo',sans-serif; font-size:16px; color:var(--ink-3); }
.p5 .thesis{ margin:40px 56px 0; }
.p5 .thesis .k{
  font-family:'JetBrains Mono',monospace; font-size:12px;
  color:var(--yellow); text-transform:uppercase; letter-spacing:0.14em;
}
.p5 .thesis h3{
  margin-top:10px; font-family:'Archivo',sans-serif; font-weight:800;
  font-size:44px; line-height:1.1; color:var(--ink); letter-spacing:-0.02em;
}
.p5 .thesis h3 em{ font-style:normal; color:var(--red); }
.p5 .thesis p{
  margin-top:16px; font-family:'Archivo',sans-serif;
  font-size:19px; color:var(--ink-2); line-height:1.5;
}
.p5 .pitch-block{ margin:32px 56px 0; padding-top:28px; border-top:1px solid var(--line); }
.p5 .pitch-block .h{
  display:flex; justify-content:space-between; align-items:baseline; margin-bottom:20px;
}
.p5 .pitch-block .h .t{
  font-family:'Archivo',sans-serif; font-weight:700; font-size:24px; color:var(--ink); letter-spacing:-0.01em;
}
.p5 .pitch-block .h .s{
  font-family:'JetBrains Mono',monospace; font-size:12px;
  color:var(--ink-3); text-transform:uppercase; letter-spacing:0.14em;
}
.p5 .pitch{
  position:relative; height:220px; background:var(--bg-2);
  border:1px solid var(--line); display:grid; grid-template-columns:1fr 1fr 1fr;
}
.p5 .pitch .zone{
  position:relative; display:flex; flex-direction:column;
  justify-content:flex-end; padding:20px;
}
.p5 .pitch .zone+.zone{ border-left:1px dashed var(--line-2); }
.p5 .pitch .zone .fill{ position:absolute; left:0; right:0; bottom:0; background:var(--zone,rgba(230,57,70,0.75)); }
.p5 .pitch .zone .pct{
  position:relative; font-family:'Archivo',sans-serif; font-weight:900;
  font-size:56px; line-height:1; letter-spacing:-0.03em; color:var(--ink);
}
.p5 .pitch .zone .lab{
  position:relative; margin-top:8px; font-family:'JetBrains Mono',monospace;
  font-size:12px; color:var(--ink-2); text-transform:uppercase; letter-spacing:0.14em;
}
.p5 .pitch-ruler{
  margin:8px 0 0; display:grid; grid-template-columns:1fr 1fr 1fr;
  font-family:'JetBrains Mono',monospace; font-size:11px;
  color:var(--ink-3); text-transform:uppercase; letter-spacing:0.14em; text-align:center;
}
.p5 .pitch-attack{
  position:absolute; right:16px; top:14px;
  font-family:'JetBrains Mono',monospace; font-size:11px;
  color:var(--ink-3); letter-spacing:0.18em; text-transform:uppercase;
  display:flex; align-items:center; gap:8px;
}

/* ── P6 JOGADORES ── */
.p6 .players{
  margin:40px 56px 0; display:grid; grid-template-columns:1fr 1fr 1fr; gap:20px;
}
.p6 .player{
  background:var(--bg-2); padding:26px 22px;
  display:flex; flex-direction:column; gap:16px; min-height:520px;
}
.p6 .player .head{
  display:flex; justify-content:space-between; align-items:center;
  padding-bottom:14px; border-bottom:1px solid var(--line);
}
.p6 .player .pos{
  font-family:'JetBrains Mono',monospace; font-size:11px;
  color:var(--ink-3); text-transform:uppercase; letter-spacing:0.14em;
}
.p6 .player .num{
  font-family:'Archivo',sans-serif; font-weight:900; font-size:28px; line-height:1;
}
.p6 .player .num i{ font-style:normal; color:var(--ink-3); font-size:14px; font-weight:500; margin-right:4px; }
.p6 .player.l1 .num{ color:var(--red); }
.p6 .player.l2 .num{ color:var(--yellow); }
.p6 .player.l3 .num{ color:var(--ink-2); }
.p6 .player .name{
  font-family:'Archivo',sans-serif; font-weight:900;
  font-size:28px; line-height:1.1; letter-spacing:-0.01em; color:var(--ink);
}
.p6 .player .name em{
  font-style:normal; display:block; font-size:20px;
  font-weight:700; color:var(--ink-2); margin-top:4px;
}
.p6 .player .rating{
  padding:16px 0; margin:4px 0;
  border-top:1px solid var(--line); border-bottom:1px solid var(--line);
  display:flex; align-items:baseline; justify-content:space-between;
}
.p6 .player .rating .l{
  font-family:'JetBrains Mono',monospace; font-size:11px;
  color:var(--ink-3); text-transform:uppercase; letter-spacing:0.14em;
}
.p6 .player .rating .v{
  font-family:'Archivo',sans-serif; font-weight:900; font-size:42px; letter-spacing:-0.02em;
}
.p6 .player.l1 .rating .v{ color:var(--red); }
.p6 .player.l2 .rating .v{ color:var(--yellow); }
.p6 .player.l3 .rating .v{ color:var(--ink); }
.p6 .player .stats{ display:flex; flex-direction:column; gap:10px; margin-top:4px; }
.p6 .player .stat{
  display:flex; justify-content:space-between; align-items:baseline; padding:6px 0;
}
.p6 .player .stat .l{
  font-family:'JetBrains Mono',monospace; font-size:12px;
  color:var(--ink-2); text-transform:uppercase; letter-spacing:0.1em;
}
.p6 .player .stat .v{
  font-family:'Archivo',sans-serif; font-weight:700; font-size:24px; color:var(--ink); letter-spacing:-0.01em;
}
.p6 .player .role{
  margin-top:auto; padding-top:14px; border-top:1px solid var(--line);
  font-family:'JetBrains Mono',monospace; font-size:12px;
  color:var(--ink-2); text-transform:uppercase; letter-spacing:0.14em; line-height:1.5;
}
.p6 .player .role b{ color:var(--ink); font-weight:500; display:block; margin-bottom:2px; }
.p6 .player.l1 .role b{ color:var(--red); }
.p6 .player.l2 .role b{ color:var(--yellow); }
"""


# ─── Helpers de template HTML ─────────────────────────────────────────────────

def _b64_img(path: str) -> str:
    """Converte imagem local para data URI base64."""
    if not path or not os.path.exists(path):
        return ""
    ext = Path(path).suffix.lower().lstrip(".")
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext, "image/png")
    with open(path, "rb") as f:
        return f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"


def _shell(body_class: str, cap_meta_line1: str, cap_meta_line2: str,
           page_num: str, content_html: str,
           logo_b64: str) -> str:
    logo_tag = f'<img src="{logo_b64}" alt="canal"/>' if logo_b64 else \
               '<div style="width:56px;height:56px;border-radius:50%;background:var(--bg-3)"></div>'
    return f"""<!doctype html><html lang="pt-BR"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<style>{CSS}</style>
</head><body><div class="card {body_class}">
  <div class="cap">
    <div class="cap-brand">
      {logo_tag}
      <div class="wordmark">
        <div class="h">Sport Recife Lab</div>
        <div class="s">@SportRecifeLab</div>
      </div>
    </div>
    <div class="cap-meta">
      <div>{cap_meta_line1}</div>
      <div class="dim">{cap_meta_line2}</div>
    </div>
  </div>
  <div class="rule"></div>
  {content_html}
  <div class="foot">
    <div class="src">Fontes <b>SofaScore</b></div>
    <div class="pg"><span class="n">{page_num}</span><span class="t">/ 06</span></div>
  </div>
</div></body></html>"""


# ─── Templates por card ───────────────────────────────────────────────────────

def html_p1(d: dict, logo_b64: str, shield_b64: str) -> str:
    shield_tag = f'<img src="{shield_b64}" alt="{d["team_name"]}"/>' if shield_b64 else \
                 f'<div style="font-family:Archivo,sans-serif;font-weight:900;font-size:64px;color:var(--ink-2)">{d["team_abbr"]}</div>'
    kpis_html = "".join(
        f'<div class="kpi"><div class="l">{k}</div>'
        f'<div class="v {vc}">{v}<small>{vs}</small></div></div>'
        for k, v, vs, vc in d["kpis"]
    )
    content = f"""
    <div class="hero">
      <div class="kicker">Raio-X do adversário</div>
      <h1>RAIO<span class="x">·</span>X</h1>
      <h2>{d["team_name_hero"]}</h2>
      <div class="sub">{d["sub"]}</div>
    </div>
    <div class="body">
      <div class="badge-wrap">{shield_tag}</div>
      <div class="kpis">{kpis_html}</div>
    </div>"""
    return _shell("p1", d["comp_label"], d["round_label"], "01", content, logo_b64)


def html_p2(d: dict, logo_b64: str) -> str:
    w, e, l = d["wins"], d["draws"], d["losses"]
    total = w + e + l
    pct = round((w * 3 + e) / (total * 3) * 100) if total else 0
    rows_html = "".join(
        f'<div class="row">'
        f'<span class="tick" style="background:{color}"></span>'
        f'<span class="name">{name}</span>'
        f'<span class="bar"><i style="width:{bar_pct}%"></i></span>'
        f'<span class="n">{n}<small>jogos</small></span>'
        f'</div>'
        for name, n, bar_pct, color in d["comps"]
    )
    gf, ga = d["gf"], d["ga"]
    saldo = gf - ga
    saldo_str = f"−{abs(saldo)}" if saldo < 0 else (f"+{saldo}" if saldo > 0 else "0")
    content = f"""
    <div class="card-title-block">
      <div class="kicker">Campanha geral</div>
      <h1>{d["team_abbr"]} EM<br/><em>{total} JOGOS</em></h1>
      <div class="sub">{w*3+e} pontos · {pct}% de aproveitamento</div>
    </div>
    <div class="record">
      <div class="seg v" style="--f:{w}"><div><div class="n">{w}</div><div class="l">Vitórias</div></div></div>
      <div class="seg e" style="--f:{e}"><div><div class="n">{e}</div><div class="l">Empates</div></div></div>
      <div class="seg d" style="--f:{l}"><div><div class="n">{l}</div><div class="l">Derrotas</div></div></div>
    </div>
    <div class="stack">
      <div class="bar" style="flex:{w};background:var(--green)"></div>
      <div class="bar" style="flex:{e};background:var(--yellow)"></div>
      <div class="bar" style="flex:{l};background:var(--red)"></div>
    </div>
    <div class="goals">
      <div><div class="n for">{gf}</div><div class="l">Gols marcados</div></div>
      <div><div class="n {'neg' if saldo < 0 else 'for'}">{saldo_str}</div><div class="l">Saldo de gols</div></div>
      <div><div class="n for">{ga}</div><div class="l">Gols sofridos</div></div>
    </div>
    <div class="breakdown">
      <h3>Jogos por competição</h3>
      <div class="rows">{rows_html}</div>
    </div>"""
    return _shell("p2", "Temporada 2026", "Todas as competições", "02", content, logo_b64)


def html_p3(d: dict, logo_b64: str) -> str:
    def lines(items):
        return "".join(
            f'<div class="line"><span class="l">{lbl}</span><span class="v {vc}">{val}</span></div>'
            for lbl, val, vc in items
        )
    content = f"""
    <div class="card-title-block">
      <div class="kicker">Em casa</div>
      <h1>{d["team_abbr"]}<br/>EM <em>{d["city"].upper()}</em></h1>
      <div class="sub">{d["sub"]}</div>
    </div>
    <div class="big">
      <div class="num">{d["home_aprov"]}<small>%</small></div>
      <div class="caption">
        <b>Aproveitamento como mandante</b>
        {d["home_games"]} jogos em 2026 · {d["home_w"]}V · {d["home_d"]}E · {d["home_l"]}D
      </div>
    </div>
    <div class="split">
      <div class="col">
        <div class="head"><b>Geral em casa</b> · {d["home_games"]} jogos</div>
        {lines(d["home_general_lines"])}
      </div>
      <div class="col">
        <div class="head"><b>Série B em casa</b> · {d["sb_home_games"]} jogos</div>
        {lines(d["home_sb_lines"])}
      </div>
    </div>
    <div class="insight">
      <div class="k">Leitura tática</div>
      <div class="t">{d["insight_title"]}</div>
      <div class="s">{d["insight_body"]}</div>
    </div>"""
    return _shell("p3", "Como mandante", f"{d['stadium']} · 2026", "03", content, logo_b64)


def html_p4(d: dict, logo_b64: str) -> str:
    label_map = {"win": "V", "draw": "E", "loss": "D"}
    cls_map   = {"win": "v", "draw": "e", "loss": "d"}
    # Streak: oldest → newest (left to right)
    streak_items = d["last5"]  # list oldest→newest
    streak_html = "".join(
        f'<div class="s {cls_map[o]}">{label_map[o]}</div>'
        for o in streak_items
    )
    # Summary line (oldest date · mais antigo ... newest date · mais recente)
    oldest_date = d["matches"][-1]["date"]
    newest_date = d["matches"][0]["date"]
    matches_html = ""
    for m in d["matches"]:  # newest first
        home_cls = "home me" if m["is_am_home"] else "home"
        away_cls = "me" if not m["is_am_home"] else ""
        chip_cls = cls_map[m["outcome"]]
        chip_lbl = label_map[m["outcome"]]
        matches_html += f"""
        <div class="match">
          <div class="date"><div class="d">{m["date"]}</div><div class="c">{m["comp"]}</div></div>
          <div class="team {home_cls}">{m["home"]}</div>
          <div class="score">{m["hs"]}<span class="x">–</span>{m["as_"]}</div>
          <div class="team {away_cls}">{m["away"]}</div>
          <div class="chip {chip_cls}">{chip_lbl}</div>
        </div>"""
    w5 = streak_items.count("win")
    e5 = streak_items.count("draw")
    l5 = streak_items.count("loss")
    content = f"""
    <div class="card-title-block">
      <div class="kicker">Forma recente</div>
      <h1>{w5}<em>V</em> · {e5}<em>E</em> · {l5}<em>D</em></h1>
      <div class="sub">{d["form_sub"]}</div>
    </div>
    <div class="streak">{streak_html}</div>
    <div class="streak-meta">
      <span>{oldest_date} · mais antigo</span>
      <span>{newest_date} · mais recente →</span>
    </div>
    <div class="matches">{matches_html}</div>"""
    return _shell("p4", "Forma recente", "Últimos 5 jogos", "04", content, logo_b64)


def html_p5(d: dict, logo_b64: str) -> str:
    zones = d["zones"]  # list of (label, pct, is_center)
    zones_html = ""
    for label, pct, is_center in zones:
        if is_center:
            fill_color = "rgba(230,57,70,0.85)"
            pct_style  = 'style="color:#fff"'
            pct_u_style = 'style="font-size:28px;color:rgba(255,255,255,0.7)"'
            lab_style   = 'style="color:rgba(255,255,255,0.9)"'
        else:
            fill_color = "rgba(184,180,171,0.22)"
            pct_style  = ""
            pct_u_style = 'style="font-size:28px;color:var(--ink-3)"'
            lab_style   = ""
        zones_html += f"""
        <div class="zone">
          <div class="fill" style="--zone:{fill_color};height:{pct}%"></div>
          <div class="pct" {pct_style}>{pct}<span {pct_u_style}>%</span></div>
          <div class="lab" {lab_style}>{label}</div>
        </div>"""
    metrics_html = "".join(
        f'<div class="m"><div class="n">{v}<span class="u">{u}</span></div>'
        f'<div class="l">{lbl}</div><div class="t">{sub}</div></div>'
        for v, u, lbl, sub in d["metrics"]
    )
    content = f"""
    <div class="card-title-block">
      <div class="kicker">Posse × finalização</div>
      <h1>DOMINA A BOLA,<br/><em>{d["title_em"]}</em></h1>
    </div>
    <div class="metrics">{metrics_html}</div>
    <div class="thesis">
      <div class="k">Leitura</div>
      <h3>{d["thesis_h3"]}</h3>
      <p>{d["thesis_p"]}</p>
    </div>
    <div class="pitch-block">
      <div class="h">
        <div class="t">Zonas de finalização</div>
        <div class="s">{d["zones_sub"]}</div>
      </div>
      <div class="pitch">
        <div class="pitch-attack">Ataque</div>
        {zones_html}
      </div>
      <div class="pitch-ruler">
        <div>Flanco esquerdo</div><div>Corredor central</div><div>Flanco direito</div>
      </div>
    </div>"""
    return _shell("p5", "Análise ofensiva", d["meta_sub"], "05", content, logo_b64)


def html_p6(d: dict, logo_b64: str) -> str:
    players_html = ""
    for i, p in enumerate(d["players"], 1):
        stats_html = "".join(
            f'<div class="stat"><span class="l">{sl}</span><span class="v">{sv}</span></div>'
            for sl, sv in p["stats"]
        )
        players_html += f"""
        <div class="player l{i}">
          <div class="head">
            <span class="pos">{p["pos"]}</span>
            <span class="num"><i>#</i>{p["jersey"]}</span>
          </div>
          <div class="name">{p["first_name"]}<em>{p["last_name"]}</em></div>
          <div class="rating">
            <span class="l">Rating<br/>médio</span>
            <span class="v">{p["rating"]}</span>
          </div>
          <div class="stats">{stats_html}</div>
          <div class="role"><b>{p["role_title"]}</b>{p["role_body"]}</div>
        </div>"""
    content = f"""
    <div class="card-title-block">
      <div class="kicker">Jogadores para observar</div>
      <h1>TRÊS<br/>NOMES <em>{d["subtitle_em"]}</em></h1>
      <div class="sub">{d["sub"]}</div>
    </div>
    <div class="players">{players_html}</div>"""
    return _shell("p6", "Fique de olho", "Destaques Série B", "06", content, logo_b64)


# ─── Renderer Selenium ────────────────────────────────────────────────────────

def _render_html_to_png(html: str, output_path: str,
                        width: int = 1080, height: int = 1350,
                        wait_fonts_ms: int = 2500):
    """Renderiza HTML como string → PNG via Selenium Edge headless."""
    if not HAS_SELENIUM:
        raise RuntimeError("Selenium não instalado")

    opts = EdgeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument(f"--window-size={width},{height}")
    opts.add_argument("--hide-scrollbars")
    opts.add_argument("--force-device-scale-factor=1")
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])

    driver = webdriver.Edge(options=opts)
    try:
        # Salva HTML temporário e navega via file://
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False,
                                        mode="w", encoding="utf-8") as tmp:
            tmp.write(html)
            tmp_path = tmp.name

        driver.get(f"file:///{tmp_path.replace(os.sep, '/')}")

        # Aguarda Google Fonts + render
        driver.execute_script(
            "return document.fonts.ready"
        )
        time.sleep(wait_fonts_ms / 1000)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        driver.save_screenshot(output_path)
        print(f"  OK {output_path}")
    finally:
        driver.quit()
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ─── Classe principal ─────────────────────────────────────────────────────────

class RaioXCards:
    """
    Gera os 6 cards Raio-X v2 para qualquer adversário.

    Parâmetros
    ----------
    data : dict
        Dicionário com todos os dados do adversário (ver DATA_AMERICA_MG abaixo).
    out_dir : str
        Pasta de saída dos PNGs.
    logo_path : str
        Caminho para o logo do @SportRecifeLab (canal).
    shield_path : str
        Caminho para o escudo do adversário.
    """

    def __init__(self, data: dict, out_dir: str,
                 logo_path: str = "sportrecifelab_avatar.png",
                 shield_path: str = ""):
        self.d = data
        self.out_dir = out_dir
        self.logo_b64   = _b64_img(logo_path)
        self.shield_b64 = _b64_img(shield_path)

    def render_all(self):
        os.makedirs(self.out_dir, exist_ok=True)
        cards = [
            ("01_cover.png",    html_p1(self.d["p1"], self.logo_b64, self.shield_b64)),
            ("02_campanha.png", html_p2(self.d["p2"], self.logo_b64)),
            ("03_mandante.png", html_p3(self.d["p3"], self.logo_b64)),
            ("04_ultimos5.png", html_p4(self.d["p4"], self.logo_b64)),
            ("05_xg.png",       html_p5(self.d["p5"], self.logo_b64)),
            ("06_jogadores.png",html_p6(self.d["p6"], self.logo_b64)),
        ]
        for fname, html in cards:
            _render_html_to_png(html, os.path.join(self.out_dir, fname))
        print(f"\nPronto. Cards em: {self.out_dir}")


# ─── Dados América Mineiro R5 ─────────────────────────────────────────────────

DATA_AMERICA_MG = {
    "p1": {
        "team_name": "América Mineiro",
        "team_name_hero": "AMÉRICA<br/>MINEIRO",
        "team_abbr": "COELHO",
        "comp_label": "Série B 2026",
        "round_label": "Rodada 05 · 18.04",
        "sub": "Sport visita o Independência — o que esperar do Coelho",
        "kpis": [
            ("Posição · Série B",  "20º", "/ 1pt", "danger"),
            ("Campanha na Série B","0", "V  1E  3D",  ""),
            ("Posse média",        "67", "%",          ""),
            ("xG gerado / jogo",   "1.64","",          "ok"),
        ],
    },
    "p2": {
        "team_abbr": "COELHO",
        "wins": 6, "draws": 7, "losses": 7,
        "gf": 31, "ga": 35,
        "comps": [
            ("Mineiro Módulo I", 11, 100,   "var(--yellow)"),
            ("Copa Sul-Sudeste", 4,  36.4,  "var(--ink-2)"),
            ("Série B",          4,  36.4,  "var(--ink-2)"),
            ("Copa do Brasil",   3,  27.3,  "var(--ink-2)"),
        ],
    },
    "p3": {
        "team_abbr": "COELHO",
        "city": "Belo Horizonte",
        "stadium": "Independência",
        "sub": "Sport visita o Independência — como o Coelho se sai em casa?",
        "home_aprov": 53,
        "home_games": 10,
        "home_w": 5, "home_d": 1, "home_l": 4,
        "home_general_lines": [
            ("Vitórias",      "5",  "ok"),
            ("Empates",       "1",  "acc"),
            ("Derrotas",      "4",  "warn"),
            ("Gols marcados", "18", ""),
            ("Gols sofridos", "18", ""),
            ("Saldo",         "0",  ""),
        ],
        "sb_home_games": 2,
        "home_sb_lines": [
            ("Vitórias",      "0",    ""),
            ("Empates",       "0",    ""),
            ("Derrotas",      "2",    "warn"),
            ("Gols marcados", "1",    ""),
            ("Gols sofridos", "5",    "warn"),
            ("xG médio",      "0.60", ""),
        ],
        "insight_title": "Em casa pela Série B, o América não venceu — e sofreu 5 gols em 2 jogos.",
        "insight_body": "Domina a posse (67%) mas não converte. Padrão vulnerável a contra-ataques diretos, com linha defensiva alta e transições lentas.",
    },
    "p4": {
        "last5": ["loss", "draw", "draw", "loss", "win"],  # oldest→newest
        "form_sub": "Apenas uma vitória — e zero vitórias na Série B desde o início",
        "matches": [
            {"date":"15/04","comp":"Copa Sul-Sud.","home":"América-MG","hs":2,"as_":1,"away":"Sampaio Corrêa","is_am_home":True, "outcome":"win"},
            {"date":"12/04","comp":"Série B · R4", "home":"América-MG","hs":0,"as_":3,"away":"Grêmio Nov.",   "is_am_home":True, "outcome":"loss"},
            {"date":"09/04","comp":"Copa Sul-Sud.","home":"Tombense",  "hs":3,"as_":3,"away":"América-MG",   "is_am_home":False,"outcome":"draw"},
            {"date":"05/04","comp":"Série B · R3", "home":"Athletic Club","hs":1,"as_":1,"away":"América-MG","is_am_home":False,"outcome":"draw"},
            {"date":"01/04","comp":"Série B · R2", "home":"América-MG","hs":1,"as_":2,"away":"Botafogo-SP",  "is_am_home":True, "outcome":"loss"},
        ],
    },
    "p5": {
        "title_em": "NÃO VENCE",
        "metrics": [
            ("67", "%",   "Posse média",    "domina o meio"),
            ("1.64","",   "xG / jogo",      "cria, não finaliza"),
            ("19.3","",   "Chutes / jogo",  "volume alto"),
        ],
        "thesis_h3": '67% de posse e 1.64 xG/jogo —<br/>mas <em>0 vitórias e 9 gols sofridos</em> na Série B.',
        "thesis_p": "Equipe cria pela posse, mas é vulnerável ao ritmo adversário: transições rápidas nas laterais e contra-ataques diretos exploram a linha alta.",
        "zones": [
            ("Esquerda", 10, False),
            ("Centro",   79, True),
            ("Direita",  11, False),
        ],
        "zones_sub": "16 jogos · SofaScore",
        "meta_sub": "Série B 2026 · 4 jogos",
    },
    "p6": {
        "subtitle_em": "DO COELHO",
        "sub": "Ratings médios · Brasileirão Série B · 4 jogos",
        "players": [
            {
                "pos": "Centroavante", "jersey": "9",
                "first_name": "Gonzalo", "last_name": "Mastriani",
                "rating": "7.22",
                "stats": [("Jogos","4"), ("Chutes","8"), ("Minutos","360'")],
                "role_title": "Principal finalizador",
                "role_body": "Referência no ataque, pivô no centro",
            },
            {
                "pos": "Meia-atacante", "jersey": "10",
                "first_name": "Felipe", "last_name": "Amaral",
                "rating": "6.93",
                "stats": [("Jogos","4"), ("Chutes","8"), ("Minutos","295'")],
                "role_title": "Criação pelo centro",
                "role_body": "Conecta meio e ataque, chega à área",
            },
            {
                "pos": "Goleiro", "jersey": "1",
                "first_name": "Gustavo", "last_name": "Ramalho",
                "rating": "6.90",
                "stats": [("Jogos","4"), ("Defesas","14"), ("Minutos","360'")],
                "role_title": "Linha de defesa",
                "role_body": "Sustenta uma zaga exposta, volume alto de defesas",
            },
        ],
    },
}


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera cards Raio-X v2")
    parser.add_argument("--team-key", default="america-mg")
    parser.add_argument("--round",    default="5")
    parser.add_argument("--date",     default="2026-04-18")
    args = parser.parse_args()

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    out = f"pending_posts/{args.date}_raio-x-{args.team_key}-v2"
    shield = f"data/cache/logos/1973.png"  # América Mineiro

    print(f"Gerando Raio-X v2 — {args.team_key} | Série B 2026 R{args.round}")
    cards = RaioXCards(
        data=DATA_AMERICA_MG,
        out_dir=out,
        logo_path="sportrecifelab_avatar.png",
        shield_path=shield,
    )
    cards.render_all()
