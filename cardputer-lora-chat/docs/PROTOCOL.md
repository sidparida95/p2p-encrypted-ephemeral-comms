# Protocol & cryptography

## LoRa packet format

The Cardputer talks to its local RYLR998 over UART using AT commands. The RYLR998 then puts whatever bytes you give it on the air as a single LoRa packet.

### Sending

```
AT+SEND=<dest>,<len>,<data>\r\n
```

- `<dest>` — receiver address. **0** means broadcast to everyone on the current `NETWORKID`.
- `<len>` — length of `<data>` in bytes (1–240).
- `<data>` — raw payload bytes.

This firmware always uses `<dest>=0` so messages reach every device on the same network.

### Receiving

The RYLR998 prints lines like:

```
+RCV=<sender_addr>,<len>,<data>,<rssi>,<snr>\r\n
```

The firmware reads `LoRa.available()`, accumulates until `\n`, then parses the `+RCV=` lines.

## Application-level message format

Inside `<data>`, the firmware uses two simple line formats:

| Format | Meaning |
|---|---|
| `<message>` | plain text (no prefix) |
| `ENC:<hex>` | AES-256-CBC encrypted blob, hex-encoded |

The `ENC:` prefix is how received messages get classified as locked.

## Encryption

When `/secure` is on, outgoing messages are protected with **AES-256 in CBC mode**, implemented via the ESP32's built-in **mbedtls**.

### Key derivation

```
key[32] = SHA-256(password)
```

The password is whatever the user types at the per-message Encrypt prompt. SHA-256 of that string becomes the 256-bit AES key. No salt, no iteration count, no Argon2 — this is *not* a password-derived encryption key in the OWASP sense. It's the simplest possible mapping from a user-typed string to a 256-bit key.

### Encryption procedure

1. Take the plaintext message (1–90 chars).
2. Prepend the literal bytes `LORA` (4 bytes). This acts as a key-validation tag.
3. PKCS7-pad the result up to the next 16-byte multiple.
4. Generate a random 16-byte **IV** using `esp_random()` (ESP32 hardware RNG).
5. Encrypt with AES-256-CBC, key + IV from above, padded plaintext.
6. Hex-encode `IV || ciphertext`.
7. Send as `ENC:<hex>` over LoRa.

### Decryption procedure

1. Strip `ENC:` prefix.
2. Hex-decode. First 16 bytes are the IV, the rest is ciphertext.
3. Derive key the same way: `sha256(password)`.
4. AES-256-CBC decrypt.
5. Strip PKCS7 padding. Verify the padding bytes are consistent (1–16, all equal).
6. Verify the first 4 plaintext bytes are exactly `LORA`. If not, the password was wrong → return failure.
7. Return the rest of the plaintext.

### Packet length budget

LoRa caps at 240 bytes per packet. The wire format is:

```
"ENC:" + hex(IV) + hex(ciphertext)
   4    +    32  +   2 × ceil((4 + len(msg) + 1)/16) × 16
```

For 90-char plaintext:
- After `LORA` prefix: 94 bytes
- PKCS7 padded to: 96 bytes
- Hex: 192 chars
- Total: `4 + 32 + 192 = 228` bytes. ✓ fits.

For 91-char plaintext, padding bumps to 112 bytes ciphertext → 224 hex chars → total 260 bytes, doesn't fit. So **90 is the conservative cap**.

## What this protects against

| Threat | Protected? |
|---|---|
| Casual eavesdropper with an SDR | ✓ ciphertext is opaque |
| Adversary recording your traffic, attacking the key later | ✓ if you used a strong, unique password per message |
| Adversary who can guess your password | ✗ no rate limit, no salt — they can grind offline |
| Adversary modifying your messages in flight | ✗ no MAC; tampering would corrupt the plaintext, but the `LORA` magic catches *most* tampering by accident |
| Replay attacks | ✗ no nonce tracking; same ciphertext re-played would decrypt to the same plaintext |
| Traffic analysis (timing, lengths, addresses) | ✗ everything is visible to anyone with an RX |

This is **not** Signal. It's a simple, honest "scramble the bytes with a shared password" layer that's perfectly fine for low-stakes hobby use (e.g. exchanging coordinates at a hackathon) and meaningfully better than plaintext for anything sensitive. For actually-secure messaging, add an authenticated mode like AES-GCM and a real KDF like Argon2id.

## Future work

A few improvements that would make this much stronger, in roughly increasing complexity:

1. **HMAC** the ciphertext so tampering and replays are detectable.
2. **Use AES-GCM** instead of CBC — gets auth and confidentiality from one primitive.
3. **PBKDF2 / Argon2** for password derivation, so offline password grinding is expensive.
4. **Per-message sequence numbers** in the plaintext, rejected if not strictly increasing per sender — kills replay.
5. **ECDH key exchange** so peers can negotiate a session key without sharing a password out-of-band.
6. **Forward secrecy** via X3DH-like ratchet — losing today's key doesn't unlock yesterday's traffic.

PRs welcome on any of the above.
