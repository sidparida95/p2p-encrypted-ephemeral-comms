# Hardware

Complete bill of materials, sourcing notes, and wiring tips.

## Bill of materials

For **one node** (single Cardputer + LoRa setup):

| # | Component | Qty | USD | INR | Where to buy |
|---|---|---:|---:|---:|---|
| 1 | M5Stack Cardputer v1.1 (StampS3 inside) | 1 | $30 | ₹2,500 | [M5Stack store](https://shop.m5stack.com/), [Robu.in](https://robu.in/), Amazon |
| 2 | Reyax RYLR998 LoRa transceiver, 868/915 MHz, with antenna | 1 | $14 | ₹1,200 | [Robu.in](https://robu.in/product/reyax-rylr998-868-915mhz-lora-antenna-transceiver-moduledip-version/), Digikey, Amazon |
| 3 | AMS1117 3.3V regulator module (3-pin DIP), Robu Part 31179 | 1 | $1 | ₹50 | [Robu.in](https://robu.in/) |
| 4 | Female-to-female Dupont jumper wires (10cm) | 6 | $3 | ₹150 (pack of 40) | Any electronics store |
| 5 | USB-C cable (for flashing) | 1 | — | — | You probably have one |

**Subtotal per node: ≈ $48 USD / ₹3,900 INR**

For a working **two-way chat** you need **two complete nodes**: ≈ **$96 USD / ₹7,800 INR**.

### Optional accessories

| Component | Purpose | USD | INR |
|---|---|---:|---:|
| **Open-source PCB carrier** ([`hardware/pcb/`](../hardware/pcb/)) | Replaces parts #3 + #4 with a single board. Cleaner build, no wire-on-wire workarounds. | $1.20 | ₹90 |
| microSD card (≤ 32 GB, FAT32) | Load firmware via SD launcher (M5Launcher, Bruce, etc.) | $5 | ₹400 |
| Small breadboard (170 tie-point mini) | Cleaner GND junction than F2F-on-F2F (only if not using the PCB) | $2 | ₹100 |
| 0.5W LiPo (already in Cardputer) | Cardputer has a 120-300 mAh battery built in | — | — |
| External 868 MHz antenna with u.FL pigtail | Range upgrade beyond the stock spring antenna | $5–10 | ₹400–800 |

## About each part

### M5Stack Cardputer

The Cardputer is a card-sized ESP32-S3 dev board with a 1.14" TFT, 56-key QWERTY keyboard, IR transmitter, microSD slot, speaker, and Grove port. The **v1.1** revision (2025+) uses the M5StampS3A; older units have the StampS3. Both work with this project.

What we use from it:
- The display (240×135 pixels).
- The keyboard.
- The speaker (one tone beep on incoming).
- The **Grove port** exposing 5V, GND, GPIO 1, GPIO 2.

### Reyax RYLR998

A 868/915 MHz LoRa transceiver built on a Semtech LoRa core + Nuvoton MCU. You talk to it over a 3.3V UART with simple AT commands. Antenna is included in the box.

| Spec | Value |
|---|---|
| Operating voltage | 3.3V |
| Default baud rate | 115200 |
| Default frequency | 915 MHz (US units) or 868 MHz (EU/IN units), often shipped 865 MHz for Indian sellers |
| Max TX power | +22 dBm |
| Sensitivity | down to −148 dBm |
| Max payload (single packet) | 240 bytes |

### AMS1117 3.3V regulator (Robu Part 31179)

The Cardputer's Grove port supplies **5V**, but the RYLR998 wants **3.3V**. This little module is a linear LDO that drops 5V down to 3.3V. The Robu listing calls it "Part 31179". Three pins: **IN** (5V), **GND**, **OUT** (3.3V).

Any AMS1117-based 3.3V module works; you don't need this exact SKU. Just pick something rated for at least 300 mA (the RYLR998 can pull ~120 mA during TX bursts).

## Wiring

See the [main README](../README.md#wiring) for the diagram.

### The GND chain problem

The AMS1117 module has only **one** GND pin. You need GND from three places to meet at one electrical node:

1. The Cardputer Grove GND
2. The AMS1117 GND
3. The RYLR998 GND

With **F2F wires only** and **no breadboard**, the trick is to "chain" through the RYLR998's GND header pin:

```
Grove GND  ──→  RYLR998 GND  ──→  AMS1117 GND
```

Both wires plug into the **same physical pin** on the RYLR998. Methods to do that:

1. **Two female ends side-by-side** on one pin (works, slightly fragile).
2. **Twist the metal contacts** of two female ends together, then push onto the pin (more secure).
3. **Solder a stub** — solder a short wire to the RYLR998 GND pad, giving you a second connection point.
4. **Use one M-F jumper as a splitter**: plug its male end into RYLR998 GND, plug your two F2F wires into the dangling female ends.
5. **Use a tiny breadboard** — the cleanest solution. Even a 17-row mini breadboard works.

## Antennas — please attach

Always attach an antenna **before** powering the RYLR998. TX'ing into an open antenna port can damage the RF front-end. The Reyax box ships with a small spring antenna that screws onto the SMA connector — that's enough for testing.

## Regulatory note

LoRa runs in **ISM bands** that differ by country:

| Region | Allowed bands |
|---|---|
| EU | 868 MHz |
| US / Canada | 915 MHz |
| India | 865 MHz |
| Australia | 915–928 MHz |
| Japan | 920 MHz |

Configure with `/freq <Hz>` in the chat — e.g. `/freq 868500000` for EU, `/freq 915000000` for US, `/freq 865000000` for India. The RYLR998 is hardware-capable across the whole 410–930 MHz range, but it's your responsibility to stay within your local regulator's allowed bands and duty cycle.
