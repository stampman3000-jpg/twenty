#!/usr/bin/env python3
"""Procedural 4x-supersampled MS-20 / AT20V UI artwork generator for Akai MPC (1280x628).

Generates:
  - Panel artwork for Page 1 (SYNTH), Page 2 (PATCHBAY/ESP), Page 3 (EXTENSIONS)
  - Fluted vintage MS-20 rotary knob filmstrips (pots + multi-way selectors)
  - 28-frame chrome 1/4" jack + 6-color numbered cable plug filmstrip
  - Glowing red LED filmstrips, control wheel strip, tactile action buttons, alpha=4 hit plates
  - ui_layout_manifest.json (single source of truth for gen_skins.py and render_preview.py)

All artwork is original procedural graphics inspired by the 1978 Korg MS-20 and Audio Tools AT20V.
Licensed under GNU AGPLv3.
"""
import json
import math
import os
import random
import sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIN_DIRS = [
    os.path.join(ROOT, "plugins", "at20_mpc", "skins"),
    os.path.join(ROOT, "plugins", "at20_fx", "skins"),
]
MANIFEST_PATH = os.path.join(ROOT, "tools", "ui_layout_manifest.json")

W, H = 1280, 628
SS = 2  # 2x supersampling for crisp anti-aliased 1280x628 panels (2560x1256 internal)

# Authentic matte-black brushed faceplate palette (restrained vintage aesthetic)
BG_BASE = (22, 23, 25, 255)
INK = (234, 232, 224, 255)
INK_DIM = (166, 164, 156, 255)
INK_LINE = (218, 216, 208, 255)
DIVIDER = (224, 222, 214, 255)
PANEL_INSET = (14, 15, 17, 255)
ACCENT_GOLD = (224, 172, 74, 255)
ACCENT_RED = (204, 48, 36, 255)

# Exact AT20V 6 cable colors (black uses deep charcoal with warm copper/amber badge ring for contrast)
CABLE_COLORS = [
    ("red",    (186, 36, 30),   (255, 245, 240)),  # 0 Red
    ("blue",   (38, 86, 178),   (240, 246, 255)),  # 1 Blue
    ("yellow", (218, 164, 30),  (20, 18, 14)),     # 2 Yellow
    ("green",  (46, 142, 62),   (242, 255, 244)),  # 3 Green
    ("white",  (220, 218, 210), (20, 20, 22)),     # 4 White
    ("black",  (196, 102, 34),  (255, 246, 234)),  # 5 Copper/Charcoal (high visibility on black panel)
]
SLOT_CHARS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C']

FONT_CANDIDATES = [
    ("/System/Library/Fonts/HelveticaNeue.ttc", 10),  # Condensed Bold
    ("/System/Library/Fonts/HelveticaNeue.ttc", 1),   # Bold
    ("/System/Library/Fonts/Helvetica.ttc", 1),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0),
]
FONT_REG_CANDIDATES = [
    ("/System/Library/Fonts/HelveticaNeue.ttc", 0),
    ("/System/Library/Fonts/Helvetica.ttc", 0),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 0),
]
FALLBACK_UNICODE = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"


def pick_font_path(cands):
    for p, idx in cands:
        if os.path.isfile(p):
            return p, idx
    return None, 0


FONT_PATH, FONT_IDX = pick_font_path(FONT_CANDIDATES)
FONT_REG_PATH, FONT_REG_IDX = pick_font_path(FONT_REG_CANDIDATES)
_font_cache = {}


def get_font(size, bold=True):
    key = (int(round(size)), bold)
    if key not in _font_cache:
        p, idx = (FONT_PATH, FONT_IDX) if bold else (FONT_REG_PATH, FONT_REG_IDX)
        if p:
            _font_cache[key] = ImageFont.truetype(p, max(8, int(round(size))), index=idx)
        else:
            _font_cache[key] = ImageFont.load_default()
    return _font_cache[key]


def get_unicode_font(size):
    key = ("uni", int(round(size)))
    if key not in _font_cache:
        if os.path.isfile(FALLBACK_UNICODE):
            _font_cache[key] = ImageFont.truetype(FALLBACK_UNICODE, max(8, int(round(size))))
        else:
            _font_cache[key] = get_font(size, True)
    return _font_cache[key]


def make_metal_canvas(w, h, seed=20):
    """Create subtly brushed, micro-textured near-black anodized metal faceplate."""
    rng = random.Random(seed)
    img = Image.new("RGBA", (w, h), BG_BASE)
    px = img.load()
    # Subtle vertical top-to-bottom studio gradient + horizontal brushed grain
    row_noise = [rng.randint(-3, 3) for _ in range(h)]
    for y in range(h):
        grad = int(round(6.0 * (1.0 - y / float(h)) - 2.0))
        rn = row_noise[y]
        r0 = max(10, min(42, BG_BASE[0] + grad + rn))
        g0 = max(10, min(42, BG_BASE[1] + grad + rn))
        b0 = max(12, min(46, BG_BASE[2] + grad + rn))
        for x in range(w):
            # Subtle micro-grain
            v = ((x * 2654435761 ^ y * 2246822519) >> 28) & 3
            d = v - 1
            px[x, y] = (r0 + d, g0 + d, b0 + d, 255)
    # Soft outer bezel shadow/highlight
    dr = ImageDraw.Draw(img)
    dr.rectangle([0, 0, w - 1, h - 1], outline=(42, 44, 48, 255), width=2)
    dr.line([(2, 2), (w - 3, 2)], fill=(54, 56, 62, 255), width=2)
    dr.line([(2, h - 3), (w - 3, h - 3)], fill=(10, 10, 12, 255), width=2)
    # Four subtle corner Phillips panel screws
    for sx, sy in [(14 * SS, 14 * SS), (w - 14 * SS, 14 * SS), (14 * SS, h - 14 * SS), (w - 14 * SS, h - 14 * SS)]:
        r = 6 * SS
        dr.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(32, 34, 38, 255), outline=(10, 10, 12, 255), width=2)
        dr.ellipse([sx - r + 2, sy - r + 2, sx + r - 2, sy + r - 2], outline=(58, 60, 66, 255), width=1)
        dr.line([(sx - r // 2, sy - 1), (sx + r // 2, sy + 1)], fill=(14, 14, 16, 255), width=2)
        dr.line([(sx - 1, sy - r // 2), (sx + 1, sy + r // 2)], fill=(14, 14, 16, 255), width=2)
    return img


def draw_text(img, s, cx, cy, size, fill=INK, align="center", cond=0.80, bold=True, track=0.04):
    """Draw condensed MS-20 style silkscreen lettering at 2x coordinates."""
    f = get_font(size, bold=bold)
    uf = get_unicode_font(size)
    lines = s.split("\n")
    lh = size * 1.12
    total_h = lh * len(lines)
    for li, line in enumerate(lines):
        if not line:
            continue
        fonts = [uf if c in "∝′↘↗−" else f for c in line]
        widths = [ff.getlength(c) for ff, c in zip(fonts, line)]
        tw = sum(widths) + track * size * max(0, len(line) - 1)
        pad = int(size * 0.6)
        layer = Image.new("RGBA", (max(4, int(tw + pad * 2)), max(4, int(size * 1.5))), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        x = float(pad)
        for c, cw, ff in zip(line, widths, fonts):
            ld.text((x, size * 0.18), c, font=ff, fill=fill)
            x += cw + track * size
        if abs(cond - 1.0) > 0.01:
            nw = max(1, int(round(layer.width * cond)))
            layer = layer.resize((nw, layer.height), Image.LANCZOS)
        real_w = tw * cond
        y0 = cy - total_h / 2.0 + li * lh - size * 0.16
        if align == "center":
            x0 = cx - real_w / 2.0 - pad * cond
        elif align == "left":
            x0 = cx - pad * cond
        else:
            x0 = cx - real_w - pad * cond
        img.alpha_composite(layer, (int(round(x0)), int(round(y0))))


# Authentic MS-20 waveform symbols
SYMS = {
    "tri":     [[(0, 1), (0.5, 0), (1, 1)]],
    "saw":     [[(0, 1), (0.14, 0), (1, 1)]],
    "square":  [[(0, 1), (0.15, 1), (0.15, 0), (0.75, 0), (0.75, 1), (1, 1)]],
    "pulse":   [[(0, 1), (0.25, 1), (0.25, 0), (0.45, 0), (0.45, 1), (1, 1)]],
    "line":    [[(0, 1), (1, 1)]],
    "noise":   [[(0, .7), (.1, .15), (.2, .85), (.3, .1), (.4, .9), (.5, .25), (.6, .75), (.7, .05), (.8, .85), (.9, .2), (1, .6)]],
    "pwm":     [[(0, 1), (0, 0), (.32, 0), (.32, 1), (.44, 1)], [(.56, 1), (.68, 1), (.68, 0), (.82, 0), (.82, 1), (1, 1)], [(.35, .5), (.65, .5)]],
    "mgtop":   [[(0, 1), (0, 0), (.3, 0), (.3, 1), (.6, 1), (.6, 0), (.9, 0)], [(.2, 1.55), (.45, 1.2), (.7, 1.55)]],
    "mgleft":  [[(0, 1), (0, 0), (.15, 0), (.15, 1), (.45, 1), (.45, 0), (.55, 0)], [(.62, 0), (.95, 1)]],
    "mgright": [[(.05, 1), (.38, 0)], [(.45, 1), (.45, 0), (.75, 0), (.75, 1), (.85, 1), (.85, 0), (1, 0)]],
}


def draw_symbol(dr, name, cx, cy, size, fill=INK):
    w = size * (1.65 if name in ("noise", "pwm", "mgtop", "mgleft", "mgright") else 1.05)
    lw = max(2, int(round(size * 0.11)))
    for stroke in SYMS[name]:
        pts = [(cx - w / 2.0 + x * w, cy - size / 2.0 + y * size) for x, y in stroke]
        dr.line(pts, fill=fill, width=lw, joint="curve")


def draw_knob_scale(img, dr, cx, cy, r_px, label, kind="pot", ticks=None, start_deg=-150.0, end_deg=150.0):
    """Draw MS-20 dial scale ticks, numbers/symbols, and bottom label around (cx, cy) in 1x coords."""
    X, Y, R = cx * SS, cy * SS, r_px * SS
    a0, a1 = math.radians(start_deg), math.radians(end_deg)
    # Subtle dark recessed shadow ring under knob
    dr.ellipse([X - R * 1.02, Y - R * 1.02, X + R * 1.02, Y + R * 1.02], fill=(10, 11, 13, 255))

    if ticks is None:
        if kind == "pot":
            ticks = [(i / 10.0, str(i) if i in (0, 2, 4, 5, 6, 8, 10) else "") for i in range(11)]
        elif kind == "bipolar":
            ticks = [(i / 10.0, {0: "-5", 2: "-3", 5: "0", 8: "+3", 10: "+5"}.get(i, "")) for i in range(11)]
        elif kind == "pw":
            ticks = [(i / 10.0, {0: "sym:square", 10: "sym:line"}.get(i, "")) for i in range(11)]
        elif kind == "mgwave":
            ticks = [(i / 10.0, {0: "sym:mgleft", 5: "sym:mgtop", 10: "sym:mgright"}.get(i, "")) for i in range(11)]
        else:
            ticks = []

    is_choice = (kind == "choice")
    r_in = R * 1.09
    r_out = R * (1.36 if is_choice else 1.24)
    r_txt = R * (1.62 if is_choice else 1.44)
    num_sz = (19 if r_px >= 34 else 17)

    for t, txt in ticks:
        a = a0 + (a1 - a0) * t
        sx, sy = math.sin(a), -math.cos(a)
        major = (txt != "")
        ro = r_out if major else R * 1.19
        dr.line([(X + sx * r_in, Y + sy * r_in), (X + sx * ro, Y + sy * ro)],
                fill=INK if major else INK_DIM, width=max(2, int(SS * (1.3 if major else 1.0))))
        if not txt:
            continue
        tx, ty = X + sx * r_txt, Y + sy * r_txt
        if txt.startswith("sym:"):
            nm = txt[4:]
            draw_symbol(dr, nm, tx, ty, num_sz * (0.85 if nm in ("tri", "saw", "square", "pulse", "line") else 0.72))
        else:
            draw_text(img, txt, tx, ty, num_sz * (1.05 if len(txt) <= 3 else 0.92), cond=0.82, track=0.01)

    if label:
        ly = Y + R * (1.46 if r_px >= 34 else 1.56)
        draw_text(img, label, X, ly, 21 if r_px >= 34 else 19, cond=0.78, track=0.04)


def draw_arrow(dr, x0, y0, x1, y1, w=2.0, head=8.0):
    dr.line([(x0 * SS, y0 * SS), (x1 * SS, y1 * SS)], fill=INK_LINE, width=max(2, int(round(w * SS))))
    a = math.atan2(y1 - y0, x1 - x0)
    p1 = (x1 - head * math.cos(a - 0.45), y1 - head * math.sin(a - 0.45))
    p2 = (x1 - head * math.cos(a + 0.45), y1 - head * math.sin(a + 0.45))
    dr.polygon([(x1 * SS, y1 * SS), (p1[0] * SS, p1[1] * SS), (p2[0] * SS, p2[1] * SS)], fill=INK_LINE)


def draw_polyline(dr, pts, w=2.0):
    dr.line([(x * SS, y * SS) for x, y in pts], fill=INK_LINE, width=max(2, int(round(w * SS))), joint="curve")


def draw_block_box(img, dr, x0, y0, x1, y1, label, font_sz=15):
    dr.rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], fill=(26, 27, 30, 255), outline=INK_LINE, width=max(2, int(1.6 * SS)))
    draw_text(img, label, (x0 + x1) * 0.5 * SS, (y0 + y1) * 0.5 * SS, font_sz, cond=0.72, track=0.02)


def draw_amp_tri(img, dr, x0, y0, x1, y1, label, font_sz=15):
    pts = [(x0 * SS, y0 * SS), (x1 * SS, (y0 + y1) * 0.5 * SS), (x0 * SS, y1 * SS)]
    dr.polygon(pts, fill=(26, 27, 30, 255), outline=INK_LINE, width=max(2, int(1.6 * SS)))
    draw_text(img, label, (x0 + (x1 - x0) * 0.36) * SS, (y0 + y1) * 0.5 * SS, font_sz, cond=0.72)


# =============================================================================
# 1. PAGE 1 — SYNTH PANEL (bg_synth.png)
# =============================================================================
def build_page1():
    img = make_metal_canvas(W * SS, H * SS, seed=101)
    dr = ImageDraw.Draw(img)

    # Authentic MS-20 white divider lines (7 columns)
    div_w = int(2.6 * SS)
    # Vertical dividers between modules
    for vx, y0, y1 in [
        (190, 16, 612),   # VCO1 | VCO2
        (368, 16, 612),   # VCO2 | Mixer+FM
        (524, 16, 612),   # Mixer+FM | HPF
        (686, 16, 612),   # HPF | LPF
        (848, 16, 612),   # LPF | VCA / MG
        (985, 240, 612),  # MG | EG1
        (1122, 16, 612),  # VCA+EG1 | EG2
    ]:
        dr.line([(vx * SS, y0 * SS), (vx * SS, y1 * SS)], fill=DIVIDER, width=div_w)

    # Horizontal module dividers
    dr.line([(16 * SS, 464 * SS), (364 * SS, 464 * SS)], fill=DIVIDER, width=div_w)     # VCO1/2 | Porta/Tune
    dr.line([(372 * SS, 344 * SS), (844 * SS, 344 * SS)], fill=DIVIDER, width=div_w)    # Mixer/Filt | Mod
    dr.line([(852 * SS, 238 * SS), (1118 * SS, 238 * SS)], fill=DIVIDER, width=div_w)   # VCA | MG+EG1

    # Module Titles
    draw_text(img, "VOLTAGE CONTROLLED\nOSCILLATOR 1", 101 * SS, 36 * SS, 23, cond=0.70, track=0.05)
    draw_text(img, "VOLTAGE CONTROLLED\nOSCILLATOR 2", 279 * SS, 36 * SS, 23, cond=0.70, track=0.05)
    draw_text(img, "VCO MIXER", 446 * SS, 34 * SS, 23, cond=0.72, track=0.06)
    draw_text(img, "VOLTAGE CONTROLLED\nHIGHPASS FILTER", 605 * SS, 36 * SS, 22, cond=0.68, track=0.04)
    draw_text(img, "VOLTAGE CONTROLLED\nLOWPASS FILTER", 767 * SS, 36 * SS, 22, cond=0.68, track=0.04)
    draw_text(img, "VOLTAGE CONTROLLED AMPLIFIER", 985 * SS, 32 * SS, 22, cond=0.72, track=0.06)
    draw_text(img, "ENVELOPE\nGENERATOR 2", 1195 * SS, 34 * SS, 22, cond=0.72, track=0.05)

    draw_text(img, "PORTAMENTO", 101 * SS, 480 * SS, 21, cond=0.74, track=0.06)
    draw_text(img, "MASTER TUNE", 279 * SS, 480 * SS, 21, cond=0.74, track=0.06)
    draw_text(img, "FREQUENCY\nMODULATION", 446 * SS, 368 * SS, 19, cond=0.72, track=0.05)
    draw_text(img, "CUTOFF FREQ\nMODULATION", 605 * SS, 368 * SS, 19, cond=0.72, track=0.05)
    draw_text(img, "CUTOFF FREQ\nMODULATION", 767 * SS, 368 * SS, 19, cond=0.72, track=0.05)
    draw_text(img, "MODULATION\nGENERATOR", 916 * SS, 266 * SS, 20, cond=0.70, track=0.05)
    draw_text(img, "ENVELOPE\nGENERATOR 1", 1053 * SS, 264 * SS, 20, cond=0.70, track=0.05)

    # Subtle recessed dark VCA status display box (left side of VCA module)
    dr.rounded_rectangle([858 * SS, 54 * SS, 1008 * SS, 198 * SS], radius=6 * SS,
                         fill=(12, 13, 15, 255), outline=(66, 68, 74, 255), width=2)
    draw_text(img, "Twenty", 933 * SS, 72 * SS, 20, fill=ACCENT_GOLD, cond=0.82, track=0.10)
    draw_text(img, "EG 2 & EXT", 933 * SS, 216 * SS, 18, fill=INK_DIM, cond=0.76, track=0.06)
    # Subtle separator inside status screen
    dr.line([(870 * SS, 132 * SS), (996 * SS, 132 * SS)], fill=(44, 46, 52, 255), width=2)

    # Knobs specification: (param_idx, id, cx, cy, size, filmstrip, frames, label, kind, ticks, start_deg, end_deg)
    knobs = [
        # VCO 1 + Portamento
        (1,  "vco1_wave",   101, 126, 76, "knob_big_4way.png",  4, "WAVE FORM", "choice",
         [(0.0, "sym:tri"), (1/3, "sym:saw"), (2/3, "sym:pwm"), (1.0, "sym:noise")], -50, 50),
        (2,  "vco1_pw",     101, 256, 64, "knob_small_pot.png", 65, "PW", "pw", None, -150, 150),
        (3,  "vco1_scale",  101, 386, 76, "knob_big_4way.png",  4, "SCALE", "choice",
         [(0.0, "32′"), (1/3, "16′"), (2/3, "8′"), (1.0, "4′")], -50, 50),
        (7,  "portamento",  101, 548, 64, "knob_small_pot.png", 65, "TIME", "pot", None, -150, 150),

        # VCO 2 + Master Tune
        (4,  "vco2_wave",   279, 126, 76, "knob_big_4way.png",  4, "WAVE FORM", "choice",
         [(0.0, "sym:saw"), (1/3, "sym:square"), (2/3, "sym:pulse"), (1.0, "RING")], -50, 50),
        (5,  "vco2_pitch",  279, 256, 64, "knob_small_pot.png", 65, "PITCH", "bipolar", None, -150, 150),
        (6,  "vco2_scale",  279, 386, 76, "knob_big_4way.png",  4, "SCALE", "choice",
         [(0.0, "16′"), (1/3, "8′"), (2/3, "4′"), (1.0, "2′")], -50, 50),
        (8,  "master_tune", 279, 548, 64, "knob_small_pot.png", 65, "TUNE", "bipolar", None, -150, 150),

        # Mixer + Freq Mod
        (9,  "vco1_level",  446, 126, 64, "knob_small_pot.png", 65, "VCO 1 LEVEL", "pot", None, -150, 150),
        (10, "vco2_level",  446, 266, 64, "knob_small_pot.png", 65, "VCO 2 LEVEL", "pot", None, -150, 150),
        (11, "fm_mg",       446, 434, 64, "knob_small_pot.png", 65, "MG/T.EXT", "pot", None, -150, 150),
        (12, "fm_eg1",      446, 548, 64, "knob_small_pot.png", 65, "EG1/EXT", "pot", None, -150, 150),

        # HPF
        (13, "hpf_cutoff",  605, 126, 76, "knob_big_pot.png",   65, "CUTOFF FREQ", "pot", None, -150, 150),
        (14, "hpf_peak",    605, 266, 64, "knob_small_pot.png", 65, "PEAK", "pot", None, -150, 150),
        (15, "hpf_mod_mg",  605, 434, 64, "knob_small_pot.png", 65, "MG/T.EXT", "pot", None, -150, 150),
        (16, "hpf_mod_eg2", 605, 548, 64, "knob_small_pot.png", 65, "EG2/EXT", "pot", None, -150, 150),

        # LPF
        (17, "lpf_cutoff",  767, 126, 76, "knob_big_pot.png",   65, "CUTOFF FREQ", "pot", None, -150, 150),
        (18, "lpf_peak",    767, 266, 64, "knob_small_pot.png", 65, "PEAK", "pot", None, -150, 150),
        (19, "lpf_mod_mg",  767, 434, 64, "knob_small_pot.png", 65, "MG/T.EXT", "pot", None, -150, 150),
        (20, "lpf_mod_eg2", 767, 548, 64, "knob_small_pot.png", 65, "EG2/EXT", "pot", None, -150, 150),

        # Main Volume (inside VCA top-right)
        (0,  "volume",     1066, 128, 64, "knob_small_pot.png", 65, "VOLUME", "pot", None, -150, 150),

        # MG
        (21, "mg_wave",     916, 434, 64, "knob_small_pot.png", 65, "WAVE FORM", "mgwave", None, -150, 150),
        (22, "mg_freq",     916, 548, 64, "knob_small_pot.png", 65, "FREQUENCY", "pot", None, -150, 150),

        # EG1
        (23, "eg1_delay",  1053, 326, 60, "knob_med_pot.png",   65, "DELAY", "pot", None, -150, 150),
        (24, "eg1_attack", 1053, 438, 60, "knob_med_pot.png",   65, "ATTACK", "pot", None, -150, 150),
        (25, "eg1_release",1053, 550, 60, "knob_med_pot.png",   65, "RELEASE", "pot", None, -150, 150),

        # EG2
        (26, "eg2_hold",   1195, 110, 60, "knob_med_pot.png",   65, "HOLD", "pot", None, -150, 150),
        (27, "eg2_attack", 1195, 220, 60, "knob_med_pot.png",   65, "ATTACK", "pot", None, -150, 150),
        (28, "eg2_decay",  1195, 330, 60, "knob_med_pot.png",   65, "DECAY", "pot", None, -150, 150),
        (29, "eg2_sustain",1195, 440, 60, "knob_med_pot.png",   65, "SUSTAIN", "pot", None, -150, 150),
        (30, "eg2_release",1195, 550, 60, "knob_med_pot.png",   65, "RELEASE", "pot", None, -150, 150),
    ]

    manifest_knobs = []
    for pidx, kid, cx, cy, sz, strip, frames, lbl, kind, ticks, a0, a1 in knobs:
        draw_knob_scale(img, dr, cx, cy, sz * 0.44, lbl, kind=kind, ticks=ticks, start_deg=a0, end_deg=a1)
        manifest_knobs.append({
            "param": pidx, "id": kid, "cx": cx, "cy": cy, "size": sz,
            "strip": strip, "frames": frames, "bipolar": (kind == "bipolar"),
        })

    leds = [
        {"param": 175, "id": "led_mg",  "cx": 916, "cy": 334, "size": 20, "strip": "led_2.png", "frames": 2},
        {"param": 176, "id": "led_eg1", "cx": 1100, "cy": 264, "size": 20, "strip": "led_4.png", "frames": 4},
    ]
    labels = [
        {"param": 180, "id": "stat_preset", "x": 862, "y": 92,  "w": 142, "h": 34, "size": 16, "color": "ffe8e6e0"},
        {"param": 181, "id": "stat_last",   "x": 862, "y": 144, "w": 142, "h": 42, "size": 17, "color": "ffe0ac4a"},
    ]

    out = img.resize((W, H), Image.LANCZOS).convert("RGB")
    return out, {"knobs": manifest_knobs, "leds": leds, "labels": labels}


# =============================================================================
# 2. PAGE 2 — PATCHBAY / EXTERNAL SIGNAL PROCESSOR (bg_patch.png)
# =============================================================================
def build_page2():
    img = make_metal_canvas(W * SS, H * SS, seed=202)
    dr = ImageDraw.Draw(img)

    # Transform original MS-20 patchbay coordinates (u: 942..1568, v: 24..510) -> (x: 24..968, y: 18..612)
    def px(u): return 28.0 + (u - 952.0) * 1.505
    def py(v): return 22.0 + (v - 20.0) * 1.215

    # Exact 35 jacks from AT20V Layout.generated.h (preserving authentic relative positions!)
    RAW_JACKS = [
        # (id, u, v, isOut, top_lbl, bot_lbl)
        ("total_in",    971.8, 109.9, False, "TOTAL",      "-5V~+5V"),
        ("freq_in",    1055.4, 109.9, False, "FREQ",       "-5V~+5V"),
        ("ext_sig_in", 1123.8, 109.9, False, "EXT SIG IN", ""),
        ("hpf_cut_in", 1189.8, 109.9, False, "HPF CUT",    "-5V~+5V"),
        ("lpf_cut_in", 1263.3, 109.9, False, "LPF CUT",    "-5V~+5V"),
        ("gain_in",    1341.9, 109.9, False, "INIT GAIN",  "0V~+5V"),
        ("signal_out", 1537.6,  51.4, True,  "SIGNAL OUT", ""),
        ("phones_out", 1537.6, 109.9, True,  "PHONES",     ""),

        ("mg_tri_out",  971.8, 186.1, True,  "OUT",        ""),
        ("mg_sq_out",  1088.3, 186.1, True,  "OUT",        ""),
        ("eg1_out",    1145.6, 186.1, True,  "OUT",        ""),
        ("eg2_rev_out",1373.6, 186.1, True,  "REV OUT",    ""),
        ("vco2_cv_in", 1422.0, 216.0, False, "VCO2 CV",    ""),
        ("vco12_cv_in",1478.7, 186.1, False, "VCO1+2 CV",  ""),
        ("kbd_cv_out", 1537.0, 186.1, True,  "KBD CV",     ""),

        ("sh_clock_in",1030.0, 245.3, False, "CLOCK",      ""),
        ("eg1_rev_out",1145.6, 245.3, True,  "REV OUT",    ""),
        ("vca_ctrl_in",1203.9, 245.3, False, "CTRL IN",    ""),
        ("eg1_trig_in",1296.5, 245.3, False, "EG1 TRIG",   ""),
        ("kbd_trig_in",1478.7, 245.3, False, "TRIG IN",    ""),
        ("kbd_trig_out",1536.4,245.3, True,  "",           "TRIG OUT"),

        ("sh_in",       971.8, 304.1, False, "IN",         ""),
        ("sh_out",     1087.4, 304.1, True,  "OUT",        ""),
        ("vca_in",     1145.0, 304.1, False, "IN",         ""),
        ("vca_out",    1236.1, 304.1, True,  "OUT",        ""),
        ("pink_out",   1296.5, 304.4, True,  "PINK",       ""),
        ("white_out",  1412.7, 304.4, True,  "WHITE",      ""),
        ("wheel_out",  1476.6, 304.4, True,  "WHEEL",      "-5V~+5V"),
        ("msw_out",    1535.5, 304.4, True,  "MSW",        "GND"),

        ("esp_in",      970.6, 385.4, False, "SIGNAL IN",  ""),
        ("esp_amp_out",1087.4, 385.4, True,  "AMP OUT",    ""),
        ("esp_bpf_out",1204.5, 385.4, True,  "BPF OUT",    ""),
        ("esp_fv_out", 1322.5, 385.4, True,  "F∝V CV",     ""),
        ("esp_env_out",1476.6, 385.4, True,  "ENV OUT",    ""),
        ("esp_trig_out",1534.9,385.4, True,  "TRIG OUT",   ""),
    ]

    # ── Top Synth Block Diagram (authentic MS-20 signal-flow schematic) ──
    by0, by1 = 18, 66
    draw_block_box(img, dr, 36,  by0, 128, by1, "VCO 1", 17)
    draw_block_box(img, dr, 152, by0, 244, by1, "VCO 2", 17)
    draw_block_box(img, dr, 270, by0, 336, by1, "VCO\nMIXER", 15)
    draw_block_box(img, dr, 362, by0, 456, by1, "VC HPF", 17)
    draw_block_box(img, dr, 482, by0, 578, by1, "VC LPF", 17)
    draw_block_box(img, dr, 604, by0, 692, by1, "VCA", 17)
    draw_arrow(dr, 128, 36, 270, 36, 1.6, 6)
    draw_arrow(dr, 244, 50, 270, 50, 1.6, 6)
    draw_arrow(dr, 336, 42, 362, 42, 1.6, 6)
    draw_arrow(dr, 456, 42, 482, 42, 1.6, 6)
    draw_arrow(dr, 578, 42, 604, 42, 1.6, 6)
    draw_arrow(dr, 692, 42, 744, 42, 1.6, 6)
    draw_arrow(dr, 822, 42, 886, 42, 1.6, 6)  # -> SIGNAL OUT

    # Normalled bus arrows from top row jacks up into blocks
    j_total_x = px(971.8); j_freq_x = px(1055.4); j_ext_x = px(1123.8)
    j_hpf_x = px(1189.8); j_lpf_x = px(1263.3); j_gain_x = px(1341.9)
    j_top_y = py(109.9)
    draw_polyline(dr, [(j_total_x, j_top_y - 24), (j_total_x, 82), (j_lpf_x, 82)], 1.4)
    draw_arrow(dr, 82, 82, 82, by1, 1.4, 5)
    draw_arrow(dr, 198, 82, 198, by1, 1.4, 5)
    draw_polyline(dr, [(j_freq_x, j_top_y - 24), (j_freq_x, 90), (82, 90)], 1.4)
    draw_polyline(dr, [(j_ext_x, j_top_y - 24), (j_ext_x, 94), (349, 94), (349, 54)], 1.4)
    draw_arrow(dr, 349, 54, 362, 54, 1.4, 5)
    draw_arrow(dr, j_hpf_x, j_top_y - 24, j_hpf_x, by1, 1.4, 5)
    draw_arrow(dr, j_lpf_x, j_top_y - 24, j_lpf_x, by1, 1.4, 5)
    draw_arrow(dr, j_gain_x, j_top_y - 24, j_gain_x, by1, 1.4, 5)

    # ── Middle Module Boxes: MG, EG1, EG2, KBD ──
    ym0, ym1 = py(186.1) - 20, py(186.1) + 20
    draw_block_box(img, dr, px(971.8) + 28, ym0, px(1088.3) - 28, ym1, "MOD\nGEN", 14)
    draw_block_box(img, dr, px(1145.6) + 28, ym0, px(1265.0), ym1, "EG 1", 16)
    draw_block_box(img, dr, px(1280.0), ym0, px(1373.6) - 28, ym1, "EG 2", 16)
    # Normalled MG -> TOTAL, EG1 -> FREQ, EG2 -> HPF/LPF
    draw_polyline(dr, [(px(971.8) + 18, py(186.1)), (px(971.8) + 28, py(186.1))], 1.4)
    draw_polyline(dr, [(px(1088.3) - 28, py(186.1)), (px(1088.3) - 18, py(186.1))], 1.4)
    draw_polyline(dr, [(px(971.8), py(186.1) - 24), (px(971.8), py(109.9) + 26)], 1.2)
    draw_polyline(dr, [(px(1145.6), py(186.1) - 24), (px(1145.6), 178), (j_freq_x, 178), (j_freq_x, j_top_y + 26)], 1.2)
    draw_polyline(dr, [(px(1300), ym0), (px(1300), 170), (j_hpf_x, 170), (j_hpf_x, j_top_y + 26)], 1.2)
    draw_polyline(dr, [(j_lpf_x, 170), (j_lpf_x, j_top_y + 26)], 1.2)

    # KBD box cleanly centered between KBD CV OUT and KBD TRIG OUT
    draw_block_box(img, dr, px(1517), py(216) - 10, px(1556), py(216) + 10, "KBD", 13)

    # ── Lower Patchbay Boxes: S&H, MVCA, NOISE ──
    yl0, yl1 = py(304.1) - 20, py(304.1) + 20
    draw_block_box(img, dr, px(971.8) + 28, yl0, px(1087.4) - 28, yl1, "SAMPLE\n& HOLD", 13)
    draw_arrow(dr, px(1030.0), py(245.3) + 24, px(1030.0), yl0, 1.4, 5)
    draw_amp_tri(img, dr, px(1145.0) + 32, yl0, px(1236.1) - 32, yl1, "VCA", 14)
    draw_arrow(dr, px(1203.9), py(245.3) + 24, px(1190), yl0 + 10, 1.4, 5)
    draw_block_box(img, dr, px(1296.5) + 28, yl0, px(1412.7) - 28, yl1, "NOISE\nGEN", 14)

    # ── Horizontal Divider above ESP ──
    esp_div_y = 408
    dr.line([(20 * SS, esp_div_y * SS), (972 * SS, esp_div_y * SS)], fill=DIVIDER, width=int(2.4 * SS))
    draw_text(img, "EXTERNAL SIGNAL PROCESSOR", 268 * SS, 422 * SS, 21, cond=0.76, track=0.08)

    # ESP Block Diagram between ESP jacks (y ≈ 466)
    ye = py(385.4)
    draw_amp_tri(img, dr, px(970.6) + 30, ye - 18, px(1087.4) - 30, ye + 18, "AMP", 13)
    draw_block_box(img, dr, px(1087.4) + 28, ye - 18, px(1204.5) - 28, ye + 18, "BPF", 15)
    draw_block_box(img, dr, px(1204.5) + 28, ye - 18, px(1322.5) - 28, ye + 18, "F-V\nCONV", 13)
    draw_block_box(img, dr, px(1322.5) + 30, ye - 18, px(1476.6) - 30, ye + 18, "ENVELOPE\nFOLLOWER", 13)
    draw_text(img, "PEAK", px(1400.7) * SS, (ye - 30) * SS, 16, cond=0.76)

    # Draw jack labels for all 35 jacks (with subtle matte plate behind labels so signal lines never strike text)
    manifest_jacks = []
    for idx, (jid, u, v, is_out, tlbl, blbl) in enumerate(RAW_JACKS):
        jx, jy = round(px(u)), round(py(v))
        if tlbl:
            lw_half = max(20, len(tlbl) * 4 + 4)
            dr.rectangle([(jx - lw_half) * SS, (jy - 38) * SS, (jx + lw_half) * SS, (jy - 24) * SS], fill=BG_BASE)
            draw_text(img, tlbl, jx * SS, (jy - 31) * SS, 15, fill=INK, cond=0.74, track=0.02)
        if blbl:
            lw_half = max(18, len(blbl) * 4 + 3)
            dr.rectangle([(jx - lw_half) * SS, (jy + 23) * SS, (jx + lw_half) * SS, (jy + 37) * SS], fill=BG_BASE)
            draw_text(img, blbl, jx * SS, (jy + 30) * SS, 14, fill=INK_DIM, cond=0.74, track=0.01)
        # Subtle socket bezel shadow
        r = 23 * SS
        dr.ellipse([jx * SS - r, jy * SS - r, jx * SS + r, jy * SS + r], fill=(10, 11, 13, 255))
        manifest_jacks.append({
            "jack": idx, "id": jid, "isOutput": is_out,
            "cx": jx, "cy": jy, "size": 46,
            "visParam": 99 + idx, "tapParam": 134 + idx,
        })

    # Main Volume knob in authentic patchbay upper-right spot + 5 ESP knobs along bottom
    p2_knobs = [
        (0,  "volume",      round(px(1440.0)), round(py(82.0)),  64, "knob_small_pot.png", 65, "VOLUME",     "pot"),
        (31, "esp_level",   round(px(995.0)),  552, 60, "knob_med_pot.png", 65, "SIG LEVEL", "pot"),
        (32, "esp_lowcut",  round(px(1095.0)), 552, 60, "knob_med_pot.png", 65, "LOW CUT",   "pot"),
        (33, "esp_highcut", round(px(1195.0)), 552, 60, "knob_med_pot.png", 65, "HIGH CUT",  "pot"),
        (34, "esp_cvadj",   round(px(1295.0)), 552, 60, "knob_med_pot.png", 65, "CV ADJUST", "pot"),
        (35, "esp_thresh",  round(px(1395.0)), 552, 60, "knob_med_pot.png", 65, "THRESHOLD", "pot"),
    ]
    manifest_knobs = []
    for pidx, kid, cx, cy, sz, strip, frames, lbl, kind in p2_knobs:
        draw_knob_scale(img, dr, cx, cy, sz * 0.44, lbl, kind=kind)
        manifest_knobs.append({
            "param": pidx, "id": kid, "cx": cx, "cy": cy, "size": sz,
            "strip": strip, "frames": frames, "bipolar": False,
        })

    # Twenty crest in bottom-right of ESP panel
    draw_text(img, "Twenty", round(px(1515)) * SS, 536 * SS, 34, fill=INK, cond=0.88, track=0.06)
    draw_text(img, "SYNTHESIZER", round(px(1515)) * SS, 566 * SS, 18, fill=INK_DIM, cond=0.76, track=0.08)

    # ── Right-hand Patch Controller & Performance Strip (x = 996..1268) ──
    dr.line([(988 * SS, 16 * SS), (988 * SS, 612 * SS)], fill=DIVIDER, width=int(2.6 * SS))

    # Section A: Patchbay Status & Actions
    draw_text(img, "PATCH ROUTING", 1132 * SS, 30 * SS, 21, fill=ACCENT_GOLD, cond=0.78, track=0.08)
    dr.rounded_rectangle([1006 * SS, 48 * SS, 1258 * SS, 92 * SS], radius=5 * SS,
                         fill=(12, 13, 15, 255), outline=(68, 70, 78, 255), width=2)
    draw_text(img, "TAP OUT JACK THEN IN JACK", 1132 * SS, 106 * SS, 15, fill=INK_DIM, cond=0.76, track=0.04)

    # Color legend dots (6 AT20V colors)
    for ci, (_, rgb, _) in enumerate(CABLE_COLORS):
        dx = (1024 + ci * 43) * SS
        dy = 126 * SS
        dr.ellipse([dx - 8 * SS, dy - 8 * SS, dx + 8 * SS, dy + 8 * SS], fill=rgb + (255,), outline=INK_DIM, width=1)
        draw_text(img, str(ci + 1), dx, dy, 15, fill=CABLE_COLORS[ci][2] + (255,), cond=1.0)

    # Section B: Direct Route Editor
    dr.line([(1002 * SS, 232 * SS), (1262 * SS, 232 * SS)], fill=DIVIDER, width=int(2.0 * SS))
    draw_text(img, "DIRECT ROUTE EDITOR", 1132 * SS, 248 * SS, 19, cond=0.76, track=0.06)
    draw_text(img, "SOURCE (OUT)", 1066 * SS, 270 * SS, 16, fill=INK_DIM, cond=0.78)
    draw_text(img, "DEST (IN)",    1198 * SS, 270 * SS, 16, fill=INK_DIM, cond=0.78)
    # Recessed value boxes under direct selectors
    dr.rounded_rectangle([1008 * SS, 352 * SS, 1124 * SS, 382 * SS], radius=4 * SS, fill=(12, 13, 15, 255), outline=(58, 60, 66, 255), width=2)
    dr.rounded_rectangle([1140 * SS, 352 * SS, 1256 * SS, 382 * SS], radius=4 * SS, fill=(12, 13, 15, 255), outline=(58, 60, 66, 255), width=2)

    for pidx, kid, cx, strip, frames in [
        (169, "pedit_src", 1066, "knob_ext_20way.png", 20),
        (170, "pedit_dst", 1198, "knob_ext_15way.png", 15),
    ]:
        draw_knob_scale(img, dr, cx, 314, 26, "", kind="choice",
                        ticks=[(i / float(frames - 1), "") for i in range(frames)], start_deg=-140, end_deg=140)
        manifest_knobs.append({
            "param": pidx, "id": kid, "cx": cx, "cy": 314, "size": 56,
            "strip": strip, "frames": frames, "bipolar": False,
        })

    # Section C: Controller (Wheel + Momentary Switch)
    dr.line([(1002 * SS, 396 * SS), (1262 * SS, 396 * SS)], fill=DIVIDER, width=int(2.0 * SS))
    draw_text(img, "CONTROLLER", 1132 * SS, 414 * SS, 20, cond=0.78, track=0.08)
    draw_text(img, "WHEEL",  1066 * SS, 436 * SS, 16, fill=INK_DIM, cond=0.78)
    draw_text(img, "MOM SW", 1198 * SS, 436 * SS, 16, fill=INK_DIM, cond=0.78)
    draw_text(img, "+5V", 1018 * SS, 458 * SS, 14, fill=INK_DIM, cond=0.8)
    draw_text(img, "0V",  1018 * SS, 520 * SS, 14, fill=INK_DIM, cond=0.8)
    draw_text(img, "-5V", 1018 * SS, 582 * SS, 14, fill=INK_DIM, cond=0.8)

    leds = [
        {"param": 177, "id": "led_esp_peak", "cx": round(px(1400.7)), "cy": round(ye - 44), "size": 20, "strip": "led_2.png", "frames": 2},
        {"param": 178, "id": "led_esp_trig", "cx": round(px(1534.9)), "cy": round(ye - 44), "size": 20, "strip": "led_2.png", "frames": 2},
    ]
    buttons = [
        {"param": 171, "id": "pact_conn",  "x": 1008, "y": 144, "w": 118, "h": 38, "on": "btn_conn_on.png",  "off": "btn_conn_off.png"},
        {"param": 172, "id": "pact_disc",  "x": 1138, "y": 144, "w": 118, "h": 38, "on": "btn_disc_on.png",  "off": "btn_disc_off.png"},
        {"param": 173, "id": "pact_clear", "x": 1008, "y": 188, "w": 248, "h": 36, "on": "btn_clear_on.png", "off": "btn_clear_off.png"},
        {"param": 68,  "id": "momentary",  "x": 1146, "y": 476, "w": 104, "h": 88, "on": "btn_msw_on.png",   "off": "btn_msw_off.png"},
    ]
    wheel = {"param": 67, "id": "wheel", "x": 1028, "y": 448, "w": 76, "h": 146, "strip": "wheel_strip.png", "frames": 33}
    labels = [
        {"param": 174, "id": "pstat_text", "x": 1010, "y": 52,  "w": 244, "h": 36, "size": 22, "color": "ffe0ac4a"},
        {"param": 169, "id": "pedit_src_v","x": 1010, "y": 354, "w": 112, "h": 26, "size": 19, "color": "ffe8e6e0"},
        {"param": 170, "id": "pedit_dst_v","x": 1142, "y": 354, "w": 112, "h": 26, "size": 19, "color": "ffe8e6e0"},
    ]

    out = img.resize((W, H), Image.LANCZOS).convert("RGB")
    return out, {"knobs": manifest_knobs, "jacks": manifest_jacks, "leds": leds, "buttons": buttons, "wheel": wheel, "labels": labels}


# =============================================================================
# 3. PAGE 3 — EXTENSIONS / ANALOGUE / FX / VOCODER (bg_ext.png)
# =============================================================================
def build_page3():
    img = make_metal_canvas(W * SS, H * SS, seed=303)
    dr = ImageDraw.Draw(img)

    div_w = int(2.6 * SS)
    # 5 clean vertical sections
    for vx in [236, 552, 764, 970]:
        dr.line([(vx * SS, 16 * SS), (vx * SS, 612 * SS)], fill=DIVIDER, width=div_w)
    dr.line([(18 * SS, 52 * SS), (1262 * SS, 52 * SS)], fill=DIVIDER, width=int(2.0 * SS))

    draw_text(img, "VOICE & PERF",      124 * SS, 34 * SS, 23, cond=0.76, track=0.07)
    draw_text(img, "ANALOGUE / SYSTEM", 394 * SS, 34 * SS, 23, cond=0.76, track=0.07)
    draw_text(img, "STEREO DELAY",      658 * SS, 34 * SS, 23, cond=0.76, track=0.07)
    draw_text(img, "PLATE REVERB",      867 * SS, 34 * SS, 23, cond=0.76, track=0.07)
    draw_text(img, "VOCODER",          1118 * SS, 34 * SS, 23, cond=0.76, track=0.07)
    draw_text(img, "SIGNAL",           1224 * SS, 34 * SS, 17, fill=INK_DIM, align="right", cond=0.78)

    y1, y2, y3 = 148, 336, 520

    def choice_ticks(labels):
        n = len(labels)
        return [(i / float(max(1, n - 1)), l) for i, l in enumerate(labels)]

    ext_knobs = [
        # Voice & Performance (6)
        (36, "voices",    72,  y1, 62, "knob_ext_6way.png",  6,  "VOICES",    "choice", choice_ticks(["MONO","2","4","6","8","12"]), -110, 110),
        (37, "unison",    180, y1, 62, "knob_ext_4way.png",  4,  "UNISON",    "choice", choice_ticks(["1","2","3","4"]), -55, 55),
        (38, "detune",    72,  y2, 62, "knob_small_pot.png", 65, "DETUNE",    "pot", None, -150, 150),
        (39, "spread",    180, y2, 62, "knob_small_pot.png", 65, "SPREAD",    "pot", None, -150, 150),
        (40, "priority",  72,  y3, 62, "knob_ext_3way.png",  3,  "PRIORITY",  "choice", choice_ticks(["LAST","HIGH","LOW"]), -50, 50),
        (41, "retrigger", 180, y3, 62, "knob_ext_2way.png",  2,  "RETRIG",    "choice", choice_ticks(["OFF","ON"]), -45, 45),

        # Analogue / System (7)
        (42, "filter_rev",294, y1, 62, "knob_ext_2way.png",  2,  "FILTER",    "choice", choice_ticks(["K35","OTA"]), -45, 45),
        (43, "analog",    394, y1, 62, "knob_small_pot.png", 65, "DRIFT",     "pot", None, -150, 150),
        (44, "mg_sync",   494, y1, 62, "knob_ext_2way.png",  2,  "MG CLOCK",  "choice", choice_ticks(["FREE","SYNC"]), -45, 45),
        (46, "quality",   294, y2, 62, "knob_ext_3way.png",  3,  "OVERSAMP",  "choice", choice_ticks(["2X","4X","8X"]), -50, 50),
        (45, "bend_range",394, y2, 62, "knob_ext_13way.png", 13, "BEND RNG",  "choice",
         [(0.0, "0"), (2/12, "2"), (5/12, "5"), (7/12, "7"), (1.0, "12")], -140, 140),
        (47, "output",    494, y2, 62, "knob_small_pot.png", 65, "OUTPUT",    "pot",
         [(0.0, "-24"), (0.4, "-12"), (0.8, "0"), (1.0, "+6")], -135, 135),
        (48, "ext_source",294, y3, 62, "knob_ext_3way.png",  3,  "EXT AUDIO", "choice", choice_ticks(["IN","SELF","NOIS"]), -50, 50),

        # Stereo Delay (5)
        (58, "dly_on",    610, y1, 62, "knob_ext_2way.png",  2,  "DELAY",     "choice", choice_ticks(["OFF","ON"]), -45, 45),
        (59, "dly_time",  710, y1, 62, "knob_ext_12way.png", 12, "TIME",      "choice",
         [(0.0, "1/32"), (2/11, "1/16"), (5/11, "1/8"), (8/11, "1/4"), (1.0, "1B")], -140, 140),
        (60, "dly_fb",    610, y2, 62, "knob_small_pot.png", 65, "FEEDBACK",  "pot", None, -150, 150),
        (61, "dly_tone",  710, y2, 62, "knob_small_pot.png", 65, "TONE",      "pot", None, -150, 150),
        (62, "dly_mix",   660, y3, 62, "knob_small_pot.png", 65, "MIX",       "pot", None, -150, 150),

        # Plate Reverb (4)
        (63, "rev_on",    818, y1, 62, "knob_ext_2way.png",  2,  "REVERB",    "choice", choice_ticks(["OFF","ON"]), -45, 45),
        (64, "rev_size",  918, y1, 62, "knob_small_pot.png", 65, "SIZE",      "pot", None, -150, 150),
        (65, "rev_damp",  818, y2, 62, "knob_small_pot.png", 65, "DAMPING",   "pot", None, -150, 150),
        (66, "rev_mix",   918, y2, 62, "knob_small_pot.png", 65, "MIX",       "pot", None, -150, 150),

        # Vocoder (9)
        (49, "voc_on",     1024, y1, 62, "knob_ext_2way.png",  2,  "VOCODER",   "choice", choice_ticks(["OFF","ON"]), -45, 45),
        (50, "voc_bands",  1121, y1, 62, "knob_ext_4way.png",  4,  "BANDS",     "choice", choice_ticks(["8","12","16","20"]), -55, 55),
        (51, "voc_gain",   1218, y1, 62, "knob_small_pot.png", 65, "INPUT",     "pot", None, -150, 150),
        (52, "voc_shift",  1024, y2, 62, "knob_small_pot.png", 65, "FORMANT",   "bipolar", None, -150, 150),
        (53, "voc_q",      1121, y2, 62, "knob_small_pot.png", 65, "RESONANCE", "pot", None, -150, 150),
        (56, "voc_hiss",   1218, y2, 62, "knob_small_pot.png", 65, "SIBILANCE", "pot", None, -150, 150),
        (54, "voc_attack", 1024, y3, 62, "knob_small_pot.png", 65, "ATTACK",    "pot", None, -150, 150),
        (55, "voc_release",1121, y3, 62, "knob_small_pot.png", 65, "RELEASE",   "pot", None, -150, 150),
        (57, "voc_mix",    1218, y3, 62, "knob_small_pot.png", 65, "MIX",       "pot", None, -150, 150),
    ]

    manifest_knobs = []
    for pidx, kid, cx, cy, sz, strip, frames, lbl, kind, ticks, a0, a1 in ext_knobs:
        draw_knob_scale(img, dr, cx, cy, sz * 0.43, lbl, kind=kind, ticks=ticks, start_deg=a0, end_deg=a1)
        manifest_knobs.append({
            "param": pidx, "id": kid, "cx": cx, "cy": cy, "size": sz,
            "strip": strip, "frames": frames, "bipolar": (kind == "bipolar"),
        })

    # Vintage Twenty crest in open bottom-right of System & Reverb
    draw_text(img, "Twenty",       444 * SS, 512 * SS, 34, fill=INK, cond=0.86, track=0.06)
    draw_text(img, "AT20V ENGINE", 444 * SS, 542 * SS, 18, fill=INK_DIM, cond=0.82, track=0.10)
    draw_text(img, "KORG35 / OTA", 868 * SS, 508 * SS, 20, fill=ACCENT_GOLD, cond=0.80, track=0.08)
    draw_text(img, "2X / 4X / 8X DSP", 868 * SS, 534 * SS, 17, fill=INK_DIM, cond=0.80, track=0.08)

    leds = [
        {"param": 179, "id": "led_voc_sig", "cx": 1244, "cy": 34, "size": 20, "strip": "led_2.png", "frames": 2},
    ]

    out = img.resize((W, H), Image.LANCZOS).convert("RGB")
    return out, {"knobs": manifest_knobs, "leds": leds}


# =============================================================================
# 4. VINTAGE MS-20 KNOB FILMSTRIP GENERATOR (4x supersampled!)
# =============================================================================
def render_ms20_knob_frame(size, deg, big=False, selector=False):
    """Render one frame of an authentic dark fluted Korg MS-20 rotary knob."""
    s = size * 4
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    cx = cy = s / 2.0
    r_skirt = s * 0.44
    r_body  = s * 0.34
    r_top   = s * 0.25

    # Soft offset cast shadow
    sh = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    sdr = ImageDraw.Draw(sh)
    sdr.ellipse([cx - r_skirt + s*0.03, cy - r_skirt + s*0.05,
                 cx + r_skirt + s*0.03, cy + r_skirt + s*0.05], fill=(0, 0, 0, 150))
    sh = sh.filter(ImageFilter.GaussianBlur(radius=s * 0.035))
    im.alpha_composite(sh)

    # Outer Bakelite skirt with subtle specular rim
    dr.ellipse([cx - r_skirt, cy - r_skirt, cx + r_skirt, cy + r_skirt],
               fill=(18, 19, 21, 255), outline=(44, 46, 52, 255), width=max(2, s // 64))

    # Authentic MS-20 fluted scallops (10 lobes around the skirt)
    rad = math.radians(deg)
    lobes = 10 if big else 8
    for i in range(lobes):
        a = rad + (2.0 * math.pi * i) / lobes
        lx = cx + math.sin(a) * (r_skirt * 0.87)
        ly = cy - math.cos(a) * (r_skirt * 0.87)
        lr = r_skirt * 0.14
        # Top-left lighting shading per scallop
        shade = 28 + int(16 * (-math.sin(a) * 0.6 + math.cos(a) * 0.8))
        dr.ellipse([lx - lr, ly - lr, lx + lr, ly + lr], fill=(shade, shade + 1, shade + 3, 255))

    # Tapered dark charcoal body
    dr.ellipse([cx - r_body, cy - r_body, cx + r_body, cy + r_body],
               fill=(24, 25, 28, 255), outline=(56, 58, 64, 255), width=max(2, s // 72))

    # Recessed matte cap with subtle studio highlight arc
    cap_col = (34, 36, 40, 255) if selector else (28, 30, 34, 255)
    dr.ellipse([cx - r_top, cy - r_top, cx + r_top, cy + r_top],
               fill=cap_col, outline=(72, 74, 82, 255), width=max(2, s // 80))
    dr.arc([cx - r_top + 2, cy - r_top + 2, cx + r_top - 2, cy + r_top - 2],
           200, 330, fill=(108, 112, 122, 160), width=max(2, s // 72))

    # Crisp white recessed MS-20 position pointer line
    dx, dy = math.sin(rad), -math.cos(rad)
    p0 = (cx + dx * (r_top * 0.18), cy + dy * (r_top * 0.18))
    p1 = (cx + dx * (r_skirt * 0.94), cy + dy * (r_skirt * 0.94))
    pw = max(6, int(s * (0.048 if selector else 0.042)))
    dr.line([p0, p1], fill=(244, 242, 234, 255), width=pw)
    # Rounded tip cap on pointer
    pr = pw * 0.5
    dr.ellipse([p1[0] - pr, p1[1] - pr, p1[0] + pr, p1[1] + pr], fill=(244, 242, 234, 255))

    return im.resize((size, size), Image.LANCZOS)


def make_knob_strip(size, frames, start_deg, end_deg, big=False, selector=False):
    strip = Image.new("RGBA", (size, size * frames), (0, 0, 0, 0))
    for i in range(frames):
        t = i / float(max(1, frames - 1))
        deg = start_deg + (end_deg - start_deg) * t
        fr = render_ms20_knob_frame(size, deg, big=big, selector=selector)
        strip.paste(fr, (0, i * size))
    assert strip.height <= 16384, f"Filmstrip too tall: {strip.height}"
    return strip


# =============================================================================
# 5. 28-FRAME JACK SOCKET & 6-COLOR NUMBERED CABLE PLUG FILMSTRIP
# =============================================================================
def render_jack_base(s):
    """Render chrome hex-nut 1/4" jack socket at 4x supersampling."""
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    cx = cy = s / 2.0
    # Outer metallic washer
    r_wash = s * 0.42
    dr.ellipse([cx - r_wash, cy - r_wash, cx + r_wash, cy + r_wash],
               fill=(136, 140, 148, 255), outline=(56, 58, 64, 255), width=max(2, s // 60))
    # Hexagonal nut
    r_hex = s * 0.36
    hex_pts = [(cx + r_hex * math.cos(math.radians(60 * k + 30)),
                cy + r_hex * math.sin(math.radians(60 * k + 30))) for k in range(6)]
    dr.polygon(hex_pts, fill=(178, 182, 190, 255), outline=(74, 78, 86, 255), width=max(2, s // 60))
    # Inner chrome sleeve collar
    r_col = s * 0.25
    dr.ellipse([cx - r_col, cy - r_col, cx + r_col, cy + r_col],
               fill=(112, 116, 124, 255), outline=(218, 222, 230, 255), width=max(2, s // 55))
    # Deep black 1/4" bore
    r_hole = s * 0.165
    dr.ellipse([cx - r_hole, cy - r_hole, cx + r_hole, cy + r_hole],
               fill=(8, 9, 11, 255), outline=(44, 46, 50, 255), width=max(2, s // 64))
    return im


def render_plug_overlay(im, s, slot_idx, selected=False, target_hint=False):
    dr = ImageDraw.Draw(im)
    cx = cy = s / 2.0
    _, rgb, fg = CABLE_COLORS[slot_idx % len(CABLE_COLORS)]
    ch = SLOT_CHARS[slot_idx % len(SLOT_CHARS)]

    # Shadow under plug
    r_plug = s * 0.36
    dr.ellipse([cx - r_plug + 4, cy - r_plug + 6, cx + r_plug + 4, cy + r_plug + 6], fill=(0, 0, 0, 140))

    # Colored plug barrel + glossy bevel
    dark = tuple(max(0, int(c * 0.58)) for c in rgb)
    hi = tuple(min(255, int(c * 1.28 + 26)) for c in rgb)
    dr.ellipse([cx - r_plug, cy - r_plug, cx + r_plug, cy + r_plug], fill=dark + (255,), outline=(18, 18, 20, 255), width=3)
    r_mid = s * 0.31
    dr.ellipse([cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid], fill=rgb + (255,))
    dr.arc([cx - r_mid + 3, cy - r_mid + 3, cx + r_mid - 3, cy + r_mid - 3], 200, 340, fill=hi + (210,), width=max(4, s // 30))

    # Crisp route badge digit/letter in center of plug cap
    draw_text(im, ch, cx, cy + 1, s * 0.36, fill=fg + (255,), cond=0.95, bold=True, track=0.0)

    if selected:
        r_hl = s * 0.46
        dr.ellipse([cx - r_hl, cy - r_hl, cx + r_hl, cy + r_hl], outline=(255, 208, 86, 255), width=max(6, s // 22))
    elif target_hint:
        r_hl = s * 0.45
        dr.ellipse([cx - r_hl, cy - r_hl, cx + r_hl, cy + r_hl], outline=(245, 186, 74, 215), width=max(4, s // 30))


def make_jack_strip(size=46):
    s = size * 4
    frames = 28
    strip = Image.new("RGBA", (size, size * frames), (0, 0, 0, 0))
    base = render_jack_base(s)

    for f in range(frames):
        im = base.copy()
        dr = ImageDraw.Draw(im)
        cx = cy = s / 2.0
        if f == 0:
            pass  # plain unconnected socket
        elif f == 1:
            # Selected unconnected jack (bright gold ring)
            r_hl = s * 0.46
            dr.ellipse([cx - r_hl, cy - r_hl, cx + r_hl, cy + r_hl], outline=(255, 208, 86, 255), width=max(7, s // 20))
        elif f == 2:
            # Compatible target highlight (warm amber dashed halo)
            r_hl = s * 0.45
            for a in range(0, 360, 30):
                dr.arc([cx - r_hl, cy - r_hl, cx + r_hl, cy + r_hl], a, a + 18, fill=(248, 198, 92, 230), width=max(5, s // 26))
        elif 3 <= f <= 14:
            render_plug_overlay(im, s, f - 3, selected=False)
        elif 15 <= f <= 26:
            render_plug_overlay(im, s, f - 15, selected=True)
        elif f == 27:
            # Connected jack highlighted as compatible/replaceable target
            render_plug_overlay(im, s, 0, selected=False, target_hint=True)
            # Neutral dark-amber ring showing "occupied, tap to replace"
            r_hl = s * 0.46
            for a in range(0, 360, 30):
                dr.arc([cx - r_hl, cy - r_hl, cx + r_hl, cy + r_hl], a, a + 18, fill=(255, 214, 102, 240), width=max(6, s // 24))
        strip.paste(im.resize((size, size), Image.LANCZOS), (0, f * size))
    return strip


# =============================================================================
# 6. LEDs, BUTTONS, CONTROL WHEEL & HIT PLATES
# =============================================================================
def make_led_strip(size=20, frames=2):
    s = size * 4
    strip = Image.new("RGBA", (size, size * frames), (0, 0, 0, 0))
    for i in range(frames):
        im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        cx = cy = s / 2.0
        t = i / float(max(1, frames - 1))
        # Glow halo when lit
        if t > 0.05:
            gl = Image.new("RGBA", (s, s), (0, 0, 0, 0))
            gdr = ImageDraw.Draw(gl)
            rg = s * 0.42
            gdr.ellipse([cx - rg, cy - rg, cx + rg, cy + rg], fill=(255, 42, 24, int(190 * t)))
            gl = gl.filter(ImageFilter.GaussianBlur(radius=s * 0.14))
            im.alpha_composite(gl)
        # Chrome bezel
        rb = s * 0.31
        dr.ellipse([cx - rb, cy - rb, cx + rb, cy + rb], fill=(38, 40, 44, 255), outline=(92, 96, 104, 255), width=3)
        # LED dome
        rl = s * 0.22
        r_col = int(64 + 191 * t)
        g_col = int(14 + 46 * t)
        b_col = int(12 + 24 * t)
        dr.ellipse([cx - rl, cy - rl, cx + rl, cy + rl], fill=(r_col, g_col, b_col, 255))
        if t > 0.2:
            rh = s * 0.09
            dr.ellipse([cx - rl * 0.45 - rh, cy - rl * 0.45 - rh, cx - rl * 0.45 + rh, cy - rl * 0.45 + rh],
                       fill=(255, 220, 200, int(210 * t)))
        strip.paste(im.resize((size, size), Image.LANCZOS), (0, i * size))
    return strip


def make_tactile_button(w, h, text_str, active=False, danger=False):
    im = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    if danger:
        bg = (96, 26, 22, 255) if active else (46, 20, 18, 255)
        ol = (224, 96, 84, 255) if active else (138, 62, 56, 255)
        tx = (255, 232, 228, 255)
    else:
        bg = (68, 56, 30, 255) if active else (32, 34, 38, 255)
        ol = ACCENT_GOLD if active else (106, 108, 116, 255)
        tx = (255, 236, 190, 255) if active else INK
    dr.rounded_rectangle([2, 2, w * 2 - 3, h * 2 - 3], radius=8, fill=bg, outline=ol, width=3)
    draw_text(im, text_str, w, h, 24, fill=tx, cond=0.84, track=0.06)
    return im.resize((w, h), Image.LANCZOS)


def make_msw_button(w=104, h=88, pressed=False):
    """Iconic Korg MS-20 red-capped momentary switch pushbutton."""
    im = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    cx, cy = w, h
    r_bezel = min(w, h) * 0.78
    dr.ellipse([cx - r_bezel, cy - r_bezel, cx + r_bezel, cy + r_bezel],
               fill=(18, 19, 22, 255), outline=(92, 96, 104, 255), width=4)
    r_cap = r_bezel * (0.72 if pressed else 0.78)
    fill = (226, 48, 36, 255) if pressed else (142, 28, 22, 255)
    rim  = (255, 160, 120, 255) if pressed else (196, 72, 60, 255)
    dr.ellipse([cx - r_cap, cy - r_cap, cx + r_cap, cy + r_cap], fill=fill, outline=rim, width=4)
    draw_text(im, "TRIG" if pressed else "PUSH", cx, cy, 24, fill=(255, 244, 236, 255), cond=0.86, track=0.06)
    return im.resize((w, h), Image.LANCZOS)


def make_wheel_strip(w=76, h=146, frames=33):
    """Vertical knurled MS-20 control wheel filmstrip."""
    strip = Image.new("RGBA", (w, h * frames), (0, 0, 0, 0))
    for i in range(frames):
        im = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        t = i / float(max(1, frames - 1))  # 0 = bottom (-5V), 1 = top (+5V)
        # Dark recessed wheel slot
        dr.rounded_rectangle([18, 8, w * 2 - 18, h * 2 - 8], radius=12,
                             fill=(8, 9, 11, 255), outline=(72, 74, 82, 255), width=3)
        # Knurled wheel cylinder
        wx0, wx1 = 30, w * 2 - 30
        wy0, wy1 = 18, h * 2 - 18
        dr.rounded_rectangle([wx0, wy0, wx1, wy1], radius=8, fill=(28, 30, 34, 255), outline=(56, 58, 64, 255), width=2)
        # Moving ridges
        offset = (1.0 - t) * 52.0
        for ry in range(wy0 + 8, wy1 - 8, 12):
            dist_center = abs(((ry + offset * 0.3) % (wy1 - wy0)) - (wy1 - wy0) * 0.5) / ((wy1 - wy0) * 0.5)
            shade = int(20 + 36 * (1.0 - min(1.0, dist_center)))
            dr.line([(wx0 + 4, ry), (wx1 - 4, ry)], fill=(shade, shade + 2, shade + 4, 255), width=3)
        # White notch indicator at current wheel angle
        ny = int(wy1 - 20 - t * (wy1 - wy0 - 40))
        dr.rounded_rectangle([wx0 - 2, ny - 6, wx1 + 2, ny + 6], radius=4, fill=(242, 240, 232, 255))
        strip.paste(im.resize((w, h), Image.LANCZOS), (0, i * h))
    return strip


def save_to_all_skins(filename, img):
    for d in SKIN_DIRS:
        os.makedirs(d, exist_ok=True)
        img.save(os.path.join(d, filename), optimize=True)


def main():
    print("Rendering Page 1 (SYNTH PANEL)...")
    bg1, m1 = build_page1()
    save_to_all_skins("bg_synth.png", bg1)

    print("Rendering Page 2 (PATCHBAY / ESP)...")
    bg2, m2 = build_page2()
    save_to_all_skins("bg_patch.png", bg2)

    print("Rendering Page 3 (EXTENSIONS / ANALOGUE)...")
    bg3, m3 = build_page3()
    save_to_all_skins("bg_ext.png", bg3)

    print("Rendering vintage MS-20 knob filmstrips...")
    save_to_all_skins("knob_big_pot.png",   make_knob_strip(76, 65, -150, 150, big=True,  selector=False))
    save_to_all_skins("knob_small_pot.png", make_knob_strip(64, 65, -150, 150, big=False, selector=False))
    save_to_all_skins("knob_med_pot.png",   make_knob_strip(60, 65, -150, 150, big=False, selector=False))
    save_to_all_skins("knob_big_4way.png",  make_knob_strip(76, 4,  -50,  50,  big=True,  selector=True))
    save_to_all_skins("knob_ext_2way.png",  make_knob_strip(62, 2,  -45,  45,  big=False, selector=True))
    save_to_all_skins("knob_ext_3way.png",  make_knob_strip(62, 3,  -50,  50,  big=False, selector=True))
    save_to_all_skins("knob_ext_4way.png",  make_knob_strip(62, 4,  -55,  55,  big=False, selector=True))
    save_to_all_skins("knob_ext_6way.png",  make_knob_strip(62, 6,  -110, 110, big=False, selector=True))
    save_to_all_skins("knob_ext_12way.png", make_knob_strip(62, 12, -140, 140, big=False, selector=True))
    save_to_all_skins("knob_ext_13way.png", make_knob_strip(62, 13, -140, 140, big=False, selector=True))
    save_to_all_skins("knob_ext_15way.png", make_knob_strip(56, 15, -140, 140, big=False, selector=True))
    save_to_all_skins("knob_ext_20way.png", make_knob_strip(56, 20, -140, 140, big=False, selector=True))

    print("Rendering 28-frame 1/4-inch jack & cable plug filmstrip...")
    save_to_all_skins("jack_strip.png", make_jack_strip(46))

    # Alpha = 4 hit-plate (NEVER alpha = 0 on MPC hardware!)
    hit = Image.new("RGBA", (46, 46), (255, 255, 255, 4))
    save_to_all_skins("hit_46.png", hit)

    print("Rendering LEDs, buttons and control wheel...")
    save_to_all_skins("led_2.png", make_led_strip(20, 2))
    save_to_all_skins("led_4.png", make_led_strip(20, 4))
    save_to_all_skins("btn_conn_off.png",  make_tactile_button(118, 38, "CONNECT", active=False))
    save_to_all_skins("btn_conn_on.png",   make_tactile_button(118, 38, "CONNECT", active=True))
    save_to_all_skins("btn_disc_off.png",  make_tactile_button(118, 38, "UNPATCH", active=False))
    save_to_all_skins("btn_disc_on.png",   make_tactile_button(118, 38, "UNPATCH", active=True))
    save_to_all_skins("btn_clear_off.png", make_tactile_button(248, 36, "CLEAR ALL CABLES", active=False, danger=True))
    save_to_all_skins("btn_clear_on.png",  make_tactile_button(248, 36, "CLEAR ALL CABLES", active=True,  danger=True))
    save_to_all_skins("btn_msw_off.png",   make_msw_button(104, 88, pressed=False))
    save_to_all_skins("btn_msw_on.png",    make_msw_button(104, 88, pressed=True))
    save_to_all_skins("wheel_strip.png",   make_wheel_strip(76, 146, 33))

    manifest = {"width": W, "height": H, "page1": m1, "page2": m2, "page3": m3}
    with open(MANIFEST_PATH, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"Done! Wrote skins assets and {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
