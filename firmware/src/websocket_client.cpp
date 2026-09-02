#include "websocket_client.h"

#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>

// Internal state management
static WebSocketsClient webSocket;
static bool wsConnected = false;
static CommandHandler inboundCommandHandler = nullptr;
static bool wsInitialized = false;

// Non-blocking Wi-Fi reconnect state machine with exponential backoff
static unsigned long lastWiFiAttempt = 0;
static const unsigned long WIFI_INITIAL_BACKOFF_MS = 2000;   // 2s initial retry interval
static const unsigned long WIFI_MAX_BACKOFF_MS = 30000;      // 30s maximum backoff interval
static unsigned long wifiBackoffInterval = WIFI_INITIAL_BACKOFF_MS;
static bool wifiConnecting = false;

// -----------------------------------------------------------------------------
// Internal WebSocket Event Handlers
// -----------------------------------------------------------------------------

static void onConnect() {
    wsConnected = true;
    Serial.printf("[WS] Connected to backend at ws://%s:%d%s\n",
                  BACKEND_HOST, BACKEND_PORT, BACKEND_WS_PATH);
}

static void onDisconnect() {
    wsConnected = false;
    Serial.printf("[WS] Disconnected from backend ws://%s:%d\n",
                  BACKEND_HOST, BACKEND_PORT);
}

static void onMessage(uint8_t* payload, size_t length) {
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, payload, length);

    if (error) {
        Serial.printf("[WS] JSON Deserialization error: %s\n", error.c_str());
        return;
    }

    const char* intent = doc["intent"] | "";
    const char* roomId = doc["room_id"] | "";
    const char* priority = doc["priority"] | "normal";

    if (strlen(intent) > 0) {
        Serial.printf("[WS] Inbound command received: intent='%s', room_id='%s', priority='%s'\n",
                      intent, roomId, priority);

        if (inboundCommandHandler != nullptr) {
            Command cmd;
            strncpy(cmd.intent, intent, sizeof(cmd.intent) - 1);
            cmd.intent[sizeof(cmd.intent) - 1] = '\0';

            strncpy(cmd.room_id, roomId, sizeof(cmd.room_id) - 1);
            cmd.room_id[sizeof(cmd.room_id) - 1] = '\0';

            strncpy(cmd.priority, priority, sizeof(cmd.priority) - 1);
            cmd.priority[sizeof(cmd.priority) - 1] = '\0';

            // Hand off parsed command to registered handler
            inboundCommandHandler(cmd);
        }
    }
}

static void webSocketEvent(WStype_t type, uint8_t* payload, size_t length) {
    switch (type) {
        case WStype_CONNECTED:
            onConnect();
            break;

        case WStype_DISCONNECTED:
            onDisconnect();
            break;

        case WStype_TEXT:
            onMessage(payload, length);
            break;

        case WStype_BIN:
            Serial.println("[WS] Binary payload received (ignored).");
            break;

        case WStype_ERROR:
            Serial.printf("[WS] Error event received: %s\n", payload ? (const char*)payload : "unknown");
            break;

        default:
            break;
    }
}

// -----------------------------------------------------------------------------
// Non-blocking Wi-Fi Connection & Reconnect with Exponential Backoff
// -----------------------------------------------------------------------------
static void updateWiFi() {
    unsigned long now = millis();

    if (WiFi.status() != WL_CONNECTED) {
        // Mark WS as disconnected if Wi-Fi dropped
        wsConnected = false;

        // Non-blocking retry with exponential backoff
        if (!wifiConnecting || (now - lastWiFiAttempt >= wifiBackoffInterval)) {
            lastWiFiAttempt = now;
            wifiConnecting = true;

            Serial.printf("[WiFi] Attempting connection to '%s' (backoff interval: %lums)...\n",
                          WIFI_SSID, wifiBackoffInterval);

            WiFi.disconnect();
            WiFi.mode(WIFI_STA);
            WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

            // Double the backoff interval up to the maximum cap
            wifiBackoffInterval = wifiBackoffInterval * 2;
            if (wifiBackoffInterval > WIFI_MAX_BACKOFF_MS) {
                wifiBackoffInterval = WIFI_MAX_BACKOFF_MS;
            }
        }
    } else {
        // Wi-Fi is connected
        if (wifiConnecting) {
            wifiConnecting = false;
            wifiBackoffInterval = WIFI_INITIAL_BACKOFF_MS; // Reset backoff upon successful connection
            Serial.print("[WiFi] Connected successfully! IP address: ");
            Serial.println(WiFi.localIP());
        }

        // Initialize or configure WebSocket client if not yet running
        if (!wsInitialized) {
            char wsUrlPath[128];
            // Include auth token as query parameter: /ws/device/{device_id}?token={DEVICE_TOKEN}
            snprintf(wsUrlPath, sizeof(wsUrlPath), "%s?token=%s", BACKEND_WS_PATH, DEVICE_TOKEN);

            // Configure WebSocket client
            webSocket.begin(BACKEND_HOST, BACKEND_PORT, wsUrlPath);
            // Send auth token via custom header per Section 4 auth contract
            webSocket.setExtraHeaders("X-Device-Token: " DEVICE_TOKEN "\r\n");
            webSocket.onEvent(webSocketEvent);

            // Automatic reconnection interval and ping/pong heartbeat
            webSocket.setReconnectInterval(3000);        // 3s reconnect retry on socket drop
            webSocket.enableHeartbeat(15000, 3000, 2);  // Ping every 15s, 3s pong timeout, 2 failed retries

            wsInitialized = true;
            Serial.printf("[WS] WebSocket client initialized for %s\n", wsUrlPath);
        }
    }
}

// -----------------------------------------------------------------------------
// Lifecycle & State API
// -----------------------------------------------------------------------------
void initWebSocket() {
    Serial.println("[WS] Initializing Wi-Fi & WebSocket client subsystem...");
    wifiBackoffInterval = WIFI_INITIAL_BACKOFF_MS;
    wifiConnecting = false;
    lastWiFiAttempt = 0;
    wsInitialized = false;
    wsConnected = false;

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    lastWiFiAttempt = millis();
    wifiConnecting = true;
}

void updateWebSocket() {
    updateWiFi();

    // Only process WebSocket loop if Wi-Fi is active and client initialized
    if (WiFi.status() == WL_CONNECTED && wsInitialized) {
        webSocket.loop();
    }
}

bool isWiFiConnected() {
    return WiFi.status() == WL_CONNECTED;
}

bool isWebSocketConnected() {
    return wsConnected;
}

void setCommandHandler(CommandHandler handler) {
    inboundCommandHandler = handler;
}

// -----------------------------------------------------------------------------
// Outgoing Message Dispatchers (Section 4 Contracts)
// -----------------------------------------------------------------------------

/**
 * Send sensor reading to backend matching Section 4 contract:
 * {
 *   "device_id": "rover_01",
 *   "room_id": "room_2",
 *   "pir_motion": true,
 *   "gas_mq135": 42.5,
 *   "gas_mq2": 18.0,
 *   "ultrasonic_distance_cm": 34.2,
 *   "battery": 91.0
 * }
 */
bool send_reading(const SensorReading& reading, const char* room_id) {
    if (!wsConnected) {
        return false;
    }

    JsonDocument doc;
    doc["device_id"] = DEVICE_ID;
    doc["room_id"] = (room_id && strlen(room_id) > 0) ? room_id : "room_1";
    doc["pir_motion"] = reading.pir_motion;
    doc["gas_mq135"] = reading.gas_mq135;
    doc["gas_mq2"] = reading.gas_mq2;
    doc["ultrasonic_distance_cm"] = reading.ultrasonic_distance_cm;
    doc["battery"] = reading.battery;

    String jsonString;
    serializeJson(doc, jsonString);
    return webSocket.sendTXT(jsonString);
}

/**
 * Send state/event update matching Section 4 contract:
 * { "type": "event", "device_id": "rover_01", "event_type": "ROOM_REACHED", "room_id": "room_2" }
 */
bool send_event(const char* event_type, const char* room_id) {
    if (!wsConnected) {
        return false;
    }

    JsonDocument doc;
    doc["type"] = "event";
    doc["device_id"] = DEVICE_ID;
    doc["event_type"] = event_type;
    if (room_id != nullptr && strlen(room_id) > 0) {
        doc["room_id"] = room_id;
    }

    String jsonString;
    serializeJson(doc, jsonString);
    return webSocket.sendTXT(jsonString);
}
