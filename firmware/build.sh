#!/usr/bin/env bash
# Build script for the Cardputer LoRa Chat firmware.
# Requires arduino-cli on PATH: https://arduino.github.io/arduino-cli/latest/installation/

set -e

SKETCH="cardputer_lora_chat.ino"
FQBN="esp32:esp32:m5stack_cardputer"
BOARD_URL="https://espressif.github.io/arduino-esp32/package_esp32_index.json"

cd "$(dirname "$0")"

echo "==> Initializing arduino-cli (no-op if already configured)"
arduino-cli config init --overwrite 2>/dev/null || true
arduino-cli config set board_manager.additional_urls "$BOARD_URL"

echo "==> Updating index"
arduino-cli core update-index

echo "==> Installing ESP32 core (skipped if already installed)"
arduino-cli core install esp32:esp32

echo "==> Installing libraries"
arduino-cli lib install "M5Cardputer"
arduino-cli lib install "M5Unified"
arduino-cli lib install "M5GFX"

echo "==> Compiling for $FQBN"
arduino-cli compile \
    --fqbn "$FQBN" \
    --export-binaries \
    --build-path "build" \
    "$SKETCH"

echo
echo "==> Done. Merged binary:"
echo "    build/${SKETCH}.merged.bin"
echo
echo "Flash with M5 Burner (Custom → Add → that file at offset 0x0)"
echo "or with esptool.py write_flash 0x0 <that file>"
