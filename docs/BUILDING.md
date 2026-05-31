# Building & flashing

Three supported paths — pick the one that matches your setup.

## Option A — Arduino IDE (GUI, easiest first-time)

1. **Install Arduino IDE 2.x**: https://www.arduino.cc/en/software
2. Open **File → Preferences** and add this to *Additional Boards Manager URLs*:
   ```
   https://espressif.github.io/arduino-esp32/package_esp32_index.json
   ```
3. **Tools → Board → Boards Manager**, search `esp32`, install **"esp32" by Espressif Systems** (3.0.0 or newer).
4. **Tools → Manage Libraries**, install the latest versions of:
   - **M5Cardputer** (by M5Stack)
   - **M5Unified** (by M5Stack)
   - **M5GFX** (by M5Stack)
5. Open `firmware/cardputer_lora_chat.ino`.
6. **Tools → Board → ESP32 Arduino → M5Stack-Cardputer**. (If you only see *StampS3*, that's fine too — it's the same chip.)
7. **Tools → USB CDC On Boot → Enabled**.
8. Plug in the Cardputer. **Tools → Port** → select its serial port.
9. Click the **Upload** button (→).

Done. The device reboots into the password screen.

## Option B — arduino-cli (recommended for repeat builds)

```bash
# Install arduino-cli (once)
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
sudo mv bin/arduino-cli /usr/local/bin/   # or any folder in PATH

cd firmware

# First-time setup: installs ESP32 core + libraries (takes ~5 minutes, downloads ~200MB)
./build.sh               # Linux / macOS
# or
build.bat                # Windows

# Plug in the Cardputer, find its port
arduino-cli board list

# Compile + flash in one step
arduino-cli compile --fqbn esp32:esp32:m5stack_cardputer \
    --upload --port /dev/cu.usbmodem2101 \
    cardputer_lora_chat.ino
```

If your installed core uses the old hyphenated FQBN, use `esp32:esp32:m5stack-cardputer` instead.

## Option C — PlatformIO

```bash
cd firmware
pio run                    # build
pio run -t upload          # build + upload
```

The merged binary will be at `.pio/build/cardputer/firmware.bin`.

## Producing a `.bin` file (no flashing)

If you want a binary you can flash later or distribute:

```bash
arduino-cli compile --fqbn esp32:esp32:m5stack_cardputer \
    --export-binaries \
    cardputer_lora_chat.ino
```

This produces, in the `build/esp32.esp32.m5stack_cardputer/` folder:

| File | What it is |
|---|---|
| `cardputer_lora_chat.ino.bin` | App binary only — use for **SD-card launchers** (M5Launcher, Bruce) |
| `cardputer_lora_chat.ino.merged.bin` | Full image including bootloader — use for **M5Burner** or direct esptool flash |
| `cardputer_lora_chat.ino.bootloader.bin` | Bootloader only — not usually needed |
| `cardputer_lora_chat.ino.partitions.bin` | Partition table — not usually needed |

### Flashing the merged binary with M5Burner

1. Open M5Burner (https://docs.m5stack.com/en/uiflow/m5burner/intro).
2. The "Custom" option lives under **My Burner** in v3.x. If you don't see it, use arduino-cli or esptool instead.
3. Browse to `cardputer_lora_chat.ino.merged.bin`, flash address `0x0`.

### Flashing with esptool.py

```bash
pip install esptool

esptool.py --chip esp32s3 --port /dev/cu.usbmodem2101 \
    --baud 921600 write_flash 0x0 \
    build/esp32.esp32.m5stack_cardputer/cardputer_lora_chat.ino.merged.bin
```

### Loading via SD card launcher

If you have **M5Launcher**, **Bruce**, or another community launcher on the other Cardputer:

1. Copy `cardputer_lora_chat.ino.bin` (the **non-merged** one) to the SD card.
2. Drop it in the launcher's apps folder. Typical paths:
   - `M5Launcher`: `/apps/LoRaChat.bin`
   - `Bruce`: `/bruce/apps/LoRaChat.bin`
3. Eject SD, insert into the Cardputer, boot, and run from the launcher menu.

## Troubleshooting

### "Sketch missing" / "main file missing"

Arduino requires the `.ino` filename to match its parent folder name. If you renamed one, rename the other to match. E.g. if your folder is `my_chat/`, the sketch must be `my_chat.ino`.

### Upload fails with "Failed to connect"

The Cardputer isn't in download mode. Hold **G0** on top of the StampS3, press and release **RST**, then release **G0**. Re-run the upload command.

### "Compiling..." appears stuck

First-time builds download the ESP32 toolchain (~200 MB) and compile dozens of files. Allow 3–5 minutes. Re-run with `-v` for verbose output if you want to see progress.

### After flashing, screen stays blank

Press **RST** once (top of the StampS3 module). If still blank, power-cycle with the side switch.

### `<M5Cardputer.h>` not found

Make sure all three M5Stack libraries are installed: `M5Cardputer`, `M5Unified`, `M5GFX`. The build scripts install them automatically; in Arduino IDE you do it manually under Tools → Manage Libraries.
