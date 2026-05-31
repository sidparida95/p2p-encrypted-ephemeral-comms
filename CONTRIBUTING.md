# Contributing

Thanks for thinking about contributing! This is a hobby/learning project, so the bar for contributions is "is it useful and does it work" — not "is it perfect".

## What's welcome

- 🐛 **Bug reports** — open an issue with what hardware you have, what you tried, and what happened.
- ✨ **Features** from the [roadmap](README.md#roadmap), or anything that fits the spirit of the project.
- 📖 **Docs improvements** — typos, clarifications, additional translations.
- 🌍 **Region-specific tweaks** — frequency presets, regulatory notes for your country.
- 🛠️ **Hardware variants** — getting this working on Cardputer Adv, CardputerZero, or other M5Stack devices.

## How to contribute

### Bug reports

Open a GitHub issue with the **Bug** template. Please include:

- Cardputer revision (v1.1 / Adv / Zero / which StampS3 variant)
- LoRa module model
- arduino-cli or Arduino IDE version
- ESP32 core version (`arduino-cli core list`)
- Exact error message or behaviour

### Pull requests

1. Fork the repo, create a branch from `main` (e.g. `feat/ack-packets`).
2. Make your change. Keep PRs focused — one logical change per PR.
3. **Test on real hardware** before submitting. Mention what you tested with in the PR description.
4. Update relevant docs (README, docs/USAGE.md, docs/PROTOCOL.md if you changed the wire format).
5. Open the PR with a clear description of *what* and *why*.

### Code style

- Match the existing style of `cardputer_lora_chat.ino`: 4-space indent, K&R braces, `camelCase` for variables/functions, `UPPER_SNAKE_CASE` for #defines.
- Keep helpers in `// ====== SECTION HEADERS ======` blocks.
- Prefer Arduino idioms (`String`, `delay()`, `Serial.println()`) over raw C — the audience is hobbyists.
- Avoid pulling in big dependencies. If you must, justify it in the PR.

### Security-sensitive changes

If your change touches the crypto code (`encryptMessage` / `decryptMessage` / key derivation) or the password handling:

- Be conservative. Read [`docs/PROTOCOL.md`](docs/PROTOCOL.md) first to understand the current threat model.
- Don't roll your own crypto primitives — stick with mbedtls.
- Don't reduce the security properties without documenting it loudly.
- Don't add features that look like security but aren't (e.g. trivial obfuscation marketed as encryption).

For severe security issues, see [`SECURITY.md`](SECURITY.md) — don't open a public issue, please.

## Don't ship binaries

This repo only contains source. We don't ship pre-built `.bin` files because:

1. Anyone running them is trusting the maintainer not to have backdoored them.
2. The unlock password and any default keys would be baked in.
3. Build settings vary per region (frequency, regulatory params).

Each user should build from source with their own password and frequency.

## Code of conduct

Be decent. No harassment, no slurs, no spam. Maintainers reserve the right to ban people who don't get it.

## Licence

By contributing, you agree your contributions will be released under the project's [MIT License](LICENSE).
