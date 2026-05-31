/*
 * Cardputer LoRa Chat (with /secure mode)
 * Two-way LoRa chat for M5Stack Cardputer using RYLR998
 *
 * Wiring:
 *   Cardputer Grove pin 1 (5V)     -> AMS1117 (Part 31179) IN
 *   Cardputer Grove pin 2 (GND)    -> RYLR998 GND (chained to AMS1117 GND)
 *   Cardputer Grove pin 3 (G2/IO2) -> RYLR998 TXD
 *   Cardputer Grove pin 4 (G1/IO1) -> RYLR998 RXD
 *   AMS1117 OUT (3.3V)             -> RYLR998 VCC
 *
 * Slash commands (typed into the input line):
 *   /help                 - list commands
 *   /freq <Hz>            - change frequency, e.g. /freq 868500000
 *   /addr <n>             - set my address (0..65535)
 *   /net  <n>             - set network ID (must match peers)
 *   /pwr  <n>             - TX power 0..22 dBm
 *   /info                 - show current settings
 *   /clear                - clear chat log
 *   /lock                 - re-lock the device (password required again)
 *   /at  <ATCMD>          - send raw AT command to RYLR998 (debug)
 *   /secure               - toggle secure (encrypted) sending mode
 *   /d   <N>              - decrypt encrypted message #N (prompts for password)
 *
 * Secure mode (AES-256-CBC with SHA-256 of password as key):
 *   - Toggle with /secure. Status bar shows [SEC] when active.
 *   - When you type a message and press Enter, the device prompts for a
 *     per-message password.
 *   - Message is encrypted and broadcast as "ENC:<hex_iv><hex_cipher>".
 *   - Received encrypted messages appear as "< [ENC #N]" (locked).
 *   - Decrypt with "/d N" and enter the password.
 *   - Wrong password -> "! decryption failed" (the message stays locked).
 *
 * NOTE: Encryption is real (mbedtls AES-256-CBC) but there is no key exchange
 * - both ends must agree on the per-message password out of band.
 */

#include <M5Cardputer.h>
#include <mbedtls/md.h>
#include <mbedtls/aes.h>
#include <esp_random.h>

// ============== USER CONFIG ==============
const char* PASSWORD = "letmein";   // device unlock password (NOT the encryption password)

#define LORA_RX_PIN  2     // Cardputer GPIO2 (G2) <- RYLR998 TXD
#define LORA_TX_PIN  1     // Cardputer GPIO1 (G1) -> RYLR998 RXD
#define LORA_BAUD    115200

uint32_t loraFreq    = 865000000;
int      loraNetId   = 18;
int      loraMyAddr  = 1;
int      loraTxPower = 22;

#define MAX_SECURE_MSG  90   // chars; encrypted+hex must fit in 240-byte LoRa payload
// =========================================

HardwareSerial LoRa(1);
M5Canvas canvas(&M5Cardputer.Display);

// ---------- UI state ----------
enum AppState {
    STATE_PASSWORD,    // initial unlock screen
    STATE_CHAT,        // normal chat
    STATE_ENC_PROMPT,  // entering password to encrypt outgoing message
    STATE_DEC_PROMPT   // entering password to decrypt a received message
};
AppState state = STATE_PASSWORD;

String inputBuffer = "";
String pwBuffer    = "";   // shared buffer for password entry

// chat log: parallel arrays
#define MAX_LINES 40
String chatLog[MAX_LINES];      // display text
String chatCipher[MAX_LINES];   // hex IV+ciphertext for received encrypted msgs
int    chatEncId[MAX_LINES];    // visible ID (>0) for encrypted msgs, else 0
int    chatHead  = 0;
int    chatCount = 0;
int    nextEncId = 1;

bool   secureMode = false;
String pendingEncryptText = "";   // typed message waiting for password to encrypt
int    pendingDecryptIdx  = -1;   // chat log slot waiting to be decrypted

String rxBuffer = "";

// ====================================================================
// CRYPTO HELPERS
// ====================================================================

static void sha256(const uint8_t* in, size_t len, uint8_t out[32]) {
    const mbedtls_md_info_t* info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
    mbedtls_md_context_t ctx;
    mbedtls_md_init(&ctx);
    mbedtls_md_setup(&ctx, info, 0);
    mbedtls_md_starts(&ctx);
    mbedtls_md_update(&ctx, in, len);
    mbedtls_md_finish(&ctx, out);
    mbedtls_md_free(&ctx);
}

static void deriveKey(const String& password, uint8_t key[32]) {
    sha256((const uint8_t*)password.c_str(), password.length(), key);
}

static String hexEncode(const uint8_t* data, size_t len) {
    static const char* hexchars = "0123456789abcdef";
    String s;
    s.reserve(len * 2);
    for (size_t i = 0; i < len; i++) {
        s += hexchars[(data[i] >> 4) & 0xf];
        s += hexchars[data[i] & 0xf];
    }
    return s;
}

static int hexNibble(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

static bool hexDecode(const String& hex, uint8_t* out, size_t outLen) {
    if (hex.length() != outLen * 2) return false;
    for (size_t i = 0; i < outLen; i++) {
        int hi = hexNibble(hex.charAt(i * 2));
        int lo = hexNibble(hex.charAt(i * 2 + 1));
        if (hi < 0 || lo < 0) return false;
        out[i] = (uint8_t)((hi << 4) | lo);
    }
    return true;
}

// Encrypt plaintext with password. Returns hex(IV) + hex(ciphertext).
// Plaintext is prepended with the magic "LORA" so we can validate the
// password on decrypt.
static String encryptMessage(const String& plaintext, const String& password) {
    uint8_t key[32];
    deriveKey(password, key);

    String marked = "LORA" + plaintext;
    size_t plainLen = marked.length();
    size_t padLen   = 16 - (plainLen % 16);    // PKCS7: always 1..16 padding bytes
    size_t totalLen = plainLen + padLen;

    if (totalLen > 240) return "";   // sanity

    uint8_t padded[256];
    memcpy(padded, marked.c_str(), plainLen);
    memset(padded + plainLen, (uint8_t)padLen, padLen);

    uint8_t iv[16];
    for (int i = 0; i < 16; i++) iv[i] = (uint8_t)esp_random();
    uint8_t ivWork[16];
    memcpy(ivWork, iv, 16);

    uint8_t ciphertext[256];
    mbedtls_aes_context aes;
    mbedtls_aes_init(&aes);
    mbedtls_aes_setkey_enc(&aes, key, 256);
    mbedtls_aes_crypt_cbc(&aes, MBEDTLS_AES_ENCRYPT, totalLen, ivWork, padded, ciphertext);
    mbedtls_aes_free(&aes);

    return hexEncode(iv, 16) + hexEncode(ciphertext, totalLen);
}

// Returns plaintext on success, "" on failure (bad hex / bad padding / wrong password)
static String decryptMessage(const String& hex, const String& password) {
    if (hex.length() < 64 || (hex.length() % 2) != 0) return "";

    uint8_t key[32];
    deriveKey(password, key);

    uint8_t iv[16];
    if (!hexDecode(hex.substring(0, 32), iv, 16)) return "";

    size_t cipherLen = (hex.length() - 32) / 2;
    if (cipherLen == 0 || cipherLen % 16 != 0 || cipherLen > 256) return "";

    uint8_t ciphertext[256];
    if (!hexDecode(hex.substring(32), ciphertext, cipherLen)) return "";

    uint8_t plaintext[256];
    mbedtls_aes_context aes;
    mbedtls_aes_init(&aes);
    mbedtls_aes_setkey_dec(&aes, key, 256);
    mbedtls_aes_crypt_cbc(&aes, MBEDTLS_AES_DECRYPT, cipherLen, iv, ciphertext, plaintext);
    mbedtls_aes_free(&aes);

    uint8_t padLen = plaintext[cipherLen - 1];
    if (padLen == 0 || padLen > 16 || padLen > cipherLen) return "";
    for (size_t i = cipherLen - padLen; i < cipherLen; i++) {
        if (plaintext[i] != padLen) return "";
    }
    size_t plainLen = cipherLen - padLen;
    if (plainLen < 4 || memcmp(plaintext, "LORA", 4) != 0) return "";   // wrong password

    String result;
    result.reserve(plainLen - 4);
    for (size_t i = 4; i < plainLen; i++) result += (char)plaintext[i];
    return result;
}

// ====================================================================
// CHAT LOG
// ====================================================================

void addEntry(const String& display, const String& cipherHex, int encId) {
    int idx = (chatHead + chatCount) % MAX_LINES;
    if (chatCount < MAX_LINES) {
        chatLog[idx]   = display;
        chatCipher[idx]= cipherHex;
        chatEncId[idx] = encId;
        chatCount++;
    } else {
        chatLog[chatHead]    = display;
        chatCipher[chatHead] = cipherHex;
        chatEncId[chatHead]  = encId;
        chatHead = (chatHead + 1) % MAX_LINES;
    }
}

void addLine(const String& s) { addEntry(s, "", 0); }

// ====================================================================
// DRAWING
// ====================================================================

void drawPassword() {
    canvas.fillSprite(BLACK);
    canvas.setTextColor(WHITE);
    canvas.setTextSize(2);
    canvas.setCursor(40, 20);
    canvas.print("LoRa Chat");

    canvas.setTextSize(1);
    canvas.setTextColor(LIGHTGREY);
    canvas.setCursor(20, 55);
    canvas.print("Enter password:");

    canvas.setTextColor(GREENYELLOW);
    canvas.setCursor(20, 75);
    String masked = "";
    for (size_t i = 0; i < pwBuffer.length(); i++) masked += '*';
    canvas.print("> " + masked + "_");

    canvas.setTextColor(DARKGREY);
    canvas.setCursor(20, 110);
    canvas.print("[Enter] to unlock");

    canvas.pushSprite(0, 0);
}

void drawPwPrompt(const String& title, const String& hint) {
    canvas.fillSprite(BLACK);
    canvas.setTextColor(YELLOW);
    canvas.setTextSize(2);
    canvas.setCursor(20, 14);
    canvas.print(title);

    canvas.setTextSize(1);
    canvas.setTextColor(LIGHTGREY);
    canvas.setCursor(20, 50);
    canvas.print(hint);

    canvas.setTextColor(WHITE);
    canvas.setCursor(20, 72);
    String masked = "";
    for (size_t i = 0; i < pwBuffer.length(); i++) masked += '*';
    canvas.print("> " + masked + "_");

    canvas.setTextColor(DARKGREY);
    canvas.setCursor(20, 102);
    canvas.print("[Enter] confirm");
    canvas.setCursor(20, 116);
    canvas.print("(empty + Enter = cancel)");

    canvas.pushSprite(0, 0);
}

void drawChat() {
    canvas.fillSprite(BLACK);

    // Status bar
    canvas.fillRect(0, 0, 240, 12, NAVY);
    canvas.setTextSize(1);
    canvas.setTextColor(WHITE, NAVY);
    canvas.setCursor(2, 2);
    canvas.printf("%.3fMHz N:%d A:%d", loraFreq / 1e6, loraNetId, loraMyAddr);
    if (secureMode) {
        canvas.setTextColor(RED, NAVY);
        canvas.print(" [SEC]");
    }

    const int yStart     = 14;
    const int lineHeight = 10;
    const int inputBarY  = 122;
    const int maxLines   = (inputBarY - yStart) / lineHeight;

    int start = (chatCount > maxLines) ? (chatCount - maxLines) : 0;
    for (int i = start; i < chatCount; i++) {
        int idx = (chatHead + i) % MAX_LINES;
        int y = yStart + (i - start) * lineHeight;

        String line = chatLog[idx];
        uint16_t color = WHITE;
        if      (line.startsWith("> [SEC]")) color = ORANGE;
        else if (line.startsWith("> "))      color = GREEN;
        else if (line.startsWith("< [")  && chatEncId[idx] > 0) color = MAGENTA;
        else if (line.startsWith("< "))      color = CYAN;
        else if (line.startsWith("# "))      color = GREENYELLOW;   // decrypted
        else if (line.startsWith("* "))      color = YELLOW;
        else if (line.startsWith("! "))      color = RED;

        canvas.setTextColor(color, BLACK);
        canvas.setCursor(2, y);
        if (line.length() > 39) line = line.substring(0, 39);
        canvas.print(line);
    }

    // Input bar
    canvas.fillRect(0, inputBarY, 240, 13, DARKGREY);
    canvas.setTextColor(WHITE, DARKGREY);
    canvas.setCursor(2, inputBarY + 2);
    String shown = inputBuffer + "_";
    if (shown.length() > 37) shown = "..." + shown.substring(shown.length() - 34);
    canvas.print((secureMode ? ">!" : "> ") + shown);

    canvas.pushSprite(0, 0);
}

// ====================================================================
// LORA AT
// ====================================================================

void sendAT(const String& cmd) {
    LoRa.print(cmd);
    LoRa.print("\r\n");
}

String readATResponse(uint32_t timeoutMs = 400) {
    String resp = "";
    uint32_t start = millis();
    while (millis() - start < timeoutMs) {
        while (LoRa.available()) resp += (char)LoRa.read();
        delay(2);
    }
    return resp;
}

void configureLoRa() {
    delay(200);
    while (LoRa.available()) LoRa.read();
    sendAT("AT");                                    readATResponse(200);
    sendAT("AT+BAND="      + String(loraFreq));      readATResponse(200);
    sendAT("AT+NETWORKID=" + String(loraNetId));     readATResponse(200);
    sendAT("AT+ADDRESS="   + String(loraMyAddr));    readATResponse(200);
    sendAT("AT+CRFOP="     + String(loraTxPower));   readATResponse(200);
}

void sendPlainMessage(const String& msg) {
    String cmd = "AT+SEND=0," + String(msg.length()) + "," + msg;
    sendAT(cmd);
    readATResponse(200);
    addLine("> " + msg);
}

void sendEncrypted(const String& plaintext, const String& password) {
    if (plaintext.length() > MAX_SECURE_MSG) {
        addLine("! too long (max " + String(MAX_SECURE_MSG) + ")");
        return;
    }
    String hex = encryptMessage(plaintext, password);
    if (hex.length() == 0) { addLine("! encrypt failed"); return; }
    String payload = "ENC:" + hex;
    if (payload.length() > 240) { addLine("! payload too long"); return; }

    String cmd = "AT+SEND=0," + String(payload.length()) + "," + payload;
    sendAT(cmd);
    readATResponse(300);

    String preview = plaintext;
    if (preview.length() > 28) preview = preview.substring(0, 28) + "...";
    addLine("> [SEC] " + preview);
}

void processLoRaIncoming() {
    while (LoRa.available()) {
        char c = LoRa.read();
        if (c == '\n') {
            rxBuffer.trim();
            if (rxBuffer.startsWith("+RCV=")) {
                String payload = rxBuffer.substring(5);
                int c1 = payload.indexOf(',');
                int c2 = payload.indexOf(',', c1 + 1);
                if (c1 > 0 && c2 > c1) {
                    int fromAddr = payload.substring(0, c1).toInt();
                    int len = payload.substring(c1 + 1, c2).toInt();
                    String rest = payload.substring(c2 + 1);
                    if ((int)rest.length() >= len) {
                        String data = rest.substring(0, len);
                        if (data.startsWith("ENC:")) {
                            String hex = data.substring(4);
                            int id = nextEncId++;
                            String disp = "< [" + String(fromAddr) + "] [ENC #" + String(id) + "]";
                            addEntry(disp, hex, id);
                        } else {
                            addLine("< [" + String(fromAddr) + "] " + data);
                        }
                        M5Cardputer.Speaker.tone(2000, 30);
                    }
                }
            }
            rxBuffer = "";
        } else if (c != '\r') {
            rxBuffer += c;
            if (rxBuffer.length() > 500) rxBuffer = "";
        }
    }
}

// ====================================================================
// COMMAND PARSER
// ====================================================================

int findEncEntry(int n) {
    for (int i = 0; i < chatCount; i++) {
        int idx = (chatHead + i) % MAX_LINES;
        if (chatEncId[idx] == n && chatCipher[idx].length() > 0) return idx;
    }
    return -1;
}

void handleCommand(String cmd) {
    cmd.trim();
    if (cmd == "/help") {
        addLine("* /freq /addr /net /pwr");
        addLine("* /info /clear /lock /at");
        addLine("* /secure (toggle)  /d N");
    } else if (cmd.startsWith("/freq ")) {
        uint32_t f = (uint32_t) cmd.substring(6).toInt();
        if (f >= 410000000UL && f <= 930000000UL) {
            loraFreq = f;
            sendAT("AT+BAND=" + String(loraFreq));
            readATResponse(300);
            addLine("* freq -> " + String(loraFreq));
        } else addLine("! bad freq (410M-930M)");
    } else if (cmd.startsWith("/addr ")) {
        int a = cmd.substring(6).toInt();
        if (a < 0 || a > 65535) { addLine("! addr 0-65535"); return; }
        loraMyAddr = a;
        sendAT("AT+ADDRESS=" + String(a));
        readATResponse(300);
        addLine("* addr -> " + String(a));
    } else if (cmd.startsWith("/net ")) {
        int n = cmd.substring(5).toInt();
        loraNetId = n;
        sendAT("AT+NETWORKID=" + String(n));
        readATResponse(300);
        addLine("* net -> " + String(n));
    } else if (cmd.startsWith("/pwr ")) {
        int p = cmd.substring(5).toInt();
        if (p < 0) p = 0; if (p > 22) p = 22;
        loraTxPower = p;
        sendAT("AT+CRFOP=" + String(p));
        readATResponse(300);
        addLine("* pwr -> " + String(p));
    } else if (cmd == "/clear") {
        chatCount = 0; chatHead = 0;
    } else if (cmd == "/info") {
        addLine("* freq=" + String(loraFreq));
        addLine("* net=" + String(loraNetId) + " adr=" + String(loraMyAddr) + " pwr=" + String(loraTxPower));
        addLine("* secure=" + String(secureMode ? "ON" : "OFF"));
    } else if (cmd == "/lock") {
        state = STATE_PASSWORD;
        inputBuffer = ""; pwBuffer = "";
        drawPassword();
    } else if (cmd.startsWith("/at ")) {
        String at = cmd.substring(4);
        sendAT(at);
        String r = readATResponse(500);
        r.replace("\r", " "); r.replace("\n", " "); r.trim();
        if (r.length() == 0) addLine("! no response");
        else                 addLine("> " + r.substring(0, min((int)r.length(), 38)));
    } else if (cmd == "/secure") {
        secureMode = !secureMode;
        addLine(secureMode ? "* secure mode ON" : "* secure mode OFF");
    } else if (cmd.startsWith("/d ") || cmd.startsWith("/decrypt ")) {
        int sp = cmd.indexOf(' ');
        int n = cmd.substring(sp + 1).toInt();
        int idx = findEncEntry(n);
        if (idx < 0) { addLine("! no encrypted msg #" + String(n)); return; }
        pendingDecryptIdx = idx;
        pwBuffer = "";
        state = STATE_DEC_PROMPT;
        drawPwPrompt("Decrypt", "password for #" + String(n));
    } else {
        addLine("! unknown cmd, try /help");
    }
}

// ====================================================================
// SETUP / LOOP
// ====================================================================

void setup() {
    auto cfg = M5.config();
    M5Cardputer.begin(cfg, true);
    M5Cardputer.Display.setRotation(1);
    M5Cardputer.Display.setBrightness(180);

    canvas.createSprite(240, 135);
    canvas.setFont(&fonts::Font0);

    LoRa.begin(LORA_BAUD, SERIAL_8N1, LORA_RX_PIN, LORA_TX_PIN);
    delay(400);
    configureLoRa();

    addLine("* LoRa ready");
    addLine("* /help for commands");

    drawPassword();
}

void loop() {
    M5Cardputer.update();

    // ----- INITIAL UNLOCK -----
    if (state == STATE_PASSWORD) {
        if (M5Cardputer.Keyboard.isChange() && M5Cardputer.Keyboard.isPressed()) {
            Keyboard_Class::KeysState ks = M5Cardputer.Keyboard.keysState();
            for (auto c : ks.word) if (pwBuffer.length() < 60) pwBuffer += c;
            if (ks.del && pwBuffer.length() > 0) pwBuffer.remove(pwBuffer.length() - 1);
            if (ks.enter) {
                if (pwBuffer == String(PASSWORD)) {
                    state = STATE_CHAT;
                    pwBuffer = "";
                    M5Cardputer.Speaker.tone(1500, 80); delay(90);
                    M5Cardputer.Speaker.tone(2200, 80);
                    drawChat();
                    return;
                } else {
                    pwBuffer = "";
                    canvas.fillSprite(RED);
                    canvas.setTextColor(WHITE);
                    canvas.setTextSize(3);
                    canvas.setCursor(50, 50);
                    canvas.print("WRONG");
                    canvas.pushSprite(0, 0);
                    M5Cardputer.Speaker.tone(400, 200);
                    delay(800);
                }
            }
            drawPassword();
        }
        return;
    }

    // ----- ENCRYPT PASSWORD PROMPT -----
    if (state == STATE_ENC_PROMPT) {
        if (M5Cardputer.Keyboard.isChange() && M5Cardputer.Keyboard.isPressed()) {
            Keyboard_Class::KeysState ks = M5Cardputer.Keyboard.keysState();
            for (auto c : ks.word) if (pwBuffer.length() < 60) pwBuffer += c;
            if (ks.del && pwBuffer.length() > 0) pwBuffer.remove(pwBuffer.length() - 1);
            if (ks.enter) {
                if (pwBuffer.length() == 0) {
                    addLine("* encrypt cancelled");
                } else {
                    sendEncrypted(pendingEncryptText, pwBuffer);
                }
                pwBuffer = "";
                pendingEncryptText = "";
                state = STATE_CHAT;
                drawChat();
                return;
            }
            drawPwPrompt("Encrypt", "password for this msg");
        }
        return;
    }

    // ----- DECRYPT PASSWORD PROMPT -----
    if (state == STATE_DEC_PROMPT) {
        if (M5Cardputer.Keyboard.isChange() && M5Cardputer.Keyboard.isPressed()) {
            Keyboard_Class::KeysState ks = M5Cardputer.Keyboard.keysState();
            for (auto c : ks.word) if (pwBuffer.length() < 60) pwBuffer += c;
            if (ks.del && pwBuffer.length() > 0) pwBuffer.remove(pwBuffer.length() - 1);
            if (ks.enter) {
                if (pwBuffer.length() == 0) {
                    addLine("* decrypt cancelled");
                } else if (pendingDecryptIdx >= 0) {
                    String hex   = chatCipher[pendingDecryptIdx];
                    int    id    = chatEncId[pendingDecryptIdx];
                    String plain = decryptMessage(hex, pwBuffer);
                    if (plain.length() == 0) addLine("! decryption failed");
                    else                     addLine("# #" + String(id) + ": " + plain);
                }
                pwBuffer = "";
                pendingDecryptIdx = -1;
                state = STATE_CHAT;
                drawChat();
                return;
            }
            drawPwPrompt("Decrypt", "password for that msg");
        }
        return;
    }

    // ----- CHAT -----
    processLoRaIncoming();

    if (M5Cardputer.Keyboard.isChange() && M5Cardputer.Keyboard.isPressed()) {
        Keyboard_Class::KeysState ks = M5Cardputer.Keyboard.keysState();
        for (auto c : ks.word) if (inputBuffer.length() < 200) inputBuffer += c;
        if (ks.del && inputBuffer.length() > 0) inputBuffer.remove(inputBuffer.length() - 1);
        if (ks.enter && inputBuffer.length() > 0) {
            if (inputBuffer.startsWith("/")) {
                handleCommand(inputBuffer);
                inputBuffer = "";
            } else if (secureMode) {
                pendingEncryptText = inputBuffer;
                inputBuffer = "";
                pwBuffer = "";
                state = STATE_ENC_PROMPT;
                drawPwPrompt("Encrypt", "password for this msg");
                return;
            } else {
                sendPlainMessage(inputBuffer);
                inputBuffer = "";
            }
        }
        drawChat();
    }

    static uint32_t lastDraw = 0;
    if (millis() - lastDraw > 120) {
        drawChat();
        lastDraw = millis();
    }
}
