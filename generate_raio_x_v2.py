"""
Gerador de cards Raio-X v2 — design system editorial.

Renderiza HTML/CSS via Selenium Edge headless -> PNG 1080x1350 (portrait 4:5).
Dados carregados automaticamente dos CSVs curados do pipeline.

Uso:
  python -X utf8 generate_raio_x_v2.py \
    --team-key novorizontino \
    --team-name "Gremio Novorizontino" \
    --team-abbr "NOVORIZONTINO" \
    --team-id 135514 \
    --round 6 \
    --season 2026 \
    --date 2026-04-25 \
    --sport-role mandante \
    [--city "Recife"] [--stadium "Ilha do Retiro"]
"""

import os
import sys
import time
import base64
import tempfile
import argparse
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from selenium import webdriver
    from selenium.webdriver.edge.options import Options as EdgeOptions
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False

try:
    from generate_como_joga_html import build_html as _cj_html, render_to_png as _cj_png
    _HAS_CJ = True
except ImportError:
    _HAS_CJ = False


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
    # suporta mandante (sport_role=visitante) e visitante (sport_role=mandante)
    is_home_context = d.get("is_home_context", True)
    if is_home_context:
        kicker = "Em casa"
        cap_meta1 = "Como mandante"
        h1_line2 = f'EM <em>{d["city"].upper()}</em>'
        aprov_label = "Aproveitamento como mandante"
        col1_head = f'Geral em casa · {d["ctx_games"]} jogos'
        col2_head = f'Série B em casa · {d["sb_ctx_games"]} jogos'
    else:
        kicker = "Como visitante"
        cap_meta1 = "Como visitante"
        h1_line2 = f'<em>COMO VISITANTE</em>'
        aprov_label = "Aproveitamento como visitante"
        col1_head = f'Geral fora de casa · {d["ctx_games"]} jogos'
        col2_head = f'Série B fora de casa · {d["sb_ctx_games"]} jogos'

    content = f"""
    <div class="card-title-block">
      <div class="kicker">{kicker}</div>
      <h1>{d["team_abbr"]}<br/>{h1_line2}</h1>
      <div class="sub">{d["sub"]}</div>
    </div>
    <div class="big">
      <div class="num">{d["ctx_aprov"]}<small>%</small></div>
      <div class="caption">
        <b>{aprov_label}</b>
        {d["ctx_games"]} jogos em 2026 · {d["ctx_w"]}V · {d["ctx_d"]}E · {d["ctx_l"]}D
      </div>
    </div>
    <div class="split">
      <div class="col">
        <div class="head"><b>{col1_head}</b></div>
        {lines(d["ctx_general_lines"])}
      </div>
      <div class="col">
        <div class="head"><b>{col2_head}</b></div>
        {lines(d["ctx_sb_lines"])}
      </div>
    </div>
    <div class="insight">
      <div class="k">Leitura tatica</div>
      <div class="t">{d["insight_title"]}</div>
      <div class="s">{d["insight_body"]}</div>
    </div>"""
    return _shell("p3", cap_meta1, f"{d['stadium']} · 2026", "03", content, logo_b64)


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
    zones = d.get("zones") or []
    zones_html = ""
    for label, pct, is_center in zones:
        if is_center:
            fill_color = "rgba(230,57,70,0.85)"
            pct_style   = 'style="color:#fff"'
            pct_u_style = 'style="font-size:28px;color:rgba(255,255,255,0.7)"'
            lab_style   = 'style="color:rgba(255,255,255,0.9)"'
        else:
            fill_color  = "rgba(184,180,171,0.22)"
            pct_style   = ""
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

    pitch_block = ""
    if zones_html:
        pitch_block = f"""
    <div class="pitch-block">
      <div class="h">
        <div class="t">Zonas de finalizacao</div>
        <div class="s">{d.get("zones_sub", "")}</div>
      </div>
      <div class="pitch">
        <div class="pitch-attack">Ataque</div>
        {zones_html}
      </div>
      <div class="pitch-ruler">
        <div>Flanco esquerdo</div><div>Corredor central</div><div>Flanco direito</div>
      </div>
    </div>"""

    content = f"""
    <div class="card-title-block">
      <div class="kicker">Posse x finalizacao</div>
      <h1>{d["title_line1"]},<br/><em>{d["title_em"]}</em></h1>
    </div>
    <div class="metrics">{metrics_html}</div>
    <div class="thesis">
      <div class="k">Leitura</div>
      <h3>{d["thesis_h3"]}</h3>
      <p>{d["thesis_p"]}</p>
    </div>
    {pitch_block}"""
    return _shell("p5", "Analise ofensiva", d["meta_sub"], "05", content, logo_b64)


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
                 cfg: dict = None,
                 logo_path: str = "sportrecifelab_avatar.png",
                 shield_path: str = ""):
        self.d = data
        self.out_dir = out_dir
        self.cfg = cfg or {}
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

        # Cards 07 e 08 — Como Joga (landscape 1200×675, design Barlow Condensed)
        if _HAS_CJ and self.cfg:
            tk   = self.cfg.get("team_key", "")
            tn   = self.d["p1"]["team_name"]
            tid  = int(self.cfg.get("team_id", 0))
            rnd  = self.cfg.get("round", 0)
            comp = self.cfg.get("comp_name", "Série B 2026")
            try:
                date_cj = datetime.strptime(self.cfg["date"], "%Y-%m-%d").strftime("%d/%m")
            except Exception:
                date_cj = self.cfg.get("date", "")[:5]
            for mode, fname in [(False, "07_como_joga.png"), (True, "08_como_marca_gols.png")]:
                try:
                    html = _cj_html(tk, tn, tid, rnd, date_cj, comp, mode)
                    out_path = Path(self.out_dir) / fname
                    _cj_png(html, out_path)
                    print(f"  OK {fname}")
                except FileNotFoundError:
                    print(f"  SKIP {fname} — attack_profile ou team_heatmap ausente (rode sync-attack-map primeiro)")
                except Exception as e:
                    print(f"  WARN {fname} — {e}")

        print(f"\nPronto. Cards em: {self.out_dir}")


# ─── Computação automática de dados dos CSVs ─────────────────────────────────

def _load(team_key: str):
    base = f"data/curated/opponents_2026/{team_key}"
    m = pd.read_csv(f"{base}/matches.csv")
    s = pd.read_csv(f"{base}/team_match_stats.csv")
    try:
        p = pd.read_csv(f"{base}/player_match_stats.csv")
    except FileNotFoundError:
        p = None
    return m, s, p


def _enrich(matches: pd.DataFrame, stats: pd.DataFrame):
    done = matches[matches["status"] == "completed"].copy()
    done["gf"] = np.where(done["is_home_team"], done["home_score"], done["away_score"])
    done["ga"] = np.where(done["is_home_team"], done["away_score"], done["home_score"])
    done["_outcome"] = np.where(
        done["gf"] > done["ga"], "win",
        np.where(done["gf"] == done["ga"], "draw", "loss")
    )
    joined = stats.merge(
        done[["match_code", "is_home_team"]].rename(columns={"match_code": "match_id"}),
        on="match_id", how="inner"
    )
    own = joined[joined["is_home"] == joined["is_home_team"]]
    opp = joined[joined["is_home"] != joined["is_home_team"]]
    return done, joined, own, opp


def _record(df):
    if df.empty:
        return {"w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "n": 0}
    return {
        "w":  int((df["_outcome"] == "win").sum()),
        "d":  int((df["_outcome"] == "draw").sum()),
        "l":  int((df["_outcome"] == "loss").sum()),
        "gf": int(df["gf"].sum()),
        "ga": int(df["ga"].sum()),
        "n":  len(df),
    }


def _aprov(rec):
    return round((rec["w"] * 3 + rec["d"]) / (rec["n"] * 3) * 100) if rec["n"] else 0


def _sb_filter(done: pd.DataFrame):
    return done[done["competition_name"].str.contains(
        "Serie B|Série B|Brasileir", case=False, na=False
    )]


def _stat_lines(rec, xg_avg=None):
    saldo = rec["gf"] - rec["ga"]
    saldo_str = f"+{saldo}" if saldo > 0 else str(saldo)
    rows = [
        ("Vitorias",      str(rec["w"]),  "ok"   if rec["w"] >= 3 else ""),
        ("Empates",       str(rec["d"]),  "acc"),
        ("Derrotas",      str(rec["l"]),  "warn" if rec["l"] >= 3 else ""),
        ("Gols marcados", str(rec["gf"]), ""),
        ("Gols sofridos", str(rec["ga"]), "warn" if rec["ga"] > rec["gf"] else ""),
        ("Saldo",         saldo_str,      "ok" if saldo > 0 else ("warn" if saldo < 0 else "")),
    ]
    if xg_avg is not None:
        rows.append(("xG medio", f"{xg_avg:.2f}", ""))
    return rows


def build_data(cfg: dict, matches, stats, players_df) -> dict:
    done, joined, own, opp = _enrich(matches, stats)
    sb = _sb_filter(done)

    # ── Totais ──────────────────────────────────────────────────────────────────
    total_rec = _record(done)
    home_done = done[done["is_home_team"]]
    away_done = done[~done["is_home_team"]]
    home_rec  = _record(home_done)
    away_rec  = _record(away_done)
    sb_rec    = _record(sb)

    sb_home = sb[sb["is_home_team"]]
    sb_away = sb[~sb["is_home_team"]]
    sb_home_rec = _record(sb_home)
    sb_away_rec = _record(sb_away)

    # ── Stats de time ───────────────────────────────────────────────────────────
    xg_avg   = own["expected_goals"].mean() if not own.empty else 0
    xga_avg  = opp["expected_goals"].mean() if not opp.empty else 0
    poss_avg = own["possession"].mean()      if not own.empty else 50
    shots_avg = own["shots_total"].mean()    if not own.empty else 0

    sb_own = joined[
        joined["match_id"].isin(sb["match_code"]) &
        (joined["is_home"] == joined["is_home_team"])
    ]
    sb_xg = sb_own["expected_goals"].mean() if not sb_own.empty else xg_avg
    sb_shots = sb_own["shots_total"].mean() if not sb_own.empty else shots_avg

    # ── Contexto mandante/visitante ──────────────────────────────────────────
    sport_role = cfg["sport_role"]   # "mandante" ou "visitante"
    # Se Sport é visitante → oponente é mandante → mostrar stats de CASA do oponente
    is_home_context = (sport_role == "visitante")
    ctx_done    = home_done if is_home_context else away_done
    ctx_rec     = home_rec  if is_home_context else away_rec
    ctx_sb_done = sb_home   if is_home_context else sb_away
    ctx_sb_rec  = sb_home_rec if is_home_context else sb_away_rec

    ctx_own = joined[
        (joined["match_id"].isin(ctx_done["match_code"])) &
        (joined["is_home"] == joined["is_home_team"])
    ]
    ctx_xg   = ctx_own["expected_goals"].mean() if not ctx_own.empty else xg_avg
    ctx_xga  = joined[
        (joined["match_id"].isin(ctx_done["match_code"])) &
        (joined["is_home"] != joined["is_home_team"])
    ]["expected_goals"].mean() if not ctx_own.empty else xga_avg
    ctx_poss = ctx_own["possession"].mean() if not ctx_own.empty else poss_avg

    ctx_sb_own = joined[
        (joined["match_id"].isin(ctx_sb_done["match_code"])) &
        (joined["is_home"] == joined["is_home_team"])
    ]
    ctx_sb_xg = ctx_sb_own["expected_goals"].mean() if not ctx_sb_own.empty else sb_xg

    # ── Últimos 5 ────────────────────────────────────────────────────────────
    done["_date_parsed"] = pd.to_datetime(done["match_date_utc"], utc=True)
    done_sorted = done.sort_values("_date_parsed", ascending=False).head(5)
    last5_outcomes = list(reversed(done_sorted["_outcome"].tolist()))  # oldest→newest

    matches_p4 = []
    for _, r in done_sorted.iterrows():
        matches_p4.append({
            "date":      pd.to_datetime(r["match_date_utc"], utc=True).strftime("%d/%m"),
            "comp":      str(r["competition_name"]).split(",")[0][:16],
            "home":      r["home_team"],
            "hs":        int(r["home_score"]) if pd.notna(r["home_score"]) else 0,
            "as_":       int(r["away_score"]) if pd.notna(r["away_score"]) else 0,
            "away":      r["away_team"],
            "is_am_home": bool(r["is_home_team"]),
            "outcome":   r["_outcome"],
        })

    # ── Players (Série B) ─────────────────────────────────────────────────────
    p6_players = []
    if players_df is not None and not players_df.empty:
        sb_match_codes = set(sb["match_code"].tolist())
        pj = players_df[players_df["match_code"].isin(sb_match_codes)].copy()
        # Flag oponente: is_home == is_home_team em matches
        hm = matches[["match_code", "is_home_team"]]
        pj = pj.merge(hm, on="match_code", how="left")
        own_p = pj[pj["is_home"] == pj["is_home_team"]]
        if not own_p.empty:
            agg = own_p.groupby(
                ["player_id", "player_name", "position", "jersey_number"]
            ).agg(
                apps=("minutes_played", "count"),
                minutes=("minutes_played", "sum"),
                rating=("rating", "mean"),
                shots=("total_shots", "sum"),
                assists=("goal_assist", "sum"),
                saves=("saves", "sum"),
            ).reset_index()
            agg = agg[agg["apps"] >= 1].sort_values("rating", ascending=False)

            pos_label = {"G": "Goleiro", "D": "Defensor", "M": "Meia", "F": "Atacante"}
            role_map  = {
                "G": ("Goleiro titular",      "Ultima linha de defesa"),
                "D": ("Muro defensivo",       "Solidez na retaguarda"),
                "M": ("Motor do meio",        "Distribui e progride"),
                "F": ("Principal finalizador","Referencia no ataque"),
            }
            colors_i = ["red", "yellow", "ink-2"]

            for _, row in agg.head(3).iterrows():
                parts     = str(row["player_name"]).split()
                first     = parts[0] if parts else "?"
                last      = " ".join(parts[1:]) if len(parts) > 1 else ""
                pos       = str(row["position"])
                role_t, role_b = role_map.get(pos, ("Destaque da temporada", ""))

                stat_list = [("Jogos", str(int(row["apps"])))]
                if pos == "G" and row["saves"] > 0:
                    stat_list.append(("Defesas", str(int(row["saves"]))))
                elif row["assists"] > 0:
                    stat_list.append(("Assistencias", str(int(row["assists"]))))
                elif row["shots"] > 0:
                    stat_list.append(("Chutes", str(int(row["shots"]))))
                stat_list.append(("Minutos", f"{int(row['minutes'])}'"))

                p6_players.append({
                    "pos":        pos_label.get(pos, pos),
                    "jersey":     str(int(row["jersey_number"])) if pd.notna(row["jersey_number"]) else "?",
                    "first_name": first,
                    "last_name":  last,
                    "rating":     f"{row['rating']:.2f}",
                    "stats":      stat_list,
                    "role_title": role_t,
                    "role_body":  role_b,
                })

    # ── Narrativa xG (p5) ────────────────────────────────────────────────────
    if poss_avg >= 55 and xg_avg < 1.3:
        title_line1 = "DOMINA A BOLA"
        title_em    = "NAO VENCE"
        thesis_h3   = (f"{poss_avg:.0f}% de posse e {xg_avg:.2f} xG/jogo — "
                       f"<br/>mas sofre <em>{total_rec['ga']} gols em {total_rec['n']} jogos</em>.")
        thesis_p    = ("Equipe circula mas cria pouco. Transicoes rapidas e pressao direta "
                       "podem explorar os espacos deixados pela linha alta.")
    elif xg_avg >= 1.6:
        title_line1 = "OFENSIVAMENTE"
        title_em    = "PERIGOSO"
        thesis_h3   = (f"{xg_avg:.2f} xG por jogo — "
                       f"<br/>saldo positivo de <em>+{total_rec['gf'] - total_rec['ga']} gols</em>.")
        thesis_p    = ("Time com volume e eficiencia ofensiva. Sport devera ser solido "
                       "defensivamente e aproveitar os contra-ataques.")
    else:
        diff_str = (f"+{xg_avg - xga_avg:.2f}" if xg_avg >= xga_avg
                    else f"{xg_avg - xga_avg:.2f}")
        title_line1 = "EQUILIBRADO"
        title_em    = "NAS METRICAS"
        thesis_h3   = (f"{xg_avg:.2f} xG gerado vs {xga_avg:.2f} xG cedido —"
                       f"<br/>saldo de <em>{diff_str}</em> xG por jogo.")
        thesis_p    = ("Equipe sem desequilibrio gritante. A qualidade do dia pode "
                       "ser o fator decisivo no confronto.")

    # ── Narrativa p3 insight ──────────────────────────────────────────────────
    ctx_label = "mandante" if is_home_context else "visitante"
    if ctx_rec["n"] == 0:
        insight_title = "Dados insuficientes para esta analise."
        insight_body  = "Adversario ainda nao disputou partidas neste contexto em 2026."
    elif ctx_xga > 1.4:
        insight_title = f"Defensivamente vulneravel como {ctx_label}."
        insight_body  = (f"Cede {ctx_xga:.2f} xG por jogo neste contexto — "
                         "pressao alta pode ser eficaz.")
    elif ctx_rec["w"] >= ctx_rec["n"] * 0.6:
        insight_title = f"Forte como {ctx_label} — aproveitamento acima de 60%."
        insight_body  = (f"{ctx_rec['w']}V em {ctx_rec['n']} jogos. "
                         "Sport precisara ser eficiente para romper a solidez.")
    else:
        total_goals = ctx_rec["gf"] + ctx_rec["ga"]
        avg_g = total_goals / ctx_rec["n"] if ctx_rec["n"] else 0
        insight_title = f"Media de {avg_g:.1f} gols por jogo como {ctx_label}."
        insight_body  = "Jogo tende a ser movimentado com chancas para os dois lados."

    # ── Comps breakdown (p2) ──────────────────────────────────────────────────
    comp_counts = (done.groupby("competition_name").size()
                   .sort_values(ascending=False).head(4))
    max_n = comp_counts.max() if len(comp_counts) else 1
    comps_data = [
        (name, int(n), round(n / max_n * 100), "var(--yellow)" if i == 0 else "var(--ink-2)")
        for i, (name, n) in enumerate(comp_counts.items())
    ]

    # ── KPIs (p1) ─────────────────────────────────────────────────────────────
    sb_aprov = _aprov(sb_rec)
    kpis = [
        ("Serie B 2026",
         f"{sb_rec['w']}V {sb_rec['d']}E {sb_rec['l']}D",
         f"/ {sb_rec['w']*3+sb_rec['d']}pt",
         "warn" if sb_rec["w"] == 0 else ""),
        ("Aproveitamento geral",
         str(_aprov(total_rec)), "%",
         "ok" if _aprov(total_rec) >= 60 else ""),
        ("Posse media",
         f"{poss_avg:.0f}", "%", ""),
        ("xG gerado / jogo",
         f"{xg_avg:.2f}", "",
         "ok" if xg_avg >= 1.5 else ("warn" if xg_avg < 1.0 else "")),
    ]

    # ── Monta data dict completo ──────────────────────────────────────────────
    team_abbr = cfg["team_abbr"]
    team_name = cfg["team_name"]
    sport_role_label = "visitante" if sport_role == "visitante" else "mandante"
    date_fmt  = cfg.get("date", "")
    try:
        date_fmt = datetime.strptime(date_fmt, "%Y-%m-%d").strftime("%d.%m")
    except Exception:
        pass

    city    = cfg.get("city", "")
    stadium = cfg.get("stadium", "")

    sub_p1 = (f"Sport recebe o adversario em casa — o que esperar do {team_abbr}"
              if sport_role == "mandante"
              else f"Sport visita o {team_abbr} — o que esperar do adversario")

    sub_p3 = (f"Sport recebe o adversario — como o {team_abbr} se sai como visitante?"
              if sport_role == "mandante"
              else f"Sport visita o {team_abbr} — como ele se sai em casa?")

    # Série B ctx lines
    ctx_sb_lines_data = _stat_lines(ctx_sb_rec, ctx_sb_xg)

    w5 = last5_outcomes.count("win")
    e5 = last5_outcomes.count("draw")
    l5 = last5_outcomes.count("loss")
    form_sub = (
        f"{w5} vitorias, {e5} empates e {l5} derrota(s) nos ultimos 5 jogos"
    )

    return {
        "p1": {
            "team_name": team_name,
            "team_name_hero": team_abbr,
            "team_abbr": team_abbr,
            "comp_label": "Serie B 2026",
            "round_label": f"Rodada {cfg['round']:02d} · {date_fmt}",
            "sub": sub_p1,
            "kpis": kpis,
        },
        "p2": {
            "team_abbr": team_abbr,
            "wins": total_rec["w"], "draws": total_rec["d"], "losses": total_rec["l"],
            "gf": total_rec["gf"], "ga": total_rec["ga"],
            "comps": comps_data,
        },
        "p3": {
            "team_abbr":  team_abbr,
            "city":       city or "Recife",
            "stadium":    stadium or "Ilha do Retiro",
            "sub":        sub_p3,
            "is_home_context": is_home_context,
            "ctx_aprov":  _aprov(ctx_rec),
            "ctx_games":  ctx_rec["n"],
            "ctx_w":      ctx_rec["w"],
            "ctx_d":      ctx_rec["d"],
            "ctx_l":      ctx_rec["l"],
            "ctx_general_lines": _stat_lines(ctx_rec, ctx_xg),
            "sb_ctx_games":  ctx_sb_rec["n"],
            "ctx_sb_lines":  ctx_sb_lines_data,
            "insight_title": insight_title,
            "insight_body":  insight_body,
        },
        "p4": {
            "last5": last5_outcomes,
            "form_sub": form_sub,
            "matches": matches_p4,
        },
        "p5": {
            "title_line1": title_line1,
            "title_em":    title_em,
            "metrics": [
                (f"{poss_avg:.0f}", "%",  "Posse media",   "controla o jogo" if poss_avg >= 52 else "disputa equilibrada"),
                (f"{xg_avg:.2f}",  "",   "xG / jogo",     "eficiente" if xg_avg >= 1.5 else "baixa criacao"),
                (f"{shots_avg:.1f}","",  "Chutes / jogo", "volume alto" if shots_avg >= 14 else "volume medio"),
            ],
            "thesis_h3": thesis_h3,
            "thesis_p":  thesis_p,
            "zones":     None,   # preencher manualmente se sync-attack-map foi rodado
            "zones_sub": f"{len(sb)} jogos Serie B · SofaScore",
            "meta_sub":  f"Serie B 2026 · {len(sb)} jogos",
        },
        "p6": {
            "subtitle_em": f"DO {team_abbr.split()[0]}",
            "sub": f"Ratings medios · Brasileirao Serie B · {len(sb)} jogos",
            "players": p6_players,
        },
    }


# ─── Dados América Mineiro R5 (mantido como referência / fallback) ────────────

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
    parser.add_argument("--team-key",   required=True, help="Ex: novorizontino")
    parser.add_argument("--team-name",  required=True, help="Ex: 'Gremio Novorizontino'")
    parser.add_argument("--team-abbr",  required=True, help="Ex: NOVORIZONTINO")
    parser.add_argument("--team-id",    required=True, help="SofaScore team_id, ex: 135514")
    parser.add_argument("--round",      required=True, type=int, help="Rodada, ex: 6")
    parser.add_argument("--season",     default="2026")
    parser.add_argument("--date",       required=True, help="YYYY-MM-DD da partida")
    parser.add_argument("--sport-role", default="mandante",
                        choices=["mandante", "visitante"],
                        help="Sport joga como mandante ou visitante")
    parser.add_argument("--city",       default="Recife")
    parser.add_argument("--stadium",    default="Ilha do Retiro")
    args = parser.parse_args()

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    cfg = {
        "team_key":   args.team_key,
        "team_name":  args.team_name,
        "team_abbr":  args.team_abbr,
        "team_id":    args.team_id,
        "round":      args.round,
        "season":     args.season,
        "date":       args.date,
        "sport_role": args.sport_role,
        "city":       args.city,
        "stadium":    args.stadium,
    }

    print(f"Carregando dados: {args.team_key} ...")
    matches, stats, players = _load(args.team_key)

    print(f"Computando metricas ...")
    data = build_data(cfg, matches, stats, players)

    out    = f"pending_posts/{args.date}_raio-x-{args.team_key}"
    shield = f"data/cache/logos/{args.team_id}.png"

    print(f"Gerando Raio-X v2 — {args.team_abbr} | Serie B {args.season} R{args.round:02d}")
    cards = RaioXCards(
        data=data,
        out_dir=out,
        cfg=cfg,
        logo_path="sportrecifelab_avatar.png",
        shield_path=shield,
    )
    cards.render_all()
