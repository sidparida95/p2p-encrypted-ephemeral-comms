# Changelog

All notable changes to this project will be documented here.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project (will eventually) adhere to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial public release
- Password-locked boot screen
- Two-way LoRa chat over RYLR998 modules
- Slash commands for live radio control (`/freq`, `/net`, `/addr`, `/pwr`, `/info`)
- `/at <ATCMD>` debug command for raw AT access to the RYLR998
- `/secure` mode with AES-256-CBC encryption via mbedtls
  - Per-message passwords
  - Random 16-byte IV per message
  - SHA-256 password-to-key derivation
  - `LORA` magic prefix for key validation
- `/d <N>` decrypt command for received encrypted messages
- `/lock` command to re-lock the device mid-session
- Audible beep on incoming messages
- Status bar showing current freq, network, address, and secure-mode indicator
- Colour-coded chat log (sent / received / encrypted / decrypted / system / error)

### Documentation
- README with cost estimates and hardware sourcing
- Wiring diagram, system architecture, state machine, and encryption flow SVGs
- Detailed hardware BOM
- Build & flash guide covering Arduino IDE, arduino-cli, and PlatformIO
- Usage guide
- Protocol / cryptography document
- Contributing guide
- Security policy

### Hardware
- Open-source PCB carrier board (50 × 22 mm, 2-layer) for clean assembly
- `generate_gerbers.py` — single-file Python script that emits manufacturable Gerber X2 + Excellon 2 files (no CAD required)
- Pre-built `gerbers.zip` ready to upload to Robu / JLCPCB / PCBWay
- Schematic + board preview SVGs
- ~₹90 / $1.20 per assembled board (qty 10 batch)
