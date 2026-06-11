#!/usr/bin/env python3
"""Generate static HTML snapshots of the CrowdCompass Rover UI for the user guide.

Renders the real app.css with representative markup in three states so the user guide can
embed faithful screenshots without a live browser session. Output HTML is rasterized to
PNG by wkhtmltoimage (see make_screenshots.sh).
"""
from __future__ import annotations

import pathlib

CSS = pathlib.Path("frontend/src/styles/app.css").read_text()

FONT_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?"
    "family=Bebas+Neue&family=Space+Mono:wght@400;700&display=swap');"
)


def page(body: str) -> str:
    return f"""<!doctype html><html><head><meta charset='utf-8'>
<style>{FONT_IMPORT}\n{CSS}\nbody{{padding:0}}</style></head>
<body><div class='app-shell'>{body}</div></body></html>"""


MAST = """
<header class='masthead'>
  <div class='brand'>
    <span class='brand__kicker'>2026 World Cup · Host City Agent</span>
    <h1 class='brand__title'>CrowdCompass <span>Rover</span></h1>
  </div>
  <span class='mode-chip' data-mode='mock'>mock mode</span>
</header>
"""

SEARCHBAR = """
<div class='searchbar'>
  <input value='{q}' />
  <button class='btn btn--go'>Ask</button>
</div>
<div class='controls'>
  <label class='toggle'><input type='checkbox'/> Use my stadium location</label>
  <div class='chips'>
    <button class='chip'>halal food open now</button>
    <button class='chip'>dónde cambiar dinero</button>
    <button class='chip'>nearest transit to stadium</button>
    <button class='chip'>où est le stade</button>
  </div>
</div>
"""


def row(glyph, name, meta, open_=True, dist=None):
    badge = (
        "<span class='badge badge--open'>Open</span>"
        if open_
        else "<span class='badge badge--closed'>Closed</span>"
    )
    d = f"<span class='row__dist'>{dist}</span>" if dist else ""
    return f"""
<article class='row'>
  <div class='row__glyph'>{glyph}</div>
  <div><h3 class='row__name'>{name}</h3><div class='row__meta'>{meta}</div></div>
  <div class='row__right'>{badge}{d}</div>
</article>"""


LANDING = page(MAST + SEARCHBAR.format(q="") + """
<div class='empty'>Ask for stadiums, food, transit, currency exchange or fan zones — in any language.</div>
""")

ENGLISH = page(MAST + """
<div class='feature-panel'>
  <span class='feature-panel__label'>Engine</span>
  <span class='feature-pill feature-pill--on'>Smart reranking</span>
  <span class='feature-pill feature-pill--on'>Synonym expansion</span>
  <span class='feature-pill feature-pill--on'>Spell tolerance</span>
  <span class='feature-panel__sessions'>2 active</span>
</div>
""" + SEARCHBAR.format(q="halal food open now") + """
<section class='answer'>
  <h2 class='answer__head'>Concierge · English</h2>
  <div>Here is what I found:
1. Halal Guys 8th Avenue — restaurant, open (9.1 km)
2. Sahara Halal Kitchen — restaurant, open</div>
</section>
<div class='plan-strip'>
  <span>Language <b>English</b></span>
  <span>Understood as <b>halal food open now</b></span>
  <span>Filters <b>Open now, Halal</b></span>
</div>
<div class='board'>
""" + row("▣", "Halal Guys 8th Avenue", "Food · New York · Halal", True, "9.1 km")
   + row("▣", "Sahara Halal Kitchen", "Food · Los Angeles · Halal", True)
   + row("▣", "Taquería Halal El Árabe", "Food · Mexico City · Halal", True)
   + """</div>
<section class='history'>
  <h2 class='history__head'>Conversation</h2>
  <ol class='history__list'>
    <li class='history__item'><button class='history__query'>halal food open now</button><span class='history__meta'>English · 3 results</span></li>
    <li class='history__item'><button class='history__query'>where is the stadium</button><span class='history__meta'>English · 3 results</span></li>
  </ol>
</section>""")

SPANISH = page(MAST + SEARCHBAR.format(q="dónde cambiar dinero ahora") + """
<section class='answer'>
  <h2 class='answer__head'>Concierge · Español</h2>
  <div>Esto es lo que encontré:
1. Casa de Cambio Centro — currency_exchange, open
2. Times Square Currency Exchange — currency_exchange, open</div>
</section>
<div class='plan-strip'>
  <span>Language <b>Español</b></span>
  <span>Understood as <b>where exchange money now</b></span>
  <span>Filters <b>Exchange, Open now</b></span>
</div>
<div class='board'>
""" + row("$", "Casa de Cambio Centro", "Exchange · Mexico City", True)
   + row("$", "Times Square Currency Exchange", "Exchange · New York", True)
   + "</div>")

OUT = pathlib.Path("docs/img")
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "01-landing.html").write_text(LANDING)
(OUT / "02-english-results.html").write_text(ENGLISH)
(OUT / "03-spanish-results.html").write_text(SPANISH)
print("snapshots written to", OUT)
