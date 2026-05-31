#!/usr/bin/env python3
"""
Generate Gerber files for the Cardputer LoRa Carrier Board.

Board: 50 x 22 mm, 2-layer
Pinout for RYLR998 socket J2 (bottom-to-top): GND, TX, RX, RST, VDD

Outputs written to gerbers/:
    cardputer-lora-F_Cu.gbr        Top copper (signal traces)
    cardputer-lora-B_Cu.gbr        Bottom copper (GND pour)
    cardputer-lora-F_Mask.gbr      Top solder mask
    cardputer-lora-B_Mask.gbr      Bottom solder mask
    cardputer-lora-F_Silkscreen.gbr  Top silkscreen labels
    cardputer-lora-Edge_Cuts.gbr   Board outline
    cardputer-lora-PTH.drl         Plated through-hole drill (Excellon)
    cardputer-lora-NPTH.drl        Non-plated drill (mounting hole)

Then zips them all into gerbers.zip.

The format is Gerber X2 + Excellon 2 — accepted by JLCPCB, PCBWay, Robu, OSH
Park, and every fab in between.

VERIFY THE OUTPUT IN A GERBER VIEWER BEFORE SENDING TO MANUFACTURE.
Recommended: https://gerber-viewer.ucamco.com/ (free, web-based).
"""

import os
import zipfile
from pathlib import Path

# ============================================================
# BOARD GEOMETRY
# ============================================================
BOARD_W = 50.0   # mm
BOARD_H = 22.0   # mm

# All coordinates in mm with origin at bottom-left.

# ----- J1: Grove 4-pin THT, vertical socket, 2.0 mm pitch -----
# Pin 1: 5V, Pin 2: GND, Pin 3: G2 (Cardputer RX), Pin 4: G1 (Cardputer TX)
J1 = [
    {"name": "5V",   "x": 3.0, "y": 11.0, "drill": 0.9, "pad": 1.6},
    {"name": "GND",  "x": 5.0, "y": 11.0, "drill": 0.9, "pad": 1.6},
    {"name": "G2",   "x": 7.0, "y": 11.0, "drill": 0.9, "pad": 1.6},
    {"name": "G1",   "x": 9.0, "y": 11.0, "drill": 0.9, "pad": 1.6},
]

# ----- U1: AMS1117-3.3 SOT-223 -----
# Body center at (18, 11). Leads on top edge, tab on bottom edge.
# Lead pads (SMD): 1.5mm wide × 2.5mm tall, 2.30mm pitch.
# Tab pad (SMD): 3.5mm wide × 2.5mm tall.
U1_CENTER = (18.0, 11.0)
U1_LEADS = [   # SMD pads on TOP layer
    {"name": "GND",  "x": 15.7, "y": 13.0, "w": 1.5, "h": 2.5},  # lead 1
    {"name": "VOUT", "x": 18.0, "y": 13.0, "w": 1.5, "h": 2.5},  # lead 2 (and tab)
    {"name": "VIN",  "x": 20.3, "y": 13.0, "w": 1.5, "h": 2.5},  # lead 3
]
U1_TAB = {"name": "VOUT", "x": 18.0, "y": 9.0, "w": 3.5, "h": 2.5}

# ----- C1: 10µF input cap, 0805 SMD -----
# Pads 1.0 × 1.2 mm, pitch 2.0 mm
C1_CENTER = (13.0, 11.0)
C1_PADS = [
    {"name": "VIN", "x": 12.0, "y": 11.0, "w": 1.0, "h": 1.2},
    {"name": "GND", "x": 14.0, "y": 11.0, "w": 1.0, "h": 1.2},
]

# ----- C2: 22µF output cap, 0805 SMD -----
C2_CENTER = (24.0, 11.0)
C2_PADS = [
    {"name": "VOUT", "x": 23.0, "y": 11.0, "w": 1.0, "h": 1.2},
    {"name": "GND",  "x": 25.0, "y": 11.0, "w": 1.0, "h": 1.2},
]

# ----- J2: 1×5 female header THT for RYLR998 -----
# 2.54 mm pitch, vertical column on right side of board.
# Pin order bottom-to-top: GND, TX, RX, RST, VDD
J2 = [
    {"name": "GND", "x": 42.0, "y": 5.0,   "drill": 1.0, "pad": 1.8},
    {"name": "TX",  "x": 42.0, "y": 7.54,  "drill": 1.0, "pad": 1.8},
    {"name": "RX",  "x": 42.0, "y": 10.08, "drill": 1.0, "pad": 1.8},
    {"name": "RST", "x": 42.0, "y": 12.62, "drill": 1.0, "pad": 1.8},
    {"name": "VDD", "x": 42.0, "y": 15.16, "drill": 1.0, "pad": 1.8},
]

# ----- M1: M2 mounting hole (non-plated) -----
M1 = {"x": 46.5, "y": 19.0, "drill": 2.2}

# ----- Vias for GND stitching from top to bottom layer -----
# 0.6mm drill, 1.0mm pad
GND_VIAS = [
    {"x": 14.0, "y": 8.0},   # near C1 GND pad
    {"x": 25.0, "y": 8.0},   # near C2 GND pad
    {"x": 13.0, "y": 14.0},  # near U1 lead 1 GND (after stub trace)
]

# ============================================================
# TRACE ROUTING (top layer)
# ============================================================
# Traces are polylines of (x,y) waypoints. Width in mm.

TRACE_POWER = 0.5
TRACE_SIG = 0.3
TRACE_GND = 0.4

TRACES = [
    # ---- VIN (5V) ----
    # J1 pin 1 → C1 left pad
    {"width": TRACE_POWER, "points": [(3.0, 11.0), (12.0, 11.0)]},
    # C1 left pad → over the top → U1 VIN lead
    {"width": TRACE_POWER, "points": [(12.0, 11.0), (12.0, 16.5), (20.3, 16.5), (20.3, 13.0)]},

    # ---- VOUT (3.3V) ----
    # U1 lead 2 → C2 left pad (short horizontal hop)
    {"width": TRACE_POWER, "points": [(18.0, 13.0), (18.0, 11.0), (23.0, 11.0)]},
    # U1 tab → lead 2 stub (heat dissipation - tab is internally connected to lead 2)
    {"width": TRACE_POWER, "points": [(18.0, 9.0), (18.0, 11.0)]},
    # C2 left pad → over the top → J2 VDD
    {"width": TRACE_POWER, "points": [(23.0, 11.0), (23.0, 18.0), (42.0, 18.0), (42.0, 15.16)]},

    # ---- GND stub: U1 lead 1 → via at (13, 14) ----
    {"width": TRACE_GND, "points": [(15.7, 13.0), (13.0, 13.0), (13.0, 14.0)]},
    # GND stub: C1 right pad → via at (14, 8)
    {"width": TRACE_GND, "points": [(14.0, 11.0), (14.0, 8.0)]},
    # GND stub: C2 right pad → via at (25, 8)
    {"width": TRACE_GND, "points": [(25.0, 11.0), (25.0, 8.0)]},

    # ---- G1 TX (Cardputer TX → RYLR RX) ----
    # J1 pin 4 → under the components → J2 RX pin
    {"width": TRACE_SIG, "points": [(9.0, 11.0), (9.0, 3.0), (40.0, 3.0), (40.0, 10.08), (42.0, 10.08)]},

    # ---- G2 RX (Cardputer RX ← RYLR TX) ----
    # J1 pin 3 → over the components → J2 TX pin
    {"width": TRACE_SIG, "points": [(7.0, 11.0), (7.0, 19.5), (40.0, 19.5), (40.0, 7.54), (42.0, 7.54)]},
]

# ============================================================
# SILKSCREEN LABELS
# ============================================================
# Format: (text, x, y, size_mm)
SILK_LABELS = [
    ("CARDPUTER LORA CARRIER", 25.0, 21.2, 0.8),
    ("J1 GROVE", 6.0, 8.5, 0.7),
    ("5V",  3.0, 12.7, 0.6),
    ("GND", 5.0, 12.7, 0.6),
    ("RX",  7.0, 12.7, 0.6),
    ("TX",  9.0, 12.7, 0.6),
    ("U1", 16.0, 11.0, 0.7),
    ("C1", 13.0, 12.7, 0.6),
    ("C2", 24.0, 12.7, 0.6),
    ("RYLR998 →", 35.0, 2.0, 0.7),
    ("GND", 43.5,  5.0,   0.6),
    ("TX",  43.5,  7.54,  0.6),
    ("RX",  43.5, 10.08,  0.6),
    ("RST", 43.5, 12.62,  0.6),
    ("VDD", 43.5, 15.16,  0.6),
]

# ============================================================
# GERBER ENCODING
# ============================================================
SCALE = 1_000_000   # Gerber uses 4.6 format (mm × 10^6)

def coord(mm):
    """Format a mm value as a Gerber 4.6 integer string (handles negative)."""
    n = int(round(mm * SCALE))
    if n >= 0:
        return str(n) if n != 0 else "0"
    else:
        return f"-{abs(n)}"

def gx(mm): return f"X{coord(mm)}"
def gy(mm): return f"Y{coord(mm)}"

class GerberFile:
    def __init__(self, layer_function, polarity="Positive"):
        self.lines = []
        self.apertures = {}   # key -> (id, definition_line)
        self.next_id = 10
        # Header
        self.lines.append(f"G04 Cardputer LoRa Carrier Board*")
        self.lines.append(f"%TF.GenerationSoftware,cardputer-lora-chat,1.0*%")
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

    def aperture_rect(self, w_mm, h_mm):
        key = ("R", round(w_mm, 4), round(h_mm, 4))
        if key not in self.apertures:
            id = self.next_id
            self.next_id += 1
            line = f"%ADD{id}R,{w_mm:.4f}X{h_mm:.4f}*%"
            self.apertures[key] = (id, line)
        return self.apertures[key][0]

    def flash(self, ap_id, x, y):
        self.lines.append(f"D{ap_id}*")
        self.lines.append(f"{gx(x)}{gy(y)}D03*")

    def draw(self, ap_id, segments):
        """segments = list of (x,y) points. Move to first, draw to rest."""
        self.lines.append(f"D{ap_id}*")
        x0, y0 = segments[0]
        self.lines.append(f"{gx(x0)}{gy(y0)}D02*")
        for x, y in segments[1:]:
            self.lines.append(f"{gx(x)}{gy(y)}D01*")

    def region_rect(self, x, y, w, h):
        """Filled rectangle as a region (used for GND pour & masks)."""
        self.lines.append("G36*")
        self.lines.append(f"{gx(x)}{gy(y)}D02*")
        self.lines.append(f"{gx(x + w)}{gy(y)}D01*")
        self.lines.append(f"{gx(x + w)}{gy(y + h)}D01*")
        self.lines.append(f"{gx(x)}{gy(y + h)}D01*")
        self.lines.append(f"{gx(x)}{gy(y)}D01*")
        self.lines.append("G37*")

    def serialize(self):
        # Insert aperture definitions after the header block.
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

    # --- Flash pads ---
    # J1 round THT pads
    for p in J1:
        ap = g.aperture_circle(p["pad"])
        g.flash(ap, p["x"], p["y"])
    # J2 round THT pads
    for p in J2:
        ap = g.aperture_circle(p["pad"])
        g.flash(ap, p["x"], p["y"])
    # U1 lead pads (SMD rect)
    for p in U1_LEADS:
        ap = g.aperture_rect(p["w"], p["h"])
        g.flash(ap, p["x"], p["y"])
    # U1 tab
    ap = g.aperture_rect(U1_TAB["w"], U1_TAB["h"])
    g.flash(ap, U1_TAB["x"], U1_TAB["y"])
    # C1, C2 SMD pads
    for p in C1_PADS + C2_PADS:
        ap = g.aperture_rect(p["w"], p["h"])
        g.flash(ap, p["x"], p["y"])
    # GND vias (top pad)
    for v in GND_VIAS:
        ap = g.aperture_circle(1.0)
        g.flash(ap, v["x"], v["y"])

    # --- Draw traces ---
    for t in TRACES:
        ap = g.aperture_circle(t["width"])
        g.draw(ap, t["points"])

    return g.serialize()


def make_bottom_copper():
    """Bottom layer = solid GND pour with clearances around vias/holes."""
    g = GerberFile("Copper,L2,Bot")

    # Solid pour rectangle covering the board (with 0.3mm margin from edge)
    g.region_rect(0.3, 0.3, BOARD_W - 0.6, BOARD_H - 0.6)

    # Clearances (in negative polarity = subtractive)
    g.lines.append("%LPC*%")  # clear (subtract) following geometry

    # Clearance around each non-GND through-hole pad
    for p in J1 + J2:
        if p["name"] != "GND":
            ap = g.aperture_circle(p["pad"] + 0.5)
            g.flash(ap, p["x"], p["y"])

    # Bottom pad for GND vias (positive again - these connect to pour)
    g.lines.append("%LPD*%")  # dark (additive)
    for v in GND_VIAS:
        ap = g.aperture_circle(1.0)
        g.flash(ap, v["x"], v["y"])

    # Clear around the mounting hole
    g.lines.append("%LPC*%")
    ap = g.aperture_circle(M1["drill"] + 1.0)
    g.flash(ap, M1["x"], M1["y"])

    return g.serialize()


def make_top_mask():
    """Soldermask is POSITIVE: drawn shapes are EXPOSED (no mask)."""
    g = GerberFile("Soldermask,Top", polarity="Negative")
    # Expose all pads with a small expansion (0.05mm)
    EXP = 0.1

    for p in J1 + J2:
        ap = g.aperture_circle(p["pad"] + EXP)
        g.flash(ap, p["x"], p["y"])
    for p in U1_LEADS + [U1_TAB] + C1_PADS + C2_PADS:
        ap = g.aperture_rect(p["w"] + EXP, p["h"] + EXP)
        g.flash(ap, p["x"], p["y"])
    for v in GND_VIAS:
        ap = g.aperture_circle(1.0 + EXP)
        g.flash(ap, v["x"], v["y"])

    return g.serialize()


def make_bottom_mask():
    g = GerberFile("Soldermask,Bot", polarity="Negative")
    EXP = 0.1
    # Through-holes also exposed on bottom
    for p in J1 + J2:
        ap = g.aperture_circle(p["pad"] + EXP)
        g.flash(ap, p["x"], p["y"])
    # Vias exposed on bottom too
    for v in GND_VIAS:
        ap = g.aperture_circle(1.0 + EXP)
        g.flash(ap, v["x"], v["y"])
    return g.serialize()


# ============================================================
# Tiny vector font for silkscreen (uppercase + digits + a few)
# ============================================================
# Each character is a list of strokes; each stroke is a list of (x,y) in a
# 4-wide × 6-tall grid (0..3 in x, 0..5 in y).

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
    "Q": [[(0,0),(0,5),(3,5),(3,1),(2,0),(0,0)],[(2,1),(3.5,-0.5)]],
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
    "/": [[(0,0),(3,5)]],
    "→": [[(0,2.5),(3,2.5)],[(2,4),(3,2.5),(2,1)]],
    "-": [[(0,2.5),(3,2.5)]],
}

def draw_text(g, ap_id, text, x, y, size_mm):
    """Draw text starting at (x, y), with cell size_mm tall."""
    cell_w = size_mm * 0.7    # 4 grid units wide → scale
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

    # Component reference designators and labels
    for text, x, y, size in SILK_LABELS:
        # Center text horizontally around (x, y)
        approx_w = len(text) * size * 0.7 * 1.4
        draw_text(g, ap, text, x - approx_w/2, y - size/2, size)

    # Outline around components (helpful for assembly)
    # U1 SOT-223 body
    g.draw(ap, [(15.0, 9.5), (21.0, 9.5), (21.0, 12.5), (15.0, 12.5), (15.0, 9.5)])
    # C1 body
    g.draw(ap, [(12.0, 10.4), (14.0, 10.4), (14.0, 11.6), (12.0, 11.6), (12.0, 10.4)])
    # C2 body
    g.draw(ap, [(23.0, 10.4), (25.0, 10.4), (25.0, 11.6), (23.0, 11.6), (23.0, 10.4)])

    return g.serialize()


def make_drill_pth():
    """Excellon 2 drill file for plated through-holes."""
    lines = []
    lines.append("M48")
    lines.append(";HEADER: Cardputer LoRa Carrier — PTH")
    lines.append("METRIC,LZ")
    lines.append("FMAT,2")

    # Collect unique drill sizes
    holes = []
    for p in J1 + J2:
        holes.append((p["drill"], p["x"], p["y"]))
    for v in GND_VIAS:
        holes.append((0.6, v["x"], v["y"]))

    sizes = sorted(set(round(h[0], 3) for h in holes))
    tool_map = {}
    for i, s in enumerate(sizes, 1):
        tool_map[s] = f"T{i}"
        lines.append(f"T{i}C{s:.3f}")
    lines.append("%")
    lines.append("G90")
    lines.append("G05")

    for size in sizes:
        lines.append(tool_map[size])
        for d, x, y in holes:
            if round(d, 3) == size:
                lines.append(f"X{x:.3f}Y{y:.3f}")
        lines.append("T0")

    lines.append("M30")
    return "\n".join(lines) + "\n"


def make_drill_npth():
    """Non-plated drill file (just the mounting hole)."""
    lines = []
    lines.append("M48")
    lines.append(";HEADER: Cardputer LoRa Carrier — NPTH")
    lines.append("METRIC,LZ")
    lines.append("FMAT,2")
    lines.append(f"T1C{M1['drill']:.3f}")
    lines.append("%")
    lines.append("G90")
    lines.append("G05")
    lines.append("T1")
    lines.append(f"X{M1['x']:.3f}Y{M1['y']:.3f}")
    lines.append("T0")
    lines.append("M30")
    return "\n".join(lines) + "\n"


# ============================================================
# SVG PREVIEW (for visual sanity-check before sending to fab)
# ============================================================
def make_svg_preview():
    """Render the board to SVG so we can eyeball it before manufacturing."""
    SCALE = 10  # 10 px per mm
    W = BOARD_W * SCALE
    H = BOARD_H * SCALE
    MARGIN = 20

    def sx(x): return x * SCALE + MARGIN
    def sy(y): return H - y * SCALE + MARGIN   # flip Y for SVG screen-coords

    lines = []
    lines.append(f'<?xml version="1.0" encoding="UTF-8"?>')
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" '
                 f'viewBox="0 0 {W + 2*MARGIN} {H + 2*MARGIN}" '
                 f'font-family="-apple-system, sans-serif">')
    lines.append('<title>Cardputer LoRa Carrier — board preview</title>')

    # Board substrate (green)
    lines.append(f'<rect x="{MARGIN}" y="{MARGIN}" width="{W}" height="{H}" '
                 f'fill="#1B5E20" stroke="#0D3812" stroke-width="2" rx="3"/>')

    # Bottom GND pour (shown as faint blue tint)
    lines.append(f'<rect x="{MARGIN+3}" y="{MARGIN+3}" width="{W-6}" height="{H-6}" '
                 f'fill="#1565C0" opacity="0.15"/>')

    # Top traces (amber)
    for t in TRACES:
        pts = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in t["points"])
        lines.append(f'<polyline points="{pts}" fill="none" stroke="#FFB300" '
                     f'stroke-width="{t["width"] * SCALE:.1f}" '
                     f'stroke-linecap="round" stroke-linejoin="round"/>')

    # Vias (small circles)
    for v in GND_VIAS:
        lines.append(f'<circle cx="{sx(v["x"]):.1f}" cy="{sy(v["y"]):.1f}" '
                     f'r="{0.5 * SCALE}" fill="#FFB300" stroke="#B58A00"/>')
        lines.append(f'<circle cx="{sx(v["x"]):.1f}" cy="{sy(v["y"]):.1f}" '
                     f'r="{0.3 * SCALE}" fill="#0D3812"/>')

    # THT pads (J1, J2)
    for p in J1 + J2:
        lines.append(f'<circle cx="{sx(p["x"]):.1f}" cy="{sy(p["y"]):.1f}" '
                     f'r="{p["pad"]/2 * SCALE}" fill="#E5C100" stroke="#8A6B00"/>')
        lines.append(f'<circle cx="{sx(p["x"]):.1f}" cy="{sy(p["y"]):.1f}" '
                     f'r="{p["drill"]/2 * SCALE}" fill="#0D3812"/>')

    # SMD pads (U1, C1, C2)
    for p in U1_LEADS + [U1_TAB] + C1_PADS + C2_PADS:
        lines.append(f'<rect x="{sx(p["x"] - p["w"]/2):.1f}" '
                     f'y="{sy(p["y"] + p["h"]/2):.1f}" '
                     f'width="{p["w"] * SCALE}" height="{p["h"] * SCALE}" '
                     f'fill="#E5C100" stroke="#8A6B00" stroke-width="0.5" rx="1"/>')

    # Mounting hole
    lines.append(f'<circle cx="{sx(M1["x"]):.1f}" cy="{sy(M1["y"]):.1f}" '
                 f'r="{M1["drill"]/2 * SCALE}" fill="#0D3812" stroke="#0D3812"/>')

    # Silkscreen
    for text, x, y, size in SILK_LABELS:
        font_px = size * SCALE * 1.5
        lines.append(f'<text x="{sx(x):.1f}" y="{sy(y) + font_px*0.3:.1f}" '
                     f'fill="white" font-size="{font_px:.1f}" font-weight="700" '
                     f'text-anchor="middle" font-family="monospace">{text}</text>')

    # Component outlines on silk
    def silk_rect(x, y, w, h):
        lines.append(f'<rect x="{sx(x-w/2):.1f}" y="{sy(y+h/2):.1f}" '
                     f'width="{w*SCALE}" height="{h*SCALE}" '
                     f'fill="none" stroke="white" stroke-width="1" opacity="0.6"/>')

    silk_rect(18.0, 11.0, 6.0, 3.0)   # U1 body
    silk_rect(13.0, 11.0, 2.0, 1.2)   # C1 body
    silk_rect(24.0, 11.0, 2.0, 1.2)   # C2 body

    # Dimension labels
    lines.append(f'<text x="{sx(BOARD_W/2):.1f}" y="{H + MARGIN + 18}" '
                 f'fill="#222" font-size="12" text-anchor="middle">'
                 f'{BOARD_W} × {BOARD_H} mm</text>')

    lines.append('</svg>')
    return "\n".join(lines)



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

# SVG preview alongside the Gerbers
svg_path = OUT_DIR.parent / "board-preview.svg"
svg_path.write_text(make_svg_preview())
print(f"  wrote {svg_path.name}")

# Zip them up
zip_path = OUT_DIR.parent / "gerbers.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for name in files:
        zf.write(OUT_DIR / name, arcname=name)
print(f"\nWrote {zip_path}")
