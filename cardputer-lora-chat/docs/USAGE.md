# Usage

## Boot sequence

1. **Power on.** Side switch ON, or plug in USB-C.
2. **Lock screen** appears: "LoRa Chat / Enter password:".
3. Type the unlock password (default `letmein` — change this in the source before flashing).
4. Press **Enter**. Two ascending beeps mean unlocked; the chat screen appears.

## The chat screen

```
┌────────────────────────────────────────┐
│  865.000MHz N:18 A:1  [SEC]            │  ← status bar (red [SEC] only in secure mode)
├────────────────────────────────────────┤
│  * LoRa ready                          │  ← yellow:  system messages
│  > hello                               │  ← green:   sent (plain)
│  < [2] hi back                         │  ← cyan:    received (plain)
│  > [SEC] my secret thing               │  ← orange:  sent (encrypted)
│  < [2] [ENC #3]                        │  ← magenta: received encrypted, locked
│  # #3: the actual secret               │  ← y-green: decrypted plaintext
│  ! decryption failed                   │  ← red:     errors
│                                        │
├────────────────────────────────────────┤
│ > type here_                           │  ← input line (prefix ">!" in secure mode)
└────────────────────────────────────────┘
```

## Sending a message

- Type, press Enter. Broadcast on the current network.
- Anyone with a Cardputer (or other RYLR998) on the same `freq` + `network ID` will receive it.

## Commands

All commands start with `/`. Type them into the input line and press Enter.

| Command | Action | Example |
|---|---|---|
| `/help` | List commands | `/help` |
| `/freq <Hz>` | Change LoRa frequency | `/freq 868500000` |
| `/net <n>` | Set network ID (peers must match) | `/net 7` |
| `/addr <n>` | Set my LoRa address | `/addr 2` |
| `/pwr <n>` | TX power, 0–22 dBm | `/pwr 14` |
| `/info` | Show current radio settings | `/info` |
| `/clear` | Clear chat history | `/clear` |
| `/lock` | Re-lock the device | `/lock` |
| `/at <ATCMD>` | Send raw AT command to RYLR998 | `/at AT+BAND?` |
| `/secure` | Toggle encrypted send mode | `/secure` |
| `/d <N>` | Decrypt received encrypted msg #N | `/d 3` |

## Secure mode walkthrough

1. Type `/secure` → bar shows `[SEC]`, log says `* secure mode ON`.
2. Type "meet me at 9pm" → Enter.
3. **Encrypt prompt** appears. Type any password (e.g. `tuesday`) → Enter.
4. Your screen shows `> [SEC] meet me at 9pm` in orange. Message goes out as `ENC:<hex>`.

On the recipient:

5. Their screen shows `< [1] [ENC #3]` (magenta).
6. They type `/d 3` → **Decrypt prompt** appears.
7. They type `tuesday` → Enter.
8. Their screen shows `# #3: meet me at 9pm` in yellow-green.

Wrong password → `! decryption failed`. The locked message stays in the log; they can try again.

Empty password + Enter at either prompt cancels and returns to chat.

## Setting up two devices

For Cardputer A and Cardputer B to talk:

1. Flash both with this firmware.
2. On each, run `/info` — verify they show the **same** frequency and network ID.
3. Give them **different** addresses: leave A at default `1`, on B run `/addr 2`.
4. From A, type a message. B should show `< [1] your message`.
5. From B, type a message. A should show `< [2] your message`.

If nothing appears:

- Run `/at AT` on both — expect `+OK`. No response → wiring problem.
- Run `/at AT+BAND?` on both — they must match.
- Confirm antennas are attached.
- Move them ~2 metres apart — too close can saturate.

See [`BUILDING.md`](BUILDING.md#troubleshooting) for more troubleshooting steps.

## Tips

- The **status bar** is always visible; glance at it to confirm freq and addr.
- The **input line** caches what you type even after a slash command, so `/info` then keep typing — your draft is preserved.
- **Encrypted messages have a 90-character plaintext limit** to fit in LoRa's 240-byte packet after AES + IV + hex encoding.
- **`/secure` only protects outgoing messages.** Plain messages still go out plain; this is by design so you can mix both. Toggle `/secure` again to go back to plain mode.
- **`/lock` doesn't clear the chat log.** Anyone with the unlock password can scroll back through what's there. Use `/clear` first if you're handing the device to someone.
