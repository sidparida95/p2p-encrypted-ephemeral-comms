@echo off
REM Build script for the Cardputer LoRa Chat firmware.
REM Requires arduino-cli on PATH: https://arduino.github.io/arduino-cli/latest/installation/

setlocal
cd /d "%~dp0"

set SKETCH=cardputer_lora_chat.ino
set FQBN=esp32:esp32:m5stack_cardputer
set BOARD_URL=https://espressif.github.io/arduino-esp32/package_esp32_index.json

echo ==^> Initializing arduino-cli
arduino-cli config init --overwrite 2>nul
arduino-cli config set board_manager.additional_urls %BOARD_URL%

echo ==^> Updating index
arduino-cli core update-index
if errorlevel 1 goto fail

echo ==^> Installing ESP32 core
arduino-cli core install esp32:esp32
if errorlevel 1 goto fail

echo ==^> Installing libraries
arduino-cli lib install "M5Cardputer"
arduino-cli lib install "M5Unified"
arduino-cli lib install "M5GFX"

echo ==^> Compiling
arduino-cli compile --fqbn %FQBN% --export-binaries --build-path build %SKETCH%
if errorlevel 1 goto fail

echo.
echo ==^> Done. Merged binary:
echo     build\%SKETCH%.merged.bin
echo.
echo Flash with M5 Burner (Custom -^> Add -^> that file at offset 0x0)
echo or with esptool.py write_flash 0x0 ^<that file^>
goto :eof

:fail
echo.
echo Build failed.
exit /b 1
