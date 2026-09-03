#include "storage.h"

#include <SPI.h>
#include <SD.h>
#include <FS.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>

#include "websocket_client.h"

/**
 * ============================================================================
 * SafeRoom ESP32 Rover - MicroSD Storage & Store-and-Forward Implementation
 * ============================================================================
 * Local Storage Format: JSON-Lines (/buffer/telemetry.jsonl)
 * Each line is an independent JSON object matching AGENTS.md Section 5 / 5b:
 * {"device_id":"rover_01","room_id":"room_1","pir_motion":false,"gas_mq135":32.5,"gas_mq2":18.0,"ultrasonic_distance_cm":120.0,"battery":92.0,"timestamp":"2026-09-03T08:45:00Z"}
 */

static const char* BUFFER_FILE = "/buffer/telemetry.jsonl";
static const char* BUFFER_TEMP = "/buffer/temp.jsonl";
static const char* BUFFER_DIR  = "/buffer";

static bool sdAvailable = false;
static bool syncActive = false;
static unsigned long lastSyncChunkTime = 0;
static size_t unsyncedCount = 0;

// -----------------------------------------------------------------------------
// Storage Initialization & SD Card Mount
// -----------------------------------------------------------------------------
bool initStorage() {
    Serial.printf("[Storage] Initializing MicroSD card on SPI CS pin %d...\n", PIN_SD_CS);

    pinMode(PIN_SD_CS, OUTPUT);
    digitalWrite(PIN_SD_CS, HIGH);

    if (!SD.begin(PIN_SD_CS)) {
        Serial.println("[Storage] WARNING: MicroSD card mount failed or card not present.");
        Serial.println("[Storage] Continuing rover operation in live-only mode (No offline buffering).");
        sdAvailable = false;
        return false;
    }

    uint8_t cardType = SD.cardType();
    if (cardType == CARD_NONE) {
        Serial.println("[Storage] WARNING: No SD card attached.");
        sdAvailable = false;
        return false;
    }

    sdAvailable = true;
    uint64_t cardSize = SD.cardSize() / (1024 * 1024);
    Serial.printf("[Storage] MicroSD Card mounted successfully. Total Size: %llu MB\n", cardSize);

    // Ensure /buffer directory exists
    if (!SD.exists(BUFFER_DIR)) {
        SD.mkdir(BUFFER_DIR);
    }

    return true;
}

bool isStorageAvailable() {
    return sdAvailable;
}

size_t getUnsyncedCount() {
    return unsyncedCount;
}

// -----------------------------------------------------------------------------
// Append Sensor Reading to Local JSON-Lines Buffer File
// -----------------------------------------------------------------------------
void logReadingToSD(const SensorReading& reading, const char* room_id) {
    if (!sdAvailable) {
        return;
    }

    File file = SD.open(BUFFER_FILE, FILE_APPEND);
    if (!file) {
        Serial.println("[Storage] Error opening buffer file for append.");
        return;
    }

    // Generate ISO8601-like timestamp string
    char timeStr[32];
    snprintf(timeStr, sizeof(timeStr), "2026-09-03T%02lu:%02lu:%02luZ",
             (millis() / 3600000) % 24,
             (millis() / 60000) % 60,
             (millis() / 1000) % 60);

    // Format single-line JSON record matching backend Section 5b schema
    JsonDocument doc;
    doc["device_id"] = DEVICE_ID;
    doc["room_id"] = (room_id && strlen(room_id) > 0) ? room_id : "room_1";
    doc["pir_motion"] = reading.pir_motion;
    doc["gas_mq135"] = reading.gas_mq135;
    doc["gas_mq2"] = reading.gas_mq2;
    doc["ultrasonic_distance_cm"] = reading.ultrasonic_distance_cm;
    doc["battery"] = reading.battery;
    doc["timestamp"] = timeStr;

    serializeJson(doc, file);
    file.println(); // newline delimiter for JSON-lines format
    file.close();

    unsyncedCount++;
}

// -----------------------------------------------------------------------------
// Trigger Non-Blocking Store-and-Forward Sync Routine
// -----------------------------------------------------------------------------
void triggerStorageSync() {
    if (!sdAvailable) {
        // SD card failed on boot -> report SENSOR_ERROR over active WebSocket
        send_event("SENSOR_ERROR", "SD_CARD_UNAVAILABLE");
        return;
    }

    if (SD.exists(BUFFER_FILE)) {
        File file = SD.open(BUFFER_FILE, FILE_READ);
        if (file && file.size() > 0) {
            file.close();
            syncActive = true;
            lastSyncChunkTime = 0; // trigger immediate first chunk
            Serial.println("[Storage] Unsynced offline buffer detected. Initiating chunked sync...");
        } else if (file) {
            file.close();
        }
    }
}

// -----------------------------------------------------------------------------
// Non-Blocking Sync Worker (Called in main.cpp loop())
// -----------------------------------------------------------------------------
void updateStorageSync() {
    // 1. Guard conditions: only run if sync active, SD available, and Wi-Fi online
    if (!syncActive || !sdAvailable || !isWiFiConnected()) {
        return;
    }

    // 2. Non-blocking rate limiter (SD_SYNC_INTERVAL_MS = 500ms between chunks)
    unsigned long now = millis();
    if (now - lastSyncChunkTime < SD_SYNC_INTERVAL_MS) {
        return;
    }
    lastSyncChunkTime = now;

    if (!SD.exists(BUFFER_FILE)) {
        syncActive = false;
        return;
    }

    File sourceFile = SD.open(BUFFER_FILE, FILE_READ);
    if (!sourceFile || sourceFile.size() == 0) {
        if (sourceFile) sourceFile.close();
        syncActive = false;
        unsyncedCount = 0;
        return;
    }

    // 3. Read up to SD_SYNC_BATCH_SIZE (10) entries from buffer
    JsonDocument payloadDoc;
    JsonArray batchArray = payloadDoc.to<JsonArray>();
    size_t batchCount = 0;

    while (sourceFile.available() && batchCount < SD_SYNC_BATCH_SIZE) {
        String line = sourceFile.readStringUntil('\n');
        line.trim();
        if (line.length() == 0) continue;

        JsonDocument itemDoc;
        DeserializationError err = deserializeJson(itemDoc, line);
        if (!err) {
            batchArray.add(itemDoc.as<JsonObject>());
            batchCount++;
        }
    }

    if (batchCount == 0) {
        sourceFile.close();
        SD.remove(BUFFER_FILE);
        syncActive = false;
        unsyncedCount = 0;
        Serial.println("[Storage] Offline buffer empty. Sync complete.");
        return;
    }

    // 4. Serialize chunk to JSON payload
    String requestBody;
    serializeJson(batchArray, requestBody);

    // 5. Send HTTP POST to /api/sensors/sync
    //    Use HTTPS (WiFiClientSecure) if BACKEND_PORT is 443 (Render cloud).
    //    Use plain WiFiClient only for local testing on port 8000.
    String syncUrl;
#if BACKEND_PORT == 443
    WiFiClientSecure secureClient;
    secureClient.setInsecure();  // Accept Render's TLS cert without local CA store
    syncUrl = "https://";
    syncUrl += BACKEND_HOST;
    syncUrl += BACKEND_SYNC_PATH;
    HTTPClient http;
    http.begin(secureClient, syncUrl);
#else
    WiFiClient client;
    syncUrl = "http://";
    syncUrl += BACKEND_HOST;
    syncUrl += ":";
    syncUrl += BACKEND_PORT;
    syncUrl += BACKEND_SYNC_PATH;
    HTTPClient http;
    http.begin(client, syncUrl);
#endif
    http.addHeader("Content-Type", "application/json");
    if (strlen(DEVICE_TOKEN) > 0) {
        http.addHeader("X-Device-Token", DEVICE_TOKEN);
    }
    http.setTimeout(5000); // 5s timeout for HTTPS

    int httpCode = http.POST(requestBody);
    bool syncSuccess = false;

    if (httpCode == 200) {
        String responseText = http.getString();
        JsonDocument resDoc;
        DeserializationError resErr = deserializeJson(resDoc, responseText);
        if (!resErr && resDoc["success"] == true) {
            syncSuccess = true;
            size_t syncedCount = resDoc["data"]["synced_count"] | batchCount;
            Serial.printf("[Storage] Synced batch of %u offline readings to backend.\n", syncedCount);
        }
    } else {
        Serial.printf("[Storage] Sync POST failed (HTTP %d). Backing off...\n", httpCode);
    }

    http.end();

    // 6. If sync confirmed by backend, prune the sent records from the buffer
    if (syncSuccess) {
        File tempFile = SD.open(BUFFER_TEMP, FILE_WRITE);
        if (tempFile) {
            // Copy all remaining unread lines from sourceFile to tempFile
            while (sourceFile.available()) {
                String line = sourceFile.readStringUntil('\n');
                line.trim();
                if (line.length() > 0) {
                    tempFile.println(line);
                }
            }
            tempFile.close();
            sourceFile.close();

            SD.remove(BUFFER_FILE);
            SD.rename(BUFFER_TEMP, BUFFER_FILE);

            // Check if more unsynced lines remain
            File checkFile = SD.open(BUFFER_FILE, FILE_READ);
            if (!checkFile || checkFile.size() == 0) {
                if (checkFile) checkFile.close();
                SD.remove(BUFFER_FILE);
                syncActive = false;
                unsyncedCount = 0;
                Serial.println("[Storage] All offline records synced successfully.");
            } else {
                checkFile.close();
            }
        } else {
            sourceFile.close();
        }
    } else {
        sourceFile.close();
    }
}
