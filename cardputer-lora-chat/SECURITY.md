# Security policy

## What this project is and isn't

**Cardputer LoRa Chat is a hobby project.** It implements AES-256-CBC encryption using
mbedtls — that's real cryptography — but the surrounding protocol is intentionally simple
and has known limitations. **Do not use this firmware for anything where the cost of
message compromise is serious.**

See [`docs/PROTOCOL.md`](docs/PROTOCOL.md) for a full discussion of the threat model.

### Quick summary of what is NOT protected

- **Replay attacks** — an attacker who records a ciphertext can re-send it later; the receiver will decrypt it identically.
- **Tampering** — there is no message authentication code. A bit-flipped ciphertext might still decrypt to seemingly valid plaintext.
- **Password grinding** — the key derivation is just `SHA-256(password)`, with no salt and no work factor. Weak passwords fall to offline brute-force quickly.
- **Traffic analysis** — addresses, timing, and message lengths are visible to anyone with an SDR.
- **Local screen access** — the unlock password lives in plaintext in flash; anyone who can dump the chip can read it.

## Reporting a vulnerability

For non-critical issues, **open a public GitHub issue** with the `security` label.

For serious vulnerabilities (especially ones that affect the cryptographic correctness),
please report privately:

1. Open a **GitHub Security Advisory** on this repo (Security tab → "Report a vulnerability").
2. Include:
   - A clear description of the issue
   - Steps to reproduce
   - The version / commit you tested against
   - Suggested fix, if you have one

Maintainers will:
- Acknowledge within 7 days
- Triage and respond within 30 days
- Coordinate a fix and disclosure timeline with you

## Supported versions

This project doesn't yet have a tagged release. Until v1.0:

- **Latest `main`** — supported, fixes applied here first.
- **Older commits** — not supported; please update to `main`.

## A note on responsible use

LoRa runs in shared ISM bands. **Respect your local regulator's rules** on frequencies,
TX power, and duty cycle. Don't use LoRa for anything that's illegal in your jurisdiction.
The maintainers are not responsible for misuse.
