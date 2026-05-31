# Cardputer LoRa Carrier Board

A small, **through-hole-only** PCB that plugs into the Cardputer's Grove port and provides regulated 3.3V plus a socket for the RYLR998 LoRa module. Replaces the F2F-jumper-wire setup with one clean board.

**No SMD soldering required.** You re-use the same Robu Part 31179 AMS1117 module from the breadboard build — it plugs into the board through 3 holes.

<div align="center">
<img src="board-preview.svg" alt="PCB top view" width="640">
</div>

## What's in this folder

| File | Purpose |
|---|---|
| `gerbers.zip` | **Upload this to your fab** (Robu, JLCPCB, PCBWay, etc.) |
| `board-preview.svg` | Visual preview of the manufactured board |
| `schematic.svg` | Circuit schematic |
| `gerbers/` | Individual Gerber + drill files (loose, in case the fab wants them separately) |
| `generate_gerbers.py` | Source for the design — re-run this if you tweak parameters |
| `README.md` | This file |

## How the 31179 module fits

The Robu Part 31179 is a tiny pre-built PCB with the AMS1117 chip and its decoupling caps already on it. It has 3 male header pins underneath at 2.54 mm pitch (VIN / GND / VOUT). This carrier board has 3 matching THT holes — the module's pins push straight through and you solder from the bottom side.

You have two installation options:

| Option | Pros | Cons |
|---|---|---|
| **Solder the module directly** (push pins through, flip board, solder on bottom) | Lowest profile, ₹0 extra, most reliable | Module is permanent |
| **Add a 1×3 female header** (₹5 from Robu), then plug the module in | Removable / reusable | ~7 mm taller, slightly more contact resistance |

For most builds, soldering directly is fine — the 31179 costs ₹50 and you're unlikely to need to swap it.

## Pin order on RYLR998 socket (J2)

Bottom to top, as shown on the silkscreen:

| Pin # | Net | Connects to |
|---:|---|---|
| 1 | **GND** | board ground |
| 2 | **TX** (RYLR's TX out) | Cardputer G2 (RX) |
| 3 | **RX** (RYLR's RX in) | Cardputer G1 (TX) |
| 4 | **RST** | unconnected (no reset needed) |
| 5 | **VDD** | 3.3V from AMS1117 module output |

## Schematic

<div align="center">
<img src="schematic.svg" alt="Schematic" width="720">
</div>

The dashed green box around U1 is the **31179 module itself** — it's a sub-PCB with the regulator chip and both 10 µF caps already on it. From the carrier board's perspective, U1 is just three through-holes.

## Bill of materials

| Ref | Component | Package | Qty | Notes | ~Cost (₹) | ~Cost ($) |
|---|---|---|---:|---|---:|---:|
| **PCB** | 2-layer, 50×22 mm, 1.6mm FR-4, HASL, green | — | 1 | upload `gerbers.zip` | ₹30–50 (qty 10) | $0.40–0.60 |
| **U1** | AMS1117-3.3 breakout module | THT, 3-pin DIP | 1 | **Robu Part 31179** (same as the breadboard build) | ₹50 | $0.60 |
| J1 | Grove HY2.0 vertical, 4-pin | THT | 1 | Robu / Seeed | ₹25 | $0.30 |
| J2 | 1×5 female pin header, 2.54mm | THT | 1 | Robu / any shop | ₹10 | $0.15 |
| _(opt.)_ U1-socket | 1×3 female pin header, 2.54mm | THT | 1 | only if you want the regulator module removable | ₹5 | $0.05 |
| M1 | M2 × 6mm screw + nut | — | 1 set | hardware store, optional | ₹5 | $0.05 |

**No SMD parts. No external capacitors needed — they're built into the 31179.**

**Cost per assembled node: ≈ ₹120 / $1.50** including the regulator module (in a qty-10 batch).

## How to order from Robu

1. Go to **https://robu.in/product/robu-pcb-manufacturing-service/** (the SKU 1373369 page).
2. Click **Upload Model**, select `gerbers.zip` from this folder.
3. Configure:
   - Base Material: **FR-4**
   - Layers: **2**
   - PCB Qty: **10** (minimum, costs the same as 5)
   - Different Design: **01**
   - Delivery Format: **Single PCB**
   - PCB Thickness: **1.6 mm**
   - PCB Color: **Green**
   - Surface finish: **HASL (with lead)** — cheapest, fine for hobby use
4. Wait for the quote (usually under an hour), pay, then receive boards in 2–3 weeks.

Same workflow works on JLCPCB, PCBWay, AllPCB — they all accept Gerber X2 + Excellon zips.

## ⚠️ VERIFY BEFORE MANUFACTURING

These Gerbers were generated programmatically without going through KiCad. **You must verify before sending to fab.** Ten boards of bad Gerbers ≈ ₹500 and 3 weeks wasted.

**Required check:**

1. Open **https://gerber-viewer.ucamco.com/** (free, no signup).
2. Click **Drop files or click here**, drop in `gerbers.zip`.
3. Wait for all layers to load.
4. Inspect:
   - **Edge cuts** — should be a 50 × 22 mm rectangle
   - **Top copper** — 5 traces visible, 4 + 3 + 5 = 12 through-hole pads
   - **Bottom copper** — solid GND pour with clearance circles around non-GND holes, plus the short TX under-pass trace at y ≈ 8.5 mm
   - **Drill** — 5 holes in J2 column, 4 in J1 row, 3 in U1 row, 2 small TX vias, plus the M2 mounting hole
   - **Silkscreen** — readable VIN / GND / VOUT labels by U1, GND / TX / RX / RST / VDD by J2
5. Compare layer-by-layer to [`board-preview.svg`](board-preview.svg) in this folder.

**Critical things to confirm:**

- [ ] J2 pin order matches your specific RYLR998 module: **GND, TX, RX, RST, VDD** (bottom to top)
- [ ] J1 pin order matches your Cardputer Grove pinout: **5V, GND, G2, G1** (left to right)
- [ ] U1 pin order matches your 31179 module: **VIN, GND, VOUT** (left to right) — most 31179 batches use this order, but Robu has shipped revisions; double-check the silk labels on your own module before soldering
- [ ] No traces shorting to each other or to GND pour
- [ ] All through-holes have annular ring (pad larger than hole)
- [ ] Silkscreen text is readable, not on top of pads

If anything's off, edit `generate_gerbers.py` and re-run `python3 generate_gerbers.py` — the script regenerates everything.

## Board specs

| Property | Value |
|---|---|
| Outline | 50.0 × 22.0 mm |
| Layers | 2 |
| Thickness | 1.6 mm |
| Surface finish | HASL (with lead) or HASL-RoHS |
| Soldermask | Green |
| Min trace width | 0.3 mm (12 mil) |
| Min clearance | 0.4 mm (16 mil) |
| Min drill | 0.6 mm (TX vias) |
| Through-hole sizes | 0.6 mm (vias) / 0.9 mm (Grove) / 1.0 mm (U1 + J2) |
| Mounting | 1 × M2 hole |

## Assembly order

All parts are through-hole. Any soldering iron works.

1. **U1 (AMS1117 module)** — insert the module's 3 pins through the THT holes labelled VIN / GND / VOUT, hold flush against the board, flip, solder the 3 pins on the bottom. (Or first install a 1×3 female header and plug the module in.)
2. **J1 (Grove socket)** — pins through holes, solder from bottom.
3. **J2 (1×5 female header)** — same.
4. _(Optional)_ **M2 screw** through M1 to mount the board to an enclosure.

Push the RYLR998 module into J2 with its pins lined up to the silk labels. Plug a 4-pin Grove cable between J1 and the Cardputer's Grove port. Power up.

## How the routing works

Looking at the [board preview](board-preview.svg), the amber lines are top-copper traces and the dashed blue line is the single bottom-layer signal trace:

- **5V (thick amber)**: Grove pin 1 → loops over the top → U1 VIN
- **3.3V (thick amber)**: U1 VOUT → loops over the top → J2 VDD
- **G2 RX (thin amber)**: Grove pin 3 → runs straight across the top side, just below the pin row → J2 TX
- **G1 TX**: top-layer drop from Grove pin 4 → **via to bottom** → short trace across bottom layer through a slot in the GND pour → **via back to top** → up to J2 RX. The two vias let TX cross under RX without shorting.
- **GND**: handled entirely by the bottom-layer copper pour. The three GND through-holes (Grove pin 2, U1 pin 2, J2 pin 1) connect directly to the pour with no clearance.

Trace widths: 0.5 mm for power, 0.3 mm for signal. All clearances are 0.4 mm. Well within any cheap fab's tolerances.

## Modifying the design

Open `generate_gerbers.py` and edit:

- Board dimensions: `BOARD_W`, `BOARD_H` at the top
- Component positions: `J1`, `U1`, `J2`, `TX_VIAS`
- Traces: `TRACES_TOP` (top layer) and `TRACES_BOT` (bottom layer) — each entry is `{"width": ..., "points": [(x, y), ...]}`
- Silkscreen labels: `SILK_LABELS`

Re-run with:

```bash
cd hardware/pcb
python3 generate_gerbers.py
```

Outputs land in `gerbers/` and re-zip into `gerbers.zip`. Re-verify in the Gerber viewer.
