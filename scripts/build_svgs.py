#!/usr/bin/env python3
"""Build every animated SVG card used by the profile README.

    python3 scripts/build_svgs.py            # writes assets/worldline/*.svg

Dev-time only (needs fontTools + brotli and a local JetBrains Mono install).
Fonts are subset per SVG and embedded as base64 WOFF2 so the cards render the
same on every OS. The Noto Serif JP subset is fetched once from Google Fonts
(only the handful of kanji/kana used) and cached in scripts/.cache/.
"""
from __future__ import annotations

import base64
import html
import io
import json
import math
import os
import random
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dmail  # noqa: E402
import svgkit as K  # noqa: E402
from svgkit import C, text, tw  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "worldline"
CACHE = ROOT / "scripts" / ".cache"
JBM_DIR = Path(os.environ.get("JBM_DIR", "/usr/share/fonts/TTF"))
JBM = {300: "JetBrainsMono-Light.ttf", 400: "JetBrainsMono-Regular.ttf", 500: "JetBrainsMono-Medium.ttf",
       700: "JetBrainsMono-Bold.ttf", 800: "JetBrainsMono-ExtraBold.ttf"}
JP_FONT = CACHE / "NotoSerifJP-700.woff2"
JP_TEXT = ("世界線変動率ステータス錬金術師賢者称号固有スキル収束メインクエストアイテムボックス実績"
           "Dメールエル・プサイ・コングルゥ発明品サイド【】×")


# ── fonts ──────────────────────────────────────────────────────────────────
def ensure_jp_font() -> None:
    if JP_FONT.exists():
        cmap = TTFont(JP_FONT).getBestCmap()
        if all(ord(c) in cmap for c in JP_TEXT):
            return
    CACHE.mkdir(parents=True, exist_ok=True)
    ua = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36"}
    url = ("https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@700&text="
           + urllib.parse.quote(JP_TEXT))
    css = urllib.request.urlopen(urllib.request.Request(url, headers=ua), timeout=30).read().decode()
    font_url = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", css).group(1)
    JP_FONT.write_bytes(urllib.request.urlopen(urllib.request.Request(font_url, headers=ua), timeout=30).read())
    print(f"fetched {JP_FONT.relative_to(ROOT)}")


def subset_b64(path: Path, chars: str) -> str:
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = []          # no ligatures: text renders exactly as written
    opts.name_IDs = ["*"]              # keep copyright + OFL licence records
    opts.name_languages = ["*"]
    opts.hinting = False
    opts.notdef_outline = True
    font = subset.load_font(str(path), opts)
    cmap = font.getBestCmap()
    missing = sorted({c for c in chars if ord(c) not in cmap and not c.isspace()})
    if missing:
        print(f"  ! {path.name} lacks {''.join(missing)!r} (will fall back)")
    sub = subset.Subsetter(opts)
    sub.populate(text=chars)
    sub.subset(font)
    buf = io.BytesIO()
    subset.save_font(font, buf, opts)
    return base64.b64encode(buf.getvalue()).decode()


def fonts_css_for(svg_body: str, extra_m: str = "") -> str:
    m_chars, j_chars = set(extra_m), set()
    for cls, s in re.findall(r'class="(m|j)"[^>]*>([^<]+)', svg_body):
        (m_chars if cls == "m" else j_chars).update(html.unescape(s))
    weights = {int(w) for w in re.findall(r'font-weight="(\d+)"', svg_body)} or {400}
    css = []
    if m_chars:
        chars = "".join(sorted(m_chars | {" "}))
        for w in sorted(weights):
            wf = min(JBM, key=lambda k: abs(k - w))
            css.append(f"@font-face{{font-family:'JBM';font-weight:{w};"
                       f"src:url(data:font/woff2;base64,{subset_b64(JBM_DIR / JBM[wf], chars)}) format('woff2')}}")
    if j_chars:
        css.append(f"@font-face{{font-family:'NSJ';font-weight:100 900;"
                   f"src:url(data:font/woff2;base64,{subset_b64(JP_FONT, ''.join(sorted(j_chars)))}) format('woff2')}}")
    return "".join(css)


def write(name: str, w: int, h: int, body: str, title: str, desc: str, css: str = "", defs: str = "",
          extra_m: str = "") -> None:
    svg = K.doc(w, h, body, defs=defs, css=css, title=title, desc=desc,
                fonts_css=fonts_css_for(body, extra_m))
    (OUT / name).write_text(svg)
    print(f"  {name:<22} {len(svg) / 1024:6.1f} KB")


def tspan(s, cls="m", fill=None, weight=None, dx=None) -> str:
    a = f' class="{cls}"'
    if fill:
        a += f' fill="{fill}"'
    if weight:
        a += f' font-weight="{weight}"'
    if dx is not None:
        a += f' dx="{dx}"'
    return f"<tspan{a}>{K.esc(s)}</tspan>"


# ── 00 · hero ──────────────────────────────────────────────────────────────
def build_hero():
    W, H = 1000, 430
    b = [f'<rect width="{W}" height="{H}" rx="16" fill="{C["bg"]}"/>',
         f'<ellipse cx="500" cy="150" rx="430" ry="190" fill="url(#heroglow)"/>',
         f'<rect width="{W}" height="{H}" rx="16" fill="url(#dots)"/>',
         f'<rect width="{W}" height="{H}" rx="16" fill="url(#scan)"/>']
    defs = (f'<radialGradient id="heroglow"><stop offset="0" stop-color="{C["amber_deep"]}" stop-opacity=".16"/>'
            f'<stop offset="1" stop-color="{C["amber_deep"]}" stop-opacity="0"/></radialGradient>'
            '<linearGradient id="ringfade" x1="0" y1="0" x2="0" y2="1"><stop offset=".55" stop-color="#fff"/>'
            '<stop offset=".86" stop-color="#fff" stop-opacity="0"/></linearGradient>'
            '<mask id="ringmask" maskUnits="userSpaceOnUse" x="0" y="0" width="1000" height="430">'
            '<rect x="0" y="-20" width="1000" height="330" fill="url(#ringfade)"/></mask>'
            f'<linearGradient id="namegrad" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{C["text"]}"/>'
            f'<stop offset=".5" stop-color="{C["amber_hot"]}"><animate attributeName="offset" values=".2;.8;.2" dur="9s" repeatCount="indefinite"/></stop>'
            f'<stop offset="1" stop-color="{C["text"]}"/></linearGradient>')

    # gears (Steins;Gate-style clockwork, original drawing)
    b.append(K.gear(42, 398, 70, 18, 9, C["amber"], 1.2, .13, 90))
    b.append(K.gear(148, 420, 34, 10, 7, C["amber"], 1.1, .13, 50, rev=True))
    b.append(K.gear(968, 34, 58, 15, 8, C["cyan"], 1.1, .12, 80, rev=True))

    # clock / magic-circle ring behind the tubes, faded out before the name
    cx, cy, r = 500, 140, 150
    ring = [f'<circle cx="{cx}" cy="{cy}" r="{r + 14}" fill="none" stroke="{C["amber"]}" stroke-opacity=".22"/>',
            f'<circle cx="{cx}" cy="{cy}" r="{r - 12}" fill="none" stroke="{C["amber"]}" stroke-opacity=".14"/>']
    ticks = []
    for k in range(60):
        a = 2 * math.pi * k / 60
        r0 = r + 4 if k % 5 else r - 2
        ticks.append(f'<line x1="{r0 * math.cos(a):.1f}" y1="{r0 * math.sin(a):.1f}" x2="{(r + 12) * math.cos(a):.1f}" y2="{(r + 12) * math.sin(a):.1f}"/>')
    ring.append(f'<g transform="translate({cx} {cy})"><g stroke="{C["amber"]}" stroke-opacity=".28" stroke-width="1">'
                f'<animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="240s" repeatCount="indefinite"/>{"".join(ticks)}</g></g>')
    runes = ("Ĥψ = Eψ   ·   ∂ρ/∂t = −∇·J   ·   softmax(QK^T/√d)·V   ·   ΔG = ΔH − TΔS   ·   "
             "RRF(d) = Σ 1/(k + r)   ·   S = −Σ p log p   ·   F = −∇U   ·   ")
    rr = r - 4
    ls = (2 * math.pi * rr) / len(runes) - 0.6 * 10.5
    ring.append(f'<path id="runering" d="M{cx},{cy - rr} a{rr},{rr} 0 1,1 0,{2 * rr} a{rr},{rr} 0 1,1 0,{-2 * rr}" fill="none"/>')
    ring.append(f'<g><animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" to="-360 {cx} {cy}" dur="200s" repeatCount="indefinite"/>'
                f'<text class="m" font-size="10.5" font-weight="400" fill="{C["amber"]}" opacity=".30" letter-spacing="{ls:.3f}">'
                f'<textPath class="m" href="#runering" xlink:href="#runering">{K.esc(runes)}</textPath></text></g>')
    b.append(f'<g mask="url(#ringmask)">{"".join(ring)}</g>')

    # background worldlines drifting along the bottom
    for i, (col, y, amp, per, dash, dur) in enumerate([(C["amber"], 372, 10, 260, "2 7", 14), (C["cyan"], 384, 8, 210, "1 6", 18),
                                                         (C["crimson"], 396, 6, 330, "3 9", 22)]):
        pts = [(x, y + amp * math.sin(2 * math.pi * x / per + i)) for x in range(0, W + 1, 25)]
        b.append(f'<path d="{K.catmull_path(pts)}" fill="none" stroke="{col}" stroke-opacity=".22" stroke-width="1.2" stroke-dasharray="{dash}">'
                 f'<animate attributeName="stroke-dashoffset" from="0" to="-90" dur="{dur}s" repeatCount="indefinite"/></path>')

    # left: benzene ring (chemistry)
    bx, by, br = 86, 150, 40
    hexpts = [(bx + br * math.cos(math.radians(-90 + 60 * k)), by + br * math.sin(math.radians(-90 + 60 * k))) for k in range(6)]
    b.append(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in hexpts)}" fill="none" stroke="{C["amber"]}" stroke-width="1.8" stroke-opacity=".85"/>')
    b.append(f'<circle cx="{bx}" cy="{by}" r="24" fill="none" stroke="{C["amber"]}" stroke-width="1.2" stroke-dasharray="5 4" stroke-opacity=".7">'
             f'<animateTransform attributeName="transform" type="rotate" from="0 {bx} {by}" to="360 {bx} {by}" dur="24s" repeatCount="indefinite"/></circle>')
    for k, (x, y) in enumerate(hexpts):
        ox, oy = bx + (br + 16) * math.cos(math.radians(-90 + 60 * k)), by + (br + 16) * math.sin(math.radians(-90 + 60 * k))
        b.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{ox:.1f}" y2="{oy:.1f}" stroke="{C["amber"]}" stroke-opacity=".45" stroke-width="1.2"/>')
        b.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{C["bg"]}" stroke="{C["amber"]}" stroke-width="1.4">'
                 f'<animate attributeName="r" values="3.2;4.4;3.2" dur="3s" begin="{k * 0.5}s" repeatCount="indefinite"/></circle>')
    b.append(text(bx, by + 84, "C₆H₆ · π", 11, C["amber"], 400, anchor="middle", op=".75"))

    # right: tiny attention network (AI)
    layers = [[(868, y) for y in (118, 150, 182)], [(910, y) for y in (102, 134, 166, 198)], [(952, y) for y in (134, 166)]]
    edges = [(p, q) for L0, L1 in zip(layers, layers[1:]) for p in L0 for q in L1]
    for p, q in edges:
        b.append(f'<line x1="{p[0]}" y1="{p[1]}" x2="{q[0]}" y2="{q[1]}" stroke="{C["cyan"]}" stroke-opacity=".22" stroke-width="1"/>')
    rnd = random.Random(3)
    for k, (p, q) in enumerate(rnd.sample(edges, 7)):
        b.append(f'<circle r="2.4" fill="{C["cyan"]}" filter="url(#glow)"><animateMotion path="M{p[0]},{p[1]} L{q[0]},{q[1]}" '
                 f'dur="1.6s" begin="{k * 0.37:.2f}s" repeatCount="indefinite"/></circle>')
    for L in layers:
        for (x, y) in L:
            b.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{C["bg"]}" stroke="{C["cyan"]}" stroke-width="1.5"/>')
    b.append(text(910, 234, "attention", 11, C["cyan"], 400, anchor="middle", op=".75"))

    # header strip
    b.append(f'<g transform="translate(34 33) rotate(45)"><rect x="-4" y="-4" width="8" height="8" fill="{C["amber"]}">'
             f'<animate attributeName="opacity" values="1;.3;1" dur="2.4s" repeatCount="indefinite"/></rect></g>')
    b.append(text(48, 37, "LAB MEMBER 076 · IISER KOLKATA", 11, C["amber"], 700, ls=3, op=".9"))
    meta = "DIVERGENCE METER"
    b.append(text(W - 30, 37, meta, 11, C["muted"], 700, anchor="end", ls=3))
    b.append(text(W - 30 - tw(meta, 11, 3) - 16, 37, "世界線変動率", 13, C["amber"], 700, anchor="end", jp=True))

    # nixie divergence meter
    tube_w, tube_h, gap = 72, 136, 13
    x0 = (W - (8 * tube_w + 7 * gap)) / 2
    segs = [(0.0, "1.048596"), (4.2, None), (5.4, "0.571024"), (8.6, None), (9.8, "1.130205"), (13.0, None), (14.4, "1.048596")]
    tl = K.scramble_timeline(segs, 8, 18.0, seed=11)
    b.append(K.nixie_row(x0, 68, "1.048596", tube_w, tube_h, gap, timeline=tl, dur=18.0, uid="hero"))

    # name + roles
    name = "SHUVAM BANERJI SEAL"
    b.append(text(500 + 5, 296, name, 44, "url(#namegrad)", 800, anchor="middle", ls=10, extra='filter="url(#soft)"'))
    b.append(f'<rect x="290" y="314" width="420" height="1" fill="{C["amber"]}" opacity=".35"/>')
    b.append(f'<g transform="translate(500 314.5) rotate(45)"><rect x="-3.5" y="-3.5" width="7" height="7" fill="{C["amber"]}"/></g>')
    role = "COMPUTATIONAL CHEMIST  ·  AI / IR RESEARCHER  ·  DEEP-TECH CO-FOUNDER"
    b.append(text(500 + 1.25, 344, role, 13.5, C["muted"], 700, anchor="middle", ls=2.5))
    b.append(text(40, 404, "Ĥψ = Eψ", 13, C["amber"], 700, op=".8"))
    b.append(text(500, 404, "TWO ATTRACTOR FIELDS  ·  ONE WORLDLINE", 10.5, C["dim"], 700, anchor="middle", ls=3))
    b.append(text(W - 40, 404, "softmax(QK^T/√d)·V", 13, C["cyan"], 700, anchor="end", op=".8"))
    b.append(f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="15.5" fill="none" stroke="{C["line"]}" stroke-width="1.5"/>')
    write("hero.svg", W, H, "\n".join(b), "Shuvam Banerji Seal: divergence meter",
          "Animated nixie-tube divergence meter cycling 1.048596, 0.571024, 1.130205 above the name Shuvam Banerji Seal: "
          "computational chemist, AI and IR researcher, deep-tech co-founder.", defs=defs)


# ── 01 · status window ─────────────────────────────────────────────────────
def build_status():
    W, H = 1000, 616
    acc = C["cyan"]
    b = [K.frame(W, H, acc, "01", "STATUS", "ステータス", "OBSERVER FILE · LAB MEMBER 076")]
    defs = (f'<linearGradient id="scanbar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{acc}" stop-opacity="0"/>'
            f'<stop offset=".85" stop-color="{acc}" stop-opacity=".07"/><stop offset="1" stop-color="{acc}" stop-opacity="0"/></linearGradient>'
            f'<clipPath id="card"><rect width="{W}" height="{H}" rx="16"/></clipPath>'
            f'<linearGradient id="xp" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{C["cyan_deep"]}"/><stop offset="1" stop-color="{C["amber"]}"/></linearGradient>')
    b.append(f'<g clip-path="url(#card)"><rect x="0" y="-90" width="{W}" height="90" fill="url(#scanbar)">'
             f'<animate attributeName="y" from="-90" to="{H}" dur="7s" repeatCount="indefinite"/></rect></g>')

    # sigil: benzene ring wired like a neural net, inside a rotating rune circle
    cx, cy = 180, 272
    b.append(f'<circle cx="{cx}" cy="{cy}" r="128" fill="{acc}" fill-opacity=".025" stroke="{acc}" stroke-opacity=".45" stroke-width="1.2"/>')
    b.append(f'<circle cx="{cx}" cy="{cy}" r="104" fill="none" stroke="{acc}" stroke-opacity=".25"/>')
    runes = "Ĥψ=Eψ · ∇²φ=−4πρ · F=−∇U · softmax(QK^T/√d)V · ΔG‡ · Σ1/(k+r) · −Σp·log p · "
    rr = 113
    ls = (2 * math.pi * rr) / len(runes) - 0.6 * 10.5
    b.append(f'<path id="sring" d="M{cx},{cy - rr} a{rr},{rr} 0 1,1 0,{2 * rr} a{rr},{rr} 0 1,1 0,{-2 * rr}" fill="none"/>')
    b.append(f'<g><animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" to="360 {cx} {cy}" dur="90s" repeatCount="indefinite"/>'
             f'<text class="m" font-size="10.5" font-weight="400" fill="{acc}" opacity=".6" letter-spacing="{ls:.3f}">'
             f'<textPath class="m" href="#sring" xlink:href="#sring">{K.esc(runes)}</textPath></text></g>')
    ticks = "".join(
        f'<line x1="{92 * math.cos(2 * math.pi * k / 72):.1f}" y1="{92 * math.sin(2 * math.pi * k / 72):.1f}" '
        f'x2="{(98 if k % 6 else 101) * math.cos(2 * math.pi * k / 72):.1f}" y2="{(98 if k % 6 else 101) * math.sin(2 * math.pi * k / 72):.1f}"/>'
        for k in range(72))
    b.append(f'<g transform="translate({cx} {cy})"><g stroke="{C["amber"]}" stroke-opacity=".45">'
             f'<animateTransform attributeName="transform" type="rotate" from="0" to="-360" dur="140s" repeatCount="indefinite"/>{ticks}</g></g>')
    hexr = 64
    hp = [(cx + hexr * math.cos(math.radians(-90 + 60 * k)), cy + hexr * math.sin(math.radians(-90 + 60 * k))) for k in range(6)]
    for k, (x, y) in enumerate(hp):
        b.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{cx}" y2="{cy}" stroke="{acc}" stroke-opacity=".4" stroke-dasharray="3 5">'
                 f'<animate attributeName="stroke-dashoffset" from="0" to="-16" dur="1.2s" repeatCount="indefinite"/></line>')
    b.append(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in hp)}" fill="none" stroke="{acc}" stroke-width="1.8"/>')
    b.append(f'<circle cx="{cx}" cy="{cy}" r="44" fill="none" stroke="{C["amber"]}" stroke-width="1.3" stroke-dasharray="4 6" stroke-opacity=".8">'
             f'<animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" to="360 {cx} {cy}" dur="30s" repeatCount="indefinite"/></circle>')
    for k, (x, y) in enumerate(hp):
        b.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{C["bg"]}" stroke="{acc}" stroke-width="1.6">'
                 f'<animate attributeName="stroke" values="{acc};{C["amber"]};{acc}" dur="3.6s" begin="{k * 0.6}s" repeatCount="indefinite"/></circle>')
    b.append(f'<circle r="3" fill="{C["amber"]}" filter="url(#glow)"><animateMotion path="M{cx + 80},{cy} a80,80 0 1,1 -160,0 a80,80 0 1,1 160,0" dur="7s" repeatCount="indefinite"/></circle>')
    b.append(f'<circle r="2.4" fill="{acc}" filter="url(#glow)"><animateMotion path="M{cx - 80},{cy} a80,80 0 1,0 160,0 a80,80 0 1,0 -160,0" dur="11s" repeatCount="indefinite"/></circle>')
    b.append(f'<circle cx="{cx}" cy="{cy}" r="22" fill="#0F1220" stroke="{C["amber"]}" stroke-width="1.6"/>')
    b.append(text(cx, cy + 5, "076", 14, C["amber"], 800, anchor="middle"))

    # level + xp
    b.append(text(56, 452, "Lv.5", 30, C["amber"], 800, extra='filter="url(#glow)"'))
    b.append(text(150, 440, "FINAL YEAR", 11, acc, 700, ls=2))
    b.append(text(150, 456, "BS-MS · 2022 → 2027", 10.5, C["muted"], 400))
    b.append(f'<rect x="56" y="470" width="248" height="8" rx="4" fill="#1A1E2E"/>')
    b.append(f'<rect x="56" y="470" width="{248 * 0.88:.0f}" height="8" rx="4" fill="url(#xp)"/>')
    b.append(f'<rect x="56" y="470" width="30" height="8" rx="4" fill="#fff" opacity=".35"><animate attributeName="x" values="56;{56 + 248 * 0.88 - 30:.0f};56" dur="4s" repeatCount="indefinite"/></rect>')
    b.append(text(56, 512, "HOME WORLD", 10, C["dim"], 700, ls=2.5))
    b.append(text(56, 530, "Kolkata, India", 13, C["text"], 700))
    b.append(text(56, 560, "SIGNAL", 10, C["dim"], 700, ls=2.5))
    b.append(text(56, 578, "sbs22ms076@iiserkol.ac.in", 12, acc, 400))

    # right column
    X = 360
    b.append(text(X, 86, "NAME", 10, C["dim"], 700, ls=3))
    b.append(text(X, 116, "Shuvam Banerji Seal", 26, C["text"], 800))
    b.append(text(X, 152, "CLASS", 10, C["dim"], 700, ls=3))
    b.append(text(X, 178, "Alchemist-Sage", 17, C["amber"], 800))
    b.append(f'<text x="{X}" y="198" font-size="12" font-weight="700" fill="{C["muted"]}">'
             f'{tspan("錬金術師", "j")}{tspan(" × ", "m")}{tspan("賢者", "j")}</text>')
    b.append(text(X, 216, "computational chemistry × AI", 11, C["muted"], 400))
    G = 680
    b.append(text(G, 152, "GUILD", 10, C["dim"], 700, ls=3))
    b.append(text(G, 178, "IISER Kolkata", 17, acc, 800))
    b.append(text(G, 198, "BS-MS · chemistry major", 11, C["muted"], 400))
    b.append(text(G, 216, "computer-science minor", 11, C["muted"], 400))

    b.append(f'<text x="{X}" y="252" font-size="10" font-weight="700" fill="{C["dim"]}" letter-spacing="3">'
             f'{tspan("TITLES", "m")}{tspan("  称号", "j", C["muted"])}</text>')
    chips = [("UIDAI Data Hackathon 2026 · 1st prize", C["gold"]), ("MeitY GENESIS co-founder ×2", C["amber"]),
             ("Slashdot · President", C["amber"]), ("AAAI · ICWSM reviewer", acc), ("FIRE 2026 track co-organizer", acc)]
    cx_, cy_ = X, 264
    for label, col in chips:
        wch = tw(label, 11.5) + 30
        if cx_ + wch > W - 32:
            cx_, cy_ = X, cy_ + 34
        b.append(f'<rect x="{cx_:.1f}" y="{cy_}" width="{wch:.1f}" height="26" rx="4" fill="{col}" fill-opacity=".07" stroke="{col}" stroke-opacity=".55"/>')
        b.append(f'<g transform="translate({cx_ + 12:.1f} {cy_ + 13}) rotate(45)"><rect x="-2.6" y="-2.6" width="5.2" height="5.2" fill="{col}"/></g>')
        b.append(text(cx_ + 22, cy_ + 17.5, label, 11.5, col, 700))
        cx_ += wch + 8

    b.append(text(X, 358, "STATS", 10, C["dim"], 700, ls=3))
    stats = [("3", "PAPERS", "+1 under review", C["amber"]), ("2", "DATASETS", "on Hugging Face", acc),
             ("2", "STARTUPS", "MeitY-funded", C["amber"]), ("4", "1ST PLACES", "incl. UIDAI '26", C["gold"]),
             ("2k+", "APP USERS", "IISERKonnect", acc)]
    bw = (W - 32 - X - 4 * 9.5) / 5
    for k, (num, lab, sub, col) in enumerate(stats):
        x = X + k * (bw + 9.5)
        b.append(f'<rect x="{x:.1f}" y="370" width="{bw:.1f}" height="74" rx="6" fill="{C["panel"]}" stroke="{col}" stroke-opacity=".3"/>')
        b.append(f'<rect x="{x:.1f}" y="370" width="3" height="74" rx="1.5" fill="{col}" opacity=".8"/>')
        b.append(text(x + 14, 402, num, 26, col, 800))
        b.append(text(x + 14, 421, lab, 9.5, C["text"], 700, ls=1.5))
        b.append(text(x + 14, 436, sub, 9.5, C["muted"], 400))

    b.append(f'<text x="{X}" y="476" font-size="10" font-weight="700" fill="{C["dim"]}" letter-spacing="3">'
             f'{tspan("UNIQUE SKILLS", "m")}{tspan("  固有スキル", "j", C["muted"])}</text>')
    skills = [("Ab Initio Sight", "DFT · B3LYP · Quantum ESPRESSO · Gaussian"),
              ("Hybrid Retrieval", "BM25 + dense · RRF · HyDE · FAISS"),
              ("Ensemble Control", "LAMMPS · GROMACS · NVT/NPT · RDF, MSD"),
              ("Sparse Experts", "MoE transformers · LoRA/QLoRA · Gemma"),
              ("Machine-Checked Truth", "Lean 4 · Mathlib · Gray codes"),
              ("Sycophancy Sense", "LLM-as-Judge · SycoLex · AI safety")]
    for k, (nm, desc) in enumerate(skills):
        x = X + (k % 2) * 312
        y = 500 + (k // 2) * 40
        col = C["amber"] if k % 2 == 0 else acc
        b.append(f'<text x="{x}" y="{y}" font-size="13.5" font-weight="800" fill="{col}">'
                 f'{tspan("【", "j")}{tspan(nm, "m")}{tspan("】", "j")}</text>')
        b.append(text(x + 4, y + 17, desc, 11, C["muted"], 400))
    write("status.svg", W, H, "\n".join(b), "Status window: Shuvam Banerji Seal",
          "Isekai-style status window. Class: Alchemist-Sage (computational chemistry × AI). Guild: IISER Kolkata, "
          "BS-MS chemistry major with computer-science minor. Titles: UIDAI Data Hackathon 2026 1st prize, MeitY GENESIS "
          "co-founder of two startups, Slashdot president, AAAI and ICWSM reviewer, FIRE 2026 track co-organizer. "
          "Stats: 3 papers plus 1 under review, 2 open datasets, 2 startups, 4 first places, 2000+ app users.",
          defs=defs)


# ── 02 · worldline map ─────────────────────────────────────────────────────
YEARS = {2022: 80, 2023: 190, 2024: 320, 2025: 500, 2026: 720, 2027: 930}


def yx(t: float) -> float:
    ks = sorted(YEARS)
    for a, b_ in zip(ks, ks[1:]):
        if a <= t <= b_:
            return YEARS[a] + (t - a) * (YEARS[b_] - YEARS[a])
    return YEARS[ks[-1]]


def build_worldlines():
    W, H = 1000, 580
    b = [K.frame(W, H, C["amber"], "02", "WORLDLINE MAP", "世界線収束", "2022 → 2027 · α CHEMISTRY × β AI")]
    defs = (f'<linearGradient id="sg" gradientUnits="userSpaceOnUse" x1="{yx(2026.45):.1f}" y1="0" x2="975" y2="0"><stop offset="0" stop-color="{C["gold"]}"/>'
            f'<stop offset=".5" stop-color="#fff"><animate attributeName="offset" values=".1;.9;.1" dur="4s" repeatCount="indefinite"/></stop>'
            f'<stop offset="1" stop-color="{C["gold"]}" stop-opacity=".3"/></linearGradient>')
    for yr, x in YEARS.items():
        b.append(f'<line x1="{x}" y1="66" x2="{x}" y2="540" stroke="#fff" stroke-opacity=".05" stroke-dasharray="2 6"/>')
        b.append(text(x, 562, str(yr), 12, C["muted"] if yr != 2026 else C["text"], 700, anchor="middle"))
        b.append(f'<line x1="{x}" y1="544" x2="{x}" y2="550" stroke="{C["muted"]}" stroke-opacity=".6"/>')
    M = (yx(2026.45), 300)
    alpha = [(40, 168), (146, 162), (260, 176), (410, 160), (554, 178), (650, 196), (720, 224), (775, 262), M]
    beta = [(40, 440), (146, 446), (268, 432), (419, 444), (520, 438), (610, 420), (665, 404), (730, 372), (780, 332), M]
    pa, pb = K.catmull_path(alpha), K.catmull_path(beta)

    # unobserved branches
    rnd = random.Random(5)
    for pts, col in ((alpha, C["amber"]), (beta, C["cyan"])):
        for _ in range(7):
            x = rnd.uniform(90, 700)
            y = K.catmull_y_at(pts, x)
            dy = rnd.choice([-1, 1]) * rnd.uniform(25, 60)
            L = rnd.uniform(90, 170)
            b.append(f'<path d="M{x:.1f},{y:.1f} C{x + L * .4:.1f},{y:.1f} {x + L * .6:.1f},{y + dy:.1f} {x + L:.1f},{y + dy:.1f}" '
                     f'fill="none" stroke="{col}" stroke-opacity=".16" stroke-width="1" stroke-dasharray="2 5"/>')
    b.append(f'<path d="{pa}" fill="none" stroke="{C["amber"]}" stroke-width="2.4" filter="url(#glow)"/>')
    b.append(f'<path d="{pb}" fill="none" stroke="{C["cyan"]}" stroke-width="2.4" filter="url(#glow)"/>')
    # a rect, not a line: a zero-height bbox would collapse both the gradient and the glow filter region
    b.append(f'<rect x="{M[0]:.1f}" y="{M[1] - 1.6}" width="{975 - M[0]:.1f}" height="3.2" rx="1.6" fill="url(#sg)" filter="url(#glow)"/>')
    for p, col, beg in ((pa, C["amber"], 0), (pb, C["cyan"], 1.5), (pa, C["amber_hot"], 3), (pb, C["cyan"], 4.5)):
        b.append(f'<circle r="3.4" fill="{col}" filter="url(#glow2)"><animateMotion path="{p} L975,{M[1]}" dur="6s" begin="{beg}s" repeatCount="indefinite"/></circle>')

    b.append(text(40, 148, "α · CHEMISTRY", 12, C["amber"], 800, ls=2))
    b.append(text(40, 196, "0.571024", 11, C["amber"], 400, op=".6"))
    b.append(text(40, 422, "β · ARTIFICIAL INTELLIGENCE", 12, C["cyan"], 800, ls=2))
    b.append(text(40, 470, "1.130205", 11, C["cyan"], 400, op=".6"))

    def event(t, pts, col, title, sub, ty, anchor="middle", up=True):
        x = yx(t)
        y = K.catmull_y_at(pts, x)
        tx = {"middle": x, "start": x - 6, "end": x + 6}[anchor]  # side labels hug the node
        lead_end = ty + 6 if up else ty - 14
        b.append(f'<line x1="{x:.1f}" y1="{(y - 8) if up else (y + 8):.1f}" x2="{x:.1f}" y2="{lead_end:.1f}" stroke="{col}" stroke-opacity=".45" stroke-dasharray="2 3"/>')
        b.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="{C["bg"]}" stroke="{col}" stroke-width="2"/>')
        b.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="none" stroke="{col}" stroke-width="1">'
                 f'<animate attributeName="r" values="5.5;13;5.5" dur="3s" begin="{(t % 1) * 3:.2f}s" repeatCount="indefinite"/>'
                 f'<animate attributeName="opacity" values=".8;0;.8" dur="3s" begin="{(t % 1) * 3:.2f}s" repeatCount="indefinite"/></circle>')
        b.append(text(tx, ty - 14 if up else ty, title, 11.5, col, 800, anchor=anchor, ls=.5))
        b.append(text(tx, ty if up else ty + 14, sub, 10.5, C["muted"], 400, anchor=anchor))

    # α events (labels above); rows at 100 / 134
    event(2022.6, alpha, C["amber"], "IISER KOLKATA", "BS-MS · chemistry major", 100)
    event(2024.5, alpha, C["amber"], "DFT CATALYST STUDY", "[VO(SALIEP)(DTP)] · B3LYP", 134)
    event(2025.3, alpha, C["amber"], "CHEMENIGMA · 1ST", "IISc Bangalore", 100)
    event(2026.15, alpha, C["amber"], "MOLECULE3D", "LAMMPS in the browser", 134)
    # β events (labels below); rows at 488 / 520
    event(2024.55, beta, C["cyan"], "TREC 2024", "tip-of-tongue retrieval", 488, up=False)
    event(2025.5, beta, C["cyan"], "FIRE 2025", "Gemma PEFT", 488, anchor="end", up=False)
    event(2025.75, beta, C["cyan"], "TWO STARTUPS", "MeitY GENESIS-funded", 520, anchor="end", up=False)
    event(2026.05, beta, C["cyan"], "ECIR 2026", "AgriIR · first author", 520, anchor="start", up=False)
    event(2026.35, beta, C["cyan"], "UIDAI · 1ST PRIZE", "of ~15,000 teams", 488, anchor="start", up=False)

    # convergence
    b.append(f'<circle cx="{M[0]:.1f}" cy="{M[1]}" r="8" fill="{C["gold"]}" filter="url(#glow2)"/>')
    b.append(f'<circle cx="{M[0]:.1f}" cy="{M[1]}" r="8" fill="none" stroke="{C["gold"]}">'
             f'<animate attributeName="r" values="8;26;8" dur="2.4s" repeatCount="indefinite"/>'
             f'<animate attributeName="opacity" values="1;0;1" dur="2.4s" repeatCount="indefinite"/></circle>')
    b.append(text(836, 268, "STEINS GATE", 13, C["gold"], 800, ls=3, extra='filter="url(#glow)"'))
    b.append(text(836, 286, "1.048596", 11, C["gold"], 400, op=".75"))
    b.append(text(836, 326, "MS thesis · 2026–27", 11.5, C["text"], 700))
    b.append(text(836, 342, "Lean 4 × MoE for RNA", 10.5, C["muted"], 400))
    write("worldlines.svg", W, H, "\n".join(b), "Worldline map 2022 to 2027",
          "Two worldlines: alpha (chemistry: IISER Kolkata, DFT catalyst study, ChemEnigma 1st, Molecule3D) and beta "
          "(AI: TREC 2024, FIRE 2025, two MeitY startups, ECIR 2026 AgriIR, UIDAI hackathon 1st prize) converging in "
          "2026 into the Steins Gate line: the MS thesis on Lean 4 formal proofs and mixture-of-experts RNA structure.",
          defs=defs)


# ── 03 · main quest (MS thesis) ────────────────────────────────────────────
def build_mainquest():
    W, H = 1000, 540
    acc = C["violet"]
    b = [K.frame(W, H, acc, "03", "MAIN QUEST", "メインクエスト", "MS THESIS · IISER KOLKATA · 2026 →")]
    b.append(f'<line x1="500" y1="70" x2="500" y2="510" stroke="{C["line"]}" stroke-dasharray="3 5"/>')

    # Project I: K-map
    b.append(text(40, 84, "PROJECT I", 10.5, acc, 800, ls=3))
    b.append(text(40, 108, "The genome on a Karnaugh map", 17, C["text"], 800))
    b.append(text(40, 127, "Gray-coded sequence space, machine-checked in Lean 4", 11.5, C["muted"], 400))
    order = ["A", "G", "T", "C"]
    bits = {"A": "00", "G": "01", "T": "11", "C": "10"}
    cw, ch, gx, gy = 64, 40, 118, 178
    b.append(text(60, 162, "1st╲2nd", 9.5, C["dim"], 700))
    for j, base in enumerate(order):
        x = gx + j * cw + cw / 2
        b.append(text(x, 154, base, 14, C["text"], 800, anchor="middle"))
        b.append(text(x, 167, bits[base], 9.5, C["dim"], 400, anchor="middle"))
        y = gy + j * ch + ch / 2 + 5
        b.append(text(76, y, base, 14, C["text"], 800, anchor="middle"))
        b.append(text(98, y - 1, bits[base], 9.5, C["dim"], 400, anchor="middle"))
    snake = [(0, 0), (0, 1), (0, 2), (0, 3), (1, 3), (1, 2), (1, 1), (1, 0),
             (2, 0), (2, 1), (2, 2), (2, 3), (3, 3), (3, 2), (3, 1), (3, 0)]
    dur, draw = 10.0, 0.8
    for i, (r_, c_) in enumerate(snake):
        x, y = gx + c_ * cw, gy + r_ * ch
        t = i / 15 * draw
        b.append(f'<rect x="{x + 2}" y="{y + 2}" width="{cw - 4}" height="{ch - 4}" rx="4" fill="{C["panel"]}" stroke="{C["line"]}"/>')
        b.append(f'<rect x="{x + 2}" y="{y + 2}" width="{cw - 4}" height="{ch - 4}" rx="4" fill="{acc}" opacity=".1">'
                 f'<animate attributeName="opacity" values=".1;.1;.55;.14;.14" keyTimes="0;{t:.4f};{t + .004:.4f};{t + .06:.4f};1" dur="{dur}s" repeatCount="indefinite"/></rect>')
    pts = [(gx + c_ * cw + cw / 2, gy + r_ * ch + ch / 2) for r_, c_ in snake]
    poly = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    L = sum(math.dist(p, q) for p, q in zip(pts, pts[1:]))
    b.append(f'<path d="{poly}" fill="none" stroke="{acc}" stroke-opacity=".25" stroke-width="2" stroke-dasharray="3 4"/>')
    b.append(f'<path d="{poly}" fill="none" stroke="{C["amber"]}" stroke-width="2.6" stroke-linejoin="round" stroke-dasharray="{L:.1f}" filter="url(#glow)">'
             f'<animate attributeName="stroke-dashoffset" values="{L:.1f};0;0" keyTimes="0;{draw};1" dur="{dur}s" repeatCount="indefinite"/></path>')
    b.append(f'<circle r="6" fill="{C["gold"]}" filter="url(#glow2)"><animateMotion path="{poly}" keyPoints="0;1;1" keyTimes="0;{draw};1" calcMode="linear" dur="{dur}s" repeatCount="indefinite"/></circle>')
    for r_, c_ in snake:  # labels above the path, with a halo so the line never cuts through them
        b.append(text(gx + c_ * cw + cw / 2, gy + r_ * ch + ch / 2 + 5, order[r_] + order[c_], 13, C["text"], 700, anchor="middle",
                      extra=f'stroke="{C["panel"]}" stroke-width="5" stroke-linejoin="round" paint-order="stroke"'))
    b.append(text(40, 362, "every step flips one bit = one point mutation", 11, C["muted"], 400))
    b.append(text(40, 378, "16 cells, 16 steps, and the walk wraps CA → AA", 11, C["dim"], 400))

    # Lean box
    b.append(f'<rect x="40" y="392" width="430" height="120" rx="8" fill="#0E0C16" stroke="{acc}" stroke-opacity=".4"/>')
    b.append(text(56, 412, "LEAN 4 · STATEMENT SKETCH", 9.5, acc, 800, ls=2))
    kw, fn, ty, num, op = acc, C["amber"], C["cyan"], C["gold"], C["muted"]
    lines = [
        [("def ", kw), ("gray", fn), (" (n : ", op), ("ℕ", ty), (") : ", op), ("ℕ", ty), (" := n ^^^ (n >>> ", op), ("1", num), (")", op)],
        [],
        [("theorem ", kw), ("gray_step", fn), (" (n : ", op), ("ℕ", ty), (") :", op)],
        [("    (", op), ("gray", fn), (" n ^^^ ", op), ("gray", fn), (" (n + ", op), ("1", num), (")).popcount = ", op), ("1", num)],
    ]
    for k, segs in enumerate(lines):
        if segs:
            b.append(f'<text x="56" y="{438 + k * 20}" font-size="12.5" font-weight="400" xml:space="preserve" style="white-space:pre">'
                     + "".join(tspan(s, "m", col) for s, col in segs) + "</text>")

    # Project II: MoE for RNA
    X0 = 530
    b.append(text(X0, 84, "PROJECT II", 10.5, acc, 800, ls=3))
    b.append(text(X0, 108, "Sparse experts for RNA structure", 17, C["text"], 800))
    b.append(text(X0, 127, "Mixture-of-Experts transformer · sequence → contacts → structure", 11.5, C["muted"], 400))
    seq = "GGGACUUCGGUCCC"
    pitch, tw_ = 30.5, 26
    tx0 = X0 + (440 - (13 * pitch + tw_)) / 2
    loop = set(range(5, 9))
    tok = []
    for i, nt in enumerate(seq):
        x = tx0 + i * pitch
        col = C["cyan"] if i in loop else C["amber"]
        tok.append(x + tw_ / 2)
        b.append(f'<rect x="{x:.1f}" y="152" width="{tw_}" height="28" rx="4" fill="{col}" fill-opacity=".08" stroke="{col}" stroke-opacity=".7"/>')
        b.append(text(x + tw_ / 2, 171, nt, 13, col, 800, anchor="middle"))
    b.append(text(tok[0], 146, "5′", 9.5, C["dim"], 700, anchor="middle"))
    b.append(text(tok[-1], 146, "3′", 9.5, C["dim"], 700, anchor="middle"))
    rx_, ry_ = X0 + 220, 214
    for x in tok:
        b.append(f'<line x1="{x:.1f}" y1="180" x2="{rx_ + (x - rx_) * .35:.1f}" y2="{ry_}" stroke="{C["muted"]}" stroke-opacity=".15"/>')
    b.append(f'<rect x="{rx_ - 95}" y="{ry_}" width="190" height="28" rx="14" fill="{C["panel2"]}" stroke="{acc}" stroke-opacity=".7"/>')
    b.append(text(rx_, ry_ + 18.5, "ROUTER · top-2 gating", 11, C["text"], 700, anchor="middle"))
    experts = [("E1", "helix", C["amber"]), ("E2", "hairpin loop", C["cyan"]), ("E3", "pseudoknot", C["violet"]), ("E4", "junction", C["muted"])]
    ew, eg = 100, 13.3
    ex0 = X0 + (440 - (4 * ew + 3 * eg)) / 2
    ecx = []
    for k, (eid, name, col) in enumerate(experts):
        x = ex0 + k * (ew + eg)
        ecx.append(x + ew / 2)
        b.append(f'<line x1="{rx_}" y1="{ry_ + 28}" x2="{x + ew / 2:.1f}" y2="274" stroke="{col}" stroke-opacity=".25"/>')
        anim = ""
        if k in (0, 1):
            anim = (f'<animate attributeName="stroke-opacity" values=".35;1;.35" dur="{1.6 + k * .5}s" repeatCount="indefinite"/>')
        b.append(f'<rect x="{x:.1f}" y="274" width="{ew}" height="44" rx="6" fill="{col}" fill-opacity=".06" stroke="{col}" stroke-opacity=".5" stroke-width="1.4">{anim}</rect>')
        b.append(text(x + 10, 290, eid, 9.5, C["dim"], 800, ls=1))
        b.append(text(x + 10, 308, name, 11.5, col, 800))
    b.append(text(ecx[2], 334, "idle: no pseudoknot here", 9, C["dim"], 400, anchor="middle"))
    for k, i in enumerate([0, 6, 3, 7, 11, 5, 13, 8]):
        e = 1 if i in loop else 0
        col = C["cyan"] if e else C["amber"]
        path = f"M{tok[i]:.1f},180 L{rx_},{ry_ + 14} L{ecx[e]:.1f},274"
        b.append(f'<circle r="3" fill="{col}" filter="url(#glow)"><animateMotion path="{path}" dur="1.8s" begin="{k * 0.45:.2f}s" repeatCount="indefinite"/></circle>')
    b.append(f'<circle r="2.4" fill="{C["muted"]}"><animateMotion path="M{tok[2]:.1f},180 L{rx_},{ry_ + 14} L{ecx[3]:.1f},274" dur="1.8s" begin=".9s" repeatCount="indefinite"/></circle>')

    # outputs: contact map + hairpin
    cm_x, cm_y, cs = 548, 356, 7
    pairs = [(0, 13), (1, 12), (2, 11), (3, 10), (4, 9)]
    b.append(f'<rect x="{cm_x - 2}" y="{cm_y - 2}" width="{14 * cs + 4}" height="{14 * cs + 4}" rx="3" fill="{C["panel"]}" stroke="{C["line"]}"/>')
    for i in range(14):
        b.append(f'<rect x="{cm_x + i * cs}" y="{cm_y + i * cs}" width="{cs - 1}" height="{cs - 1}" fill="{C["muted"]}" opacity=".25"/>')
    for k, (i, j) in enumerate(pairs):
        col = C["gold"] if seq[i] + seq[j] in ("GC", "CG") else C["amber"]
        for (p, q) in ((i, j), (j, i)):
            b.append(f'<rect x="{cm_x + q * cs}" y="{cm_y + p * cs}" width="{cs - 1}" height="{cs - 1}" fill="{col}">'
                     f'<animate attributeName="opacity" values=".35;1;.35" dur="2.5s" begin="{k * .3:.1f}s" repeatCount="indefinite"/></rect>')
    b.append(text(cm_x + 7 * cs, cm_y + 14 * cs + 18, "contact map", 10, C["dim"], 700, anchor="middle"))
    b.append(f'<path d="M662,405 L694,405 M688,399 L694,405 L688,411" fill="none" stroke="{C["muted"]}" stroke-width="1.4"/>')
    sx = [730, 762, 794, 826, 858]
    top = [(x, 385) for x in sx]
    lpc = (888, 405)
    lps = [(lpc[0] + 28 * math.cos(math.radians(a)), lpc[1] + 28 * math.sin(math.radians(a))) for a in (-70, -22, 22, 70)]
    bot = [(x, 425) for x in reversed(sx)]
    pos = top + lps + bot
    b.append(f'<path d="M{" L".join(f"{x:.1f},{y:.1f}" for x, y in pos)}" fill="none" stroke="{C["muted"]}" stroke-opacity=".45" stroke-width="1.3"/>')
    for i, j in pairs:
        (x1, y1), (x2, y2) = pos[i], pos[j]
        gc = seq[i] + seq[j] in ("GC", "CG")
        col = C["gold"] if gc else C["amber"]
        if gc:
            b.append(f'<line x1="{x1 - 2}" y1="{y1 + 10}" x2="{x2 - 2}" y2="{y2 - 10}" stroke="{col}" stroke-width="1.2"/>'
                     f'<line x1="{x1 + 2}" y1="{y1 + 10}" x2="{x2 + 2}" y2="{y2 - 10}" stroke="{col}" stroke-width="1.2"/>')
        else:
            b.append(f'<line x1="{x1}" y1="{y1 + 10}" x2="{x2}" y2="{y2 - 10}" stroke="{col}" stroke-width="1.2"/>')
    for i, (x, y) in enumerate(pos):
        col = C["cyan"] if i in loop else C["amber"]
        b.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="10" fill="{C["bg"]}" stroke="{col}" stroke-width="1.4"/>')
        b.append(text(x, y + 4, seq[i], 11, col, 800, anchor="middle"))
    b.append(text(712, 389, "5′", 9.5, C["dim"], 700, anchor="end"))
    b.append(text(712, 429, "3′", 9.5, C["dim"], 700, anchor="end"))
    b.append(text(810, 466, "UUCG tetraloop · 5 bp stem", 10, C["dim"], 700, anchor="middle"))
    b.append(text(750, 500, "sparse routing · one expert per motif · fixed inference budget", 10, C["muted"], 400, anchor="middle"))
    write("mainquest.svg", W, H, "\n".join(b), "Main quest: MS thesis",
          "Project I: DNA dinucleotides on a Gray-coded 4 by 4 Karnaugh map, walked one bit flip (one point mutation) "
          "at a time, with a Lean 4 statement sketch that consecutive Gray codes differ in one bit. Project II: a "
          "mixture-of-experts transformer routing an RNA hairpin's stem tokens to a helix expert and loop tokens to a "
          "loop expert, producing a contact map and the hairpin structure.")


# ── 04 · guild records ─────────────────────────────────────────────────────
def build_guild():
    W, H = 1000, 466
    acc = C["gold"]
    b = [K.frame(W, H, acc, "04", "GUILD RECORDS", "実績", "HONOURS · CONTESTS · SERVICE")]
    defs = ('<linearGradient id="shine" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
            '<stop offset=".5" stop-color="#fff" stop-opacity=".16"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>')
    entries = [
        ("1ST", C["gold"], "UIDAI Data Hackathon 2026 · 1st prize", "Rs 2,00,000 · ~15,000 teams · UIDAI, NIC & MeitY", "2026"),
        ("TOP14", C["amber"], "Capital One Launchpad · top 14", "of 5,073 teams · IndicAgri, 20+ language agri-RAG", "2025"),
        ("1ST", C["amber"], "ChemEnigma, IISc Bangalore · 1st", "72-hour theory + experiment + presentation contest", "2025"),
        ("1ST", C["cyan"], "StatusCode1, IIIT Kalyani · 1st", "GIAN track · LLM search over abandoned US patents", "2024"),
        ("1ST", C["cyan"], "StatusCode0, IIIT Kalyani · 1st", "MATLAB track · domestic-waste data analysis", "2023"),
        ("REV", C["violet"], "Peer reviewer · AAAI & ICWSM", "program committee / reviewer", "now"),
        ("ORG", C["violet"], "FIRE 2026 · SYCO PHANCY track", "co-organizer with UBO (France) and UvA (NL)", "2026"),
        ("TALK", C["green"], "CBSE District-Level Deliberation", "AI subject expert · 64 teachers from 38 schools", "2026"),
        ("PRES", C["green"], "Slashdot, IISER Kolkata · President", "programming & design club · elected with 99%", "2025"),
        ("ORG", C["green"], "Qiskit Fall Fest 2025 · organizer", "IBM Quantum-sponsored · 1 of 150 institutes", "2025"),
    ]
    cw_, ch_ = 458, 64
    for k, (rank, col, title, sub, yr) in enumerate(entries):
        x = 30 if k % 2 == 0 else 512
        y = 70 + (k // 2) * 76
        b.append(f'<rect x="{x}" y="{y}" width="{cw_}" height="{ch_}" rx="8" fill="{C["panel"]}" stroke="{col}" stroke-opacity="{.6 if k == 0 else .28}"/>')
        if k == 0:
            b.append(f'<clipPath id="c0"><rect x="{x}" y="{y}" width="{cw_}" height="{ch_}" rx="8"/></clipPath>'
                     f'<g clip-path="url(#c0)"><rect x="{x - 160}" y="{y}" width="160" height="{ch_}" fill="url(#shine)">'
                     f'<animate attributeName="x" values="{x - 160};{x + cw_};{x + cw_}" keyTimes="0;.55;1" dur="4.5s" repeatCount="indefinite"/></rect></g>')
        hx, hy, hr = x + 38, y + 32, 23
        hp = " ".join(f"{hx + hr * math.cos(math.radians(30 + 60 * i)):.1f},{hy + hr * math.sin(math.radians(30 + 60 * i)):.1f}" for i in range(6))
        b.append(f'<polygon points="{hp}" fill="{col}" fill-opacity=".1" stroke="{col}" stroke-width="1.4"'
                 + (' filter="url(#glow)"' if k == 0 else "") + "/>")
        b.append(text(hx, hy + 4, rank, 10.5 if len(rank) < 5 else 9.5, col, 800, anchor="middle"))
        b.append(text(x + 74, y + 27, title, 13.5, C["text"], 800))
        b.append(text(x + 74, y + 46, sub, 11, C["muted"], 400))
        b.append(text(x + cw_ - 14, y + 22, yr, 10.5, C["dim"], 700, anchor="end"))
    write("guild.svg", W, H, "\n".join(b), "Guild records: honours and service",
          "UIDAI Data Hackathon 2026 1st prize (Rs 2,00,000, about 15,000 teams); Capital One Launchpad top 14 of 5,073; "
          "ChemEnigma IISc 1st; StatusCode1 and StatusCode0 1st; AAAI and ICWSM reviewer; FIRE 2026 track co-organizer; "
          "CBSE district-level guest lecturer; Slashdot president; Qiskit Fall Fest 2025 organizer.", defs=defs)


# ── 05 · item box ──────────────────────────────────────────────────────────
INVENTORY = [
    ("ALCHEMY", "computational chem & bio", "amber",
     ["Gaussian", "Q. ESPRESSO", "ORCA", "LAMMPS", "GROMACS", "VMD", "OVITO", "PyMOL", "ChimeraX", "AutoDock", "ASE", "MDAnalysis"]),
    ("ARCANA", "ML · LLMs · retrieval", "cyan",
     ["PyTorch", "Transformers", "MoE", "LoRA·QLoRA", "FAISS", "BM25/Lucene", "LangChain", "Ollama", "vLLM", "HF Datasets", "scikit-learn", "XGBoost"]),
    ("RUNES", "languages & formal proof", "violet",
     ["Python", "C / C++", "Lean 4", "Mathlib", "Rust", "Kotlin", "TypeScript", "Fortran", "Java", "Bash", "SQL", "LaTeX"]),
    ("ARTIFICE", "systems · web · HPC", "green",
     ["React", "Three.js", "WebGL/GLSL", "Django", "Flask", "Node.js", "WebRTC", "Android", "GTK4", "Docker", "CUDA/MPI", "GH Actions"]),
]


def _icon(school, x, y, col):
    if school == "ALCHEMY":
        pts = " ".join(f"{x + 6 * math.cos(math.radians(-90 + 60 * i)):.1f},{y + 6 * math.sin(math.radians(-90 + 60 * i)):.1f}" for i in range(6))
        return f'<polygon points="{pts}" fill="none" stroke="{col}" stroke-width="1.3"/>'
    if school == "ARCANA":
        return (f'<path d="M{x - 5},{y + 4} L{x},{y - 5} L{x + 5},{y + 4} Z" fill="none" stroke="{col}" stroke-opacity=".6"/>'
                + "".join(f'<circle cx="{px}" cy="{py}" r="1.9" fill="{col}"/>' for px, py in ((x - 5, y + 4), (x, y - 5), (x + 5, y + 4))))
    if school == "RUNES":
        return (f'<path d="M{x},{y - 6} L{x + 6},{y} L{x},{y + 6} L{x - 6},{y} Z" fill="none" stroke="{col}" stroke-width="1.3"/>'
                f'<circle cx="{x}" cy="{y}" r="1.6" fill="{col}"/>')
    return (f'<circle cx="{x}" cy="{y}" r="4" fill="none" stroke="{col}" stroke-width="1.3"/>'
            + "".join(f'<line x1="{x + 4 * math.cos(a):.1f}" y1="{y + 4 * math.sin(a):.1f}" x2="{x + 6.5 * math.cos(a):.1f}" y2="{y + 6.5 * math.sin(a):.1f}" stroke="{col}" stroke-width="1.6"/>'
                      for a in (0, math.pi / 2, math.pi, 3 * math.pi / 2)))


def build_inventory():
    W, H = 1000, 400
    n = sum(len(i[3]) for i in INVENTORY)
    b = [K.frame(W, H, C["gold"], "05", "ITEM BOX", "アイテムボックス", f"{n} ITEMS · SORTED BY SCHOOL")]
    defs = ('<linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
            '<stop offset=".5" stop-color="#fff" stop-opacity=".07"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>')
    for c, (school, sub, ckey, items) in enumerate(INVENTORY):
        col = C[ckey]
        x0 = 30 + c * 240
        b.append(text(x0, 88, school, 14, col, 800, ls=3))
        b.append(text(x0, 105, sub, 10.5, C["muted"], 400))
        b.append(f'<rect x="{x0}" y="114" width="220" height="1" fill="{col}" opacity=".4"/>')
        for k, item in enumerate(items):
            x = x0 + (k % 2) * 114
            y = 126 + (k // 2) * 42
            b.append(f'<rect x="{x}" y="{y}" width="106" height="34" rx="5" fill="{C["panel2"]}" stroke="{col}" stroke-opacity=".3"/>')
            b.append(f'<rect x="{x + 2}" y="{y + 2}" width="102" height="1" fill="#fff" opacity=".05"/>')
            b.append(_icon(school, x + 13, y + 17, col))
            b.append(text(x + 24, y + 21.5, item, 11 if len(item) <= 10 else 10, C["text"], 700))
    b.append(f'<rect x="-300" y="60" width="300" height="{H - 80}" fill="url(#sweep)" transform="skewX(-20)">'
             f'<animate attributeName="x" values="-300;1300;1300" keyTimes="0;.6;1" dur="7s" repeatCount="indefinite"/></rect>')
    write("inventory.svg", W, H, "\n".join(b), "Item box: tools and languages",
          "Alchemy: " + ", ".join(INVENTORY[0][3]) + ". Arcana: " + ", ".join(INVENTORY[1][3]) + ". Runes: "
          + ", ".join(INVENTORY[2][3]) + ". Artifice: " + ", ".join(INVENTORY[3][3]) + ".", defs=defs)


# ── small pieces: divider, nav, buttons, footer ────────────────────────────
def build_divider():
    W, H = 1000, 36
    b = []
    for col, ph in ((C["amber"], 0), (C["cyan"], math.pi)):
        pts = [(x, 18 + 7 * math.sin(2 * math.pi * x / 500 + ph) * math.sin(math.pi * x / W)) for x in range(0, W + 1, 20)]
        b.append(f'<path d="{K.catmull_path(pts)}" fill="none" stroke="{col}" stroke-opacity=".55" stroke-width="1.2"/>')
    b.append(f'<circle r="2.6" fill="{C["amber_hot"]}" filter="url(#glow)"><animateMotion path="M0,18 L1000,18" dur="6s" repeatCount="indefinite"/></circle>')
    b.append(f'<g transform="translate(500 18) rotate(45)"><rect x="-5" y="-5" width="10" height="10" fill="{C["bg"]}" stroke="{C["gold"]}" stroke-width="1.5"/></g>')
    write("divider.svg", W, H, "\n".join(b), "divider", "Two crossing worldlines")


NAV = [("01", "STATUS", "ステータス", "cyan"), ("02", "WORLDLINES", "世界線", "amber"), ("03", "MAIN QUEST", "メインクエスト", "violet"),
       ("04", "GADGETS", "発明品", "amber"), ("05", "SIDE QUESTS", "サイドクエスト", "green"), ("06", "D-MAIL", "Dメール", "gold")]


def build_nav():
    W, H = 180, 48
    for k, (idx, label, jp, ckey) in enumerate(NAV):
        col = C[ckey]
        b = [f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="8" fill="{C["bg"]}" stroke="{col}" stroke-opacity=".55" stroke-width="1.4">'
             f'<animate attributeName="stroke-opacity" values=".35;.95;.35" dur="3s" begin="{k * .5}s" repeatCount="indefinite"/></rect>',
             f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="8" fill="url(#dots)"/>',
             f'<g transform="translate(18 24) rotate(45)"><rect x="-4" y="-4" width="8" height="8" fill="{col}"/></g>',
             text(32, 22, label, 12.5, C["text"], 800, ls=2),
             f'<text x="32" y="38" font-size="10" font-weight="700" fill="{C["muted"]}">{tspan(idx + "  ", "m", C["dim"])}{tspan(jp, "j")}</text>']
        write(f"nav_{label.lower().replace(' ', '_').replace('-', '')}.svg", W, H, "\n".join(b), label, f"Jump to {label.lower()}")


def build_dmail_buttons():
    W, H = 320, 72
    btns = [("alpha", "SHIFT TOWARD α", "chemistry · −0.01 to −0.10", C["amber"], "α"),
            ("beta", "SHIFT TOWARD β", "AI / ML · +0.01 to +0.10", C["cyan"], "β"),
            ("steins", "PULL TO STEINS GATE", "halve the distance to 1.048596", C["gold"], "SG")]
    for k, (key, title, sub, col, sym) in enumerate(btns):
        b = [f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="10" fill="{C["bg"]}" stroke="{col}" stroke-width="1.5">'
             f'<animate attributeName="stroke-opacity" values=".4;1;.4" dur="2.6s" begin="{k * .6}s" repeatCount="indefinite"/></rect>',
             f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="10" fill="url(#dots)"/>',
             f'<circle cx="38" cy="36" r="22" fill="{col}" fill-opacity=".08" stroke="{col}" stroke-opacity=".7"/>',
             text(38, 44 if sym != "SG" else 41, sym, 24 if sym != "SG" else 15, col, 800, anchor="middle", extra='filter="url(#glow)"'),
             text(74, 33, title, 14, col, 800, ls=1.5),
             text(74, 52, sub, 11, C["muted"], 400)]
        write(f"btn_{key}.svg", W, H, "\n".join(b), title, f"Send a D-mail: {title.lower()}")


def build_footer():
    W, H = 1000, 200
    b = [f'<rect width="{W}" height="{H}" rx="16" fill="{C["bg"]}"/>', f'<rect width="{W}" height="{H}" rx="16" fill="url(#dots)"/>',
         K.gear(70, 160, 46, 14, 7, C["amber"], 1.1, .16, 60), K.gear(140, 186, 24, 9, 6, C["amber"], 1, .16, 34, rev=True),
         K.gear(934, 44, 40, 12, 7, C["cyan"], 1.1, .14, 55, rev=True), K.gear(872, 18, 20, 8, 5, C["cyan"], 1, .14, 28)]
    tube_w, tube_h, gap = 30, 58, 6
    x0 = (W - (8 * tube_w + 7 * gap)) / 2
    b.append(K.nixie_row(x0, 24, "1.048596", tube_w, tube_h, gap, uid="ft"))
    b.append(text(500, 128, "エル・プサイ・コングルゥ", 20, C["amber"], 700, anchor="middle", jp=True, ls=4, extra='filter="url(#glow)"'))
    b.append(text(500 + 1.5, 154, "EL PSY KONGROO", 12, C["muted"], 700, anchor="middle", ls=3))
    b.append(text(500 + 1, 178, "LAB MEMBER 076 · SIGNING OFF · SEE YOU ON THE NEXT WORLDLINE", 9.5, C["dim"], 700, anchor="middle", ls=2))
    b.append(f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="15.5" fill="none" stroke="{C["line"]}" stroke-width="1.5"/>')
    write("footer.svg", W, H, "\n".join(b), "El Psy Kongroo", "Footer: small nixie meter reading 1.048596 and the words El Psy Kongroo.")


def build_live_meter():
    state = dmail.load_state()
    body = dmail.render_meter(state)
    ascii_ = "".join(chr(c) for c in range(32, 127)) + "αβΔ→×·—–…"
    fonts = fonts_css_for(body, extra_m=ascii_)
    dmail.write_all(state, fonts_css=fonts)
    print(f"  dmail_meter.svg        {len(dmail.METER.read_text()) / 1024:6.1f} KB  (live; rewritten by the D-mail action)")


def main():
    ensure_jp_font()
    OUT.mkdir(parents=True, exist_ok=True)
    for fn in (build_hero, build_status, build_worldlines, build_mainquest, build_guild, build_inventory,
               build_divider, build_nav, build_dmail_buttons, build_footer, build_live_meter):
        fn()


if __name__ == "__main__":
    main()
