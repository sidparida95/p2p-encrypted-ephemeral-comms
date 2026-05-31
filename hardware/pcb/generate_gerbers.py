#!/usr/bin/env python3
"""
Generate Gerber files for the Cardputer LoRa Carrier Board.

Design: through-hole only — no SMD soldering required.

  J1   Grove HY2.0, 4-pin THT, 2.0 mm pitch  (Cardputer side)
  U1   AMS1117-3.3 BREAKOUT MODULE (Robu Part 31179) — 3-pin THT, 2.54 mm pitch
       (the module is a tiny PCB with its own onboard caps)
  J2   1×5 female header, 2.54 mm pitch       (RYLR998 socket)
  M1   M2 mounting hole

Board: 50 x 22 mm, 2-layer.

RYLR998 socket (J2) pin order, bottom-to-top: GND, TX, RX, RST, VDD

Outputs to gerbers/:
    cardputer-lora-F_Cu.gbr        Top copper
    cardputer-lora-B_Cu.gbr        Bottom copper (GND pour)
    cardputer-lora-F_Mask.gbr      Top solder mask
    cardputer-lora-B_Mask.gbr      Bottom solder mask
    cardputer-lora-F_Silkscreen.gbr  Top silkscreen
    cardputer-lora-Edge_Cuts.gbr   Board outline
    cardputer-lora-PTH.drl         Plated through-hole drill
    cardputer-lora-NPTH.drl        Non-plated drill (mounting hole only)

Then zips them into gerbers.zip.

VERIFY OUTPUT IN https://gerber-viewer.ucamco.com/ BEFORE MANUFACTURE.
"""

import os
import zipfile
from pathlib import Path

# ============================================================
# BOARD GEOMETRY
# ============================================================
BOARD_W = 50.0
BOARD_H = 22.0

# ----- J1: Grove 4-pin THT, vertical socket, 2.0 mm pitch -----
# Pin 1: 5V, Pin 2: GND, Pin 3: G2 (Cardputer RX), Pin 4: G1 (Cardputer TX)
J1 = [
    {"name": "5V",   "x": 3.0, "y": 11.0, "drill": 0.9, "pad": 1.6},
    {"name": "GND",  "x": 5.0, "y": 11.0, "drill": 0.9, "pad": 1.6},
    {"name": "G2",   "x": 7.0, "y": 11.0, "drill": 0.9, "pad": 1.6},
    {"name": "G1",   "x": 9.0, "y": 11.0, "drill": 0.9, "pad": 1.6},
]

# ----- U1: AMS1117-3.3 BREAKOUT MODULE (Robu Part 31179) -----
# Pre-made breakout: 3 male header pins at 2.54 mm pitch on the module's
# underside. The module's own PCB has the SOT-223 chip + caps already.
# Two assembly options:
#   (a) Push the module's pins through these THT holes and solder underneath
#       (permanent, lower profile, ~₹0 extra).
#   (b) Install a 1×3 female header (~₹5) here and plug the module in
#       (removable, slightly taller).
U1 = [
    {"name": "VIN",  "x": 15.00, "y": 11.0, "drill": 1.0, "pad": 1.8},
    {"name": "GND",  "x": 17.54, "y": 11.0, "drill": 1.0, "pad": 1.8},
    {"name": "VOUT", "x": 20.08, "y": 11.0, "drill": 1.0, "pad": 1.8},
]

# ----- J2: 1×5 female header for RYLR998 -----
# Pin order bottom-to-top: GND, TX, RX, RST, VDD
J2 = [
    {"name": "GND", "x": 42.0, "y": 5.0,   "drill": 1.0, "pad": 1.8},
    {"name": "TX",  "x": 42.0, "y": 7.54,  "drill": 1.0, "pad": 1.8},
    {"name": "RX",  "x": 42.0, "y": 10.08, "drill": 1.0, "pad": 1.8},
    {"name": "RST", "x": 42.0, "y": 12.62, "drill": 1.0, "pad": 1.8},
    {"name": "VDD", "x": 42.0, "y": 15.16, "drill": 1.0, "pad": 1.8},
]

# ----- TX trace vias -----
# The TX signal needs to cross under RX to reach J2 pin 3 without shorting.
# It hops to the bottom layer via these two vias, then comes back to top.
TX_VIAS = [
    {"x":  9.0, "y": 8.5, "drill": 0.6, "pad": 1.0},
    {"x": 40.0, "y": 8.5, "drill": 0.6, "pad": 1.0},
]

# ----- M1: M2 mounting hole (non-plated) -----
M1 = {"x": 46.5, "y": 19.0, "drill": 2.2}

# Which through-holes are GND (connect directly to the bottom GND pour,
# no clearance circle around them). Everything else gets cleared.
GND_THT = {(5.0, 11.0), (17.54, 11.0), (42.0, 5.0)}

# ============================================================
# TRACES
# ============================================================
TRACE_POWER = 0.5
TRACE_SIG   = 0.3

TRACES_TOP = [
    # VIN (5V): Grove pin 1 → U1 VIN, looping over the top
    {"width": TRACE_POWER, "points": [(3.0, 11.0), (3.0, 17.0), (15.0, 17.0), (15.0, 11.0)]},

    # VOUT (3.3V): U1 VOUT → J2 VDD, looping over the top
    {"width": TRACE_POWER, "points": [(20.08, 11.0), (20.08, 19.0), (42.0, 19.0), (42.0, 15.16)]},

    # TX top segment 1: Grove pin 4 (G1 = Cardputer TX) → via at (9, 8.5)
    {"width": TRACE_SIG, "points": [(9.0, 11.0), (9.0, 8.5)]},

    # TX top segment 2: via at (40, 8.5) → J2 RX
    {"width": TRACE_SIG, "points": [(40.0, 8.5), (40.0, 10.08), (42.0, 10.08)]},

    # RX (G2 ← RYLR TX): Grove pin 3 → J2 TX, runs under the regulator pin row
    {"width": TRACE_SIG, "points": [(7.0, 11.0), (7.0, 7.0), (40.0, 7.0), (40.0, 7.54), (42.0, 7.54)]},
]

# Bottom-layer trace: TX under-pass connecting the two vias.
TRACES_BOT = [
    {"width": TRACE_SIG, "points": [(9.0, 8.5), (40.0, 8.5)]},
]

# ============================================================
# SILKSCREEN LABELS  (text, x, y, height_mm)
# ============================================================
SILK_LABELS = [
    ("CARDPUTER LORA CARRIER", 25.0, 21.0, 0.7),
    # J1 Grove
    ("5V",  3.0, 12.7, 0.5),
    ("GND", 5.0, 12.7, 0.5),
    ("RX",  7.0, 12.7, 0.5),
    ("TX",  9.0, 12.7, 0.5),
    ("J1",  6.0, 13.8, 0.5),
    # U1 AMS1117 module
    ("VIN",  15.00, 12.7, 0.5),
    ("GND",  17.54, 12.7, 0.5),
    ("VOUT", 20.08, 12.7, 0.5),
    ("U1 AMS1117", 17.54, 13.9, 0.5),
    # J2 RYLR998 socket
    ("GND", 43.6,  5.0,   0.5),
    ("TX",  43.6,  7.54,  0.5),
    ("RX",  43.6, 10.08,  0.5),
    ("RST", 43.6, 12.62,  0.5),
    ("VDD", 43.6, 15.16,  0.5),
    ("J2 - RYLR998", 38.0, 17.0, 0.5),
]

# Silkscreen body outlines (so you know which way modules face)
SILK_OUTLINES = [
    # U1 module body (Robu 31179 is ~12 x 7 mm; body sits *below* the pin row)
    [(11.5, 4.0), (23.5, 4.0), (23.5, 10.0), (11.5, 10.0), (11.5, 4.0)],
]

# ============================================================
# GERBER ENCODING
# ============================================================
SCALE = 1_000_000   # 4.6 format (1 unit = 1 µm)

def coord(mm):
    n = int(round(mm * SCALE))
    return str(n)

def gx(mm): return f"X{coord(mm)}"
def gy(mm): return f"Y{coord(mm)}"


class GerberFile:
    def __init__(self, layer_function, polarity="Positive"):
        self.lines = []
        self.apertures = {}
        self.next_id = 10
        self.lines.append("G04 Cardputer LoRa Carrier Board*")
        self.lines.append("%TF.GenerationSoftware,cardputer-lora-chat,2.0*%")
        self.lines.append(f"%TF.FileFunction,{layer_function}*%")
        self.lines.append(f"%TF.FilePolarity,{polarity}*%")
        self.lines.append("%FSLAX46Y46*%")
        self.lines.append("%MOMM*%")
        self.lines.append("%LPD*%")

    def aperture_circle(self, diameter_mm):
        key = ("C", round(diameter_mm, 4))
        if key not in self.apertures:
            id = self.next_id
            self.next_id += 1
            line = f"%ADD{id}C,{diameter_mm:.4f}*%"
            self.apertures[key] = (id, line)
        return self.apertures[key][0]

    def aperture_rect(self, w, h):
        key = ("R", round(w, 4), round(h, 4))
        if key not in self.apertures:
            id = self.next_id
            self.next_id += 1
            line = f"%ADD{id}R,{w:.4f}X{h:.4f}*%"
            self.apertures[key] = (id, line)
        return self.apertures[key][0]

    def flash(self, ap_id, x, y):
        self.lines.append(f"D{ap_id}*")
        self.lines.append(f"{gx(x)}{gy(y)}D03*")

    def draw(self, ap_id, segments):
        self.lines.append(f"D{ap_id}*")
        x0, y0 = segments[0]
        self.lines.append(f"{gx(x0)}{gy(y0)}D02*")
        for x, y in segments[1:]:
            self.lines.append(f"{gx(x)}{gy(y)}D01*")

    def region_rect(self, x, y, w, h):
        self.lines.append("G36*")
        self.lines.append(f"{gx(x)}{gy(y)}D02*")
        self.lines.append(f"{gx(x + w)}{gy(y)}D01*")
        self.lines.append(f"{gx(x + w)}{gy(y + h)}D01*")
        self.lines.append(f"{gx(x)}{gy(y + h)}D01*")
        self.lines.append(f"{gx(x)}{gy(y)}D01*")
        self.lines.append("G37*")

    def serialize(self):
        ap_defs = [v[1] for v in self.apertures.values()]
        full = self.lines[:7] + ap_defs + self.lines[7:] + ["M02*"]
        return "\n".join(full) + "\n"


# ============================================================
# LAYER GENERATORS
# ============================================================

def make_edge_cuts():
    g = GerberFile("Profile,NP")
    ap = g.aperture_circle(0.10)
    g.draw(ap, [(0, 0), (BOARD_W, 0), (BOARD_W, BOARD_H), (0, BOARD_H), (0, 0)])
    return g.serialize()


def make_top_copper():
    g = GerberFile("Copper,L1,Top")

    # THT pads (all components are through-hole now)
    for p in J1 + U1 + J2:
        ap = g.aperture_circle(p["pad"])
        g.flash(ap, p["x"], p["y"])

    # TX via pads on top layer
    for v in TX_VIAS:
        ap = g.aperture_circle(v["pad"])
        g.flash(ap, v["x"], v["y"])

    # Top-layer traces
    for t in TRACES_TOP:
        ap = g.aperture_circle(t["width"])
        g.draw(ap, t["points"])

    return g.serialize()


def make_bottom_copper():
    """Solid GND pour with clearances around non-GND pads and TX bottom trace."""
    g = GerberFile("Copper,L2,Bot")

    # Solid pour over (almost) the whole board
    g.region_rect(0.3, 0.3, BOARD_W - 0.6, BOARD_H - 0.6)

    # Subtractive clearances
    g.lines.append("%LPC*%")

    # Clear around every non-GND THT pad
    for p in J1 + U1 + J2:
        if (p["x"], p["y"]) not in GND_THT:
            ap = g.aperture_circle(p["pad"] + 0.8)
            g.flash(ap, p["x"], p["y"])

    # Clear around mounting hole
    ap = g.aperture_circle(M1["drill"] + 1.0)
    g.flash(ap, M1["x"], M1["y"])

    # Clear around TX via pads (not GND)
    for v in TX_VIAS:
        ap = g.aperture_circle(v["pad"] + 0.8)
        g.flash(ap, v["x"], v["y"])

    # Clear a wide channel around the bottom-layer TX trace
    for t in TRACES_BOT:
        ap = g.aperture_circle(t["width"] + 0.8)
        g.draw(ap, t["points"])

    # Switch back to additive — draw the TX trace and via pads in the cleared zone
    g.lines.append("%LPD*%")
    for v in TX_VIAS:
        ap = g.aperture_circle(v["pad"])
        g.flash(ap, v["x"], v["y"])
    for t in TRACES_BOT:
        ap = g.aperture_circle(t["width"])
        g.draw(ap, t["points"])

    return g.serialize()


def make_top_mask():
    g = GerberFile("Soldermask,Top", polarity="Negative")
    EXP = 0.1
    for p in J1 + U1 + J2:
        ap = g.aperture_circle(p["pad"] + EXP)
        g.flash(ap, p["x"], p["y"])
    for v in TX_VIAS:
        ap = g.aperture_circle(v["pad"] + EXP)
        g.flash(ap, v["x"], v["y"])
    return g.serialize()


def make_bottom_mask():
    g = GerberFile("Soldermask,Bot", polarity="Negative")
    EXP = 0.1
    for p in J1 + U1 + J2:
        ap = g.aperture_circle(p["pad"] + EXP)
        g.flash(ap, p["x"], p["y"])
    for v in TX_VIAS:
        ap = g.aperture_circle(v["pad"] + EXP)
        g.flash(ap, v["x"], v["y"])
    return g.serialize()


# Tiny vector font (4x6 grid)
CHAR_STROKES = {
    "A": [[(0,0),(0,4),(1,5),(2,5),(3,4),(3,0)],[(0,2),(3,2)]],
    "B": [[(0,0),(0,5),(2,5),(3,4),(3,3),(2,2.5),(0,2.5)],[(0,2.5),(2,2.5),(3,2),(3,1),(2,0),(0,0)]],
    "C": [[(3,5),(0,5),(0,0),(3,0)]],
    "D": [[(0,0),(0,5),(2,5),(3,4),(3,1),(2,0),(0,0)]],
    "E": [[(3,5),(0,5),(0,0),(3,0)],[(0,2.5),(2,2.5)]],
    "F": [[(3,5),(0,5),(0,0)],[(0,2.5),(2,2.5)]],
    "G": [[(3,5),(0,5),(0,0),(3,0),(3,2.5),(2,2.5)]],
    "H": [[(0,0),(0,5)],[(3,0),(3,5)],[(0,2.5),(3,2.5)]],
    "I": [[(0,5),(3,5)],[(1.5,5),(1.5,0)],[(0,0),(3,0)]],
    "J": [[(3,5),(3,1),(2,0),(1,0),(0,1)]],
    "K": [[(0,0),(0,5)],[(0,2),(3,5)],[(0,2),(3,0)]],
    "L": [[(0,5),(0,0),(3,0)]],
    "M": [[(0,0),(0,5),(1.5,3),(3,5),(3,0)]],
    "N": [[(0,0),(0,5),(3,0),(3,5)]],
    "O": [[(0,0),(0,5),(3,5),(3,0),(0,0)]],
    "P": [[(0,0),(0,5),(2,5),(3,4),(3,3),(2,2.5),(0,2.5)]],
    "R": [[(0,0),(0,5),(2,5),(3,4),(3,3),(2,2.5),(0,2.5)],[(1.5,2.5),(3,0)]],
    "S": [[(3,5),(0,5),(0,3),(3,2),(3,0),(0,0)]],
    "T": [[(0,5),(3,5)],[(1.5,5),(1.5,0)]],
    "U": [[(0,5),(0,1),(1,0),(2,0),(3,1),(3,5)]],
    "V": [[(0,5),(1.5,0),(3,5)]],
    "W": [[(0,5),(0.5,0),(1.5,2),(2.5,0),(3,5)]],
    "X": [[(0,0),(3,5)],[(0,5),(3,0)]],
    "Y": [[(0,5),(1.5,2.5)],[(3,5),(1.5,2.5),(1.5,0)]],
    "Z": [[(0,5),(3,5),(0,0),(3,0)]],
    "0": [[(0,0),(0,5),(3,5),(3,0),(0,0)],[(0,0),(3,5)]],
    "1": [[(0.5,4),(1.5,5),(1.5,0)],[(0,0),(3,0)]],
    "2": [[(0,4),(1,5),(2,5),(3,4),(3,3),(0,1),(0,0),(3,0)]],
    "3": [[(0,4),(1,5),(2,5),(3,4),(2,2.5)],[(2,2.5),(3,1),(2,0),(1,0),(0,1)]],
    "4": [[(0,5),(0,2.5),(3,2.5)],[(3,5),(3,0)]],
    "5": [[(3,5),(0,5),(0,3),(2,3),(3,2),(3,1),(2,0),(0,0)]],
    "6": [[(3,5),(1,5),(0,4),(0,1),(1,0),(2,0),(3,1),(3,2),(2,3),(0,3)]],
    "7": [[(0,5),(3,5),(1,0)]],
    "8": [[(1,2.5),(0,3),(0,4),(1,5),(2,5),(3,4),(3,3),(2,2.5),(1,2.5),(0,2),(0,1),(1,0),(2,0),(3,1),(3,2),(2,2.5)]],
    "9": [[(3,2.5),(3,4),(2,5),(1,5),(0,4),(0,3),(1,2.5),(3,2.5),(3,1),(2,0),(0,0)]],
    " ": [],
    ".": [[(1.4,0),(1.6,0),(1.6,0.2),(1.4,0.2),(1.4,0)]],
    "-": [[(0,2.5),(3,2.5)]],
}


def draw_text(g, ap_id, text, x, y, size_mm):
    cell_w = size_mm * 0.7
    cell_h = size_mm
    spacing = cell_w * 0.4
    cx = x
    for ch in text.upper():
        strokes = CHAR_STROKES.get(ch)
        if strokes is None:
            cx += cell_w + spacing
            continue
        for stroke in strokes:
            if len(stroke) < 2:
                continue
            pts = [(cx + sx/3 * cell_w, y + sy/5 * cell_h) for sx, sy in stroke]
            g.draw(ap_id, pts)
        cx += cell_w + spacing


def make_top_silk():
    g = GerberFile("Legend,Top")
    ap = g.aperture_circle(0.15)

    for text, x, y, size in SILK_LABELS:
        # Approximate width to centre the text on (x, y)
        approx_w = len(text) * size * 0.7 * 1.4
        draw_text(g, ap, text, x - approx_w/2, y - size/2, size)

    # Outlines
    for outline in SILK_OUTLINES:
        g.draw(ap, outline)

    return g.serialize()


def make_drill_pth():
    """Excellon 2 — plated through-holes."""
    holes = []
    for p in J1 + U1 + J2:
        holes.append((p["drill"], p["x"], p["y"]))
    for v in TX_VIAS:
        holes.append((v["drill"], v["x"], v["y"]))

    sizes = sorted(set(round(h[0], 3) for h in holes))
    lines = ["M48", ";HEADER: Cardputer LoRa Carrier — PTH", "METRIC,LZ", "FMAT,2"]
    tool_map = {}
    for i, s in enumerate(sizes, 1):
        tool_map[s] = f"T{i}"
        lines.append(f"T{i}C{s:.3f}")
    lines += ["%", "G90", "G05"]

    for size in sizes:
        lines.append(tool_map[size])
        for d, x, y in holes:
            if round(d, 3) == size:
                lines.append(f"X{x:.3f}Y{y:.3f}")
        lines.append("T0")
    lines.append("M30")
    return "\n".join(lines) + "\n"


def make_drill_npth():
    """Non-plated drill — mounting hole only."""
    lines = ["M48", ";HEADER: Cardputer LoRa Carrier — NPTH", "METRIC,LZ", "FMAT,2"]
    lines.append(f"T1C{M1['drill']:.3f}")
    lines += ["%", "G90", "G05", "T1", f"X{M1['x']:.3f}Y{M1['y']:.3f}", "T0", "M30"]
    return "\n".join(lines) + "\n"


# ============================================================
# SVG PREVIEW
# ============================================================
def make_svg_preview():
    SCALE = 10
    W = BOARD_W * SCALE
    H = BOARD_H * SCALE
    MARGIN = 20

    def sx(x): return x * SCALE + MARGIN
    def sy(y): return H - y * SCALE + MARGIN

    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" '
                 f'viewBox="0 0 {W + 2*MARGIN} {H + 2*MARGIN}" '
                 f'font-family="-apple-system, sans-serif">')
    lines.append('<title>Cardputer LoRa Carrier — board preview</title>')

    # Substrate
    lines.append(f'<rect x="{MARGIN}" y="{MARGIN}" width="{W}" height="{H}" '
                 f'fill="#1B5E20" stroke="#0D3812" stroke-width="2" rx="3"/>')
    # Hint of GND pour on bottom
    lines.append(f'<rect x="{MARGIN+3}" y="{MARGIN+3}" width="{W-6}" height="{H-6}" '
                 f'fill="#1565C0" opacity="0.10"/>')

    # Bottom-layer TX trace (dashed darker blue, drawn first)
    for t in TRACES_BOT:
        pts = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in t["points"])
        lines.append(f'<polyline points="{pts}" fill="none" stroke="#1976D2" '
                     f'stroke-width="{t["width"] * SCALE:.1f}" stroke-dasharray="6 4" '
                     f'stroke-linecap="round" stroke-linejoin="round" opacity="0.85"/>')

    # Top traces (amber)
    for t in TRACES_TOP:
        pts = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in t["points"])
        lines.append(f'<polyline points="{pts}" fill="none" stroke="#FFB300" '
                     f'stroke-width="{t["width"] * SCALE:.1f}" '
                     f'stroke-linecap="round" stroke-linejoin="round"/>')

    # TX vias (top pads + drill)
    for v in TX_VIAS:
        lines.append(f'<circle cx="{sx(v["x"]):.1f}" cy="{sy(v["y"]):.1f}" '
                     f'r="{v["pad"]/2 * SCALE}" fill="#FFB300" stroke="#B58A00"/>')
        lines.append(f'<circle cx="{sx(v["x"]):.1f}" cy="{sy(v["y"]):.1f}" '
                     f'r="{v["drill"]/2 * SCALE}" fill="#0D3812"/>')

    # All THT pads (J1 + U1 + J2)
    for p in J1 + U1 + J2:
        lines.append(f'<circle cx="{sx(p["x"]):.1f}" cy="{sy(p["y"]):.1f}" '
                     f'r="{p["pad"]/2 * SCALE}" fill="#E5C100" stroke="#8A6B00"/>')
        lines.append(f'<circle cx="{sx(p["x"]):.1f}" cy="{sy(p["y"]):.1f}" '
                     f'r="{p["drill"]/2 * SCALE}" fill="#0D3812"/>')

    # Mounting hole
    lines.append(f'<circle cx="{sx(M1["x"]):.1f}" cy="{sy(M1["y"]):.1f}" '
                 f'r="{M1["drill"]/2 * SCALE}" fill="#0D3812" stroke="#0D3812"/>')

    # Silkscreen labels
    for text, x, y, size in SILK_LABELS:
        font_px = size * SCALE * 1.6
        lines.append(f'<text x="{sx(x):.1f}" y="{sy(y) + font_px*0.3:.1f}" '
                     f'fill="white" font-size="{font_px:.1f}" font-weight="700" '
                     f'text-anchor="middle" font-family="monospace">{text}</text>')

    # Silkscreen outlines (U1 module body indicator)
    for outline in SILK_OUTLINES:
        pts = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in outline)
        lines.append(f'<polyline points="{pts}" fill="none" stroke="white" '
                     f'stroke-width="1" opacity="0.7"/>')

    # Module hint label inside U1 outline
    lines.append(f'<text x="{sx(17.54):.1f}" y="{sy(6.5):.1f}" '
                 f'fill="white" font-size="10" opacity="0.5" text-anchor="middle" '
                 f'font-family="monospace" font-style="italic">31179 module sits here</text>')

    # Dimension
    lines.append(f'<text x="{sx(BOARD_W/2):.1f}" y="{H + MARGIN + 18}" '
                 f'fill="#222" font-size="12" text-anchor="middle">'
                 f'{BOARD_W} × {BOARD_H} mm</text>')

    lines.append('</svg>')
    return "\n".join(lines)


# ============================================================
# WRITE FILES
# ============================================================
OUT_DIR = Path(__file__).parent / "gerbers"
OUT_DIR.mkdir(exist_ok=True)

files = {
    "cardputer-lora-F_Cu.gbr":         make_top_copper(),
    "cardputer-lora-B_Cu.gbr":         make_bottom_copper(),
    "cardputer-lora-F_Mask.gbr":       make_top_mask(),
    "cardputer-lora-B_Mask.gbr":       make_bottom_mask(),
    "cardputer-lora-F_Silkscreen.gbr": make_top_silk(),
    "cardputer-lora-Edge_Cuts.gbr":    make_edge_cuts(),
    "cardputer-lora-PTH.drl":          make_drill_pth(),
    "cardputer-lora-NPTH.drl":         make_drill_npth(),
}

for name, content in files.items():
    (OUT_DIR / name).write_text(content)
    print(f"  wrote {name}  ({len(content)} bytes)")

svg_path = OUT_DIR.parent / "board-preview.svg"
svg_path.write_text(make_svg_preview())
print(f"  wrote {svg_path.name}")

zip_path = OUT_DIR.parent / "gerbers.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for name in files:
        zf.write(OUT_DIR / name, arcname=name)
print(f"\nWrote {zip_path}")
