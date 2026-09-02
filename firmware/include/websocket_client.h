#pragma once

#include <Arduino.h>
#include "config.h"
#include "sensors.h"

/**
 * Inbound command struct parsed from backend JSON payload:
 * { "intent": "GO_TO_ROOM", "room_id": "room_2", "priority": "normal" }
 */
struct Command {
    char intent[32];
    char room_id[32];
    char priority[16];
};

// Callback signature for handing off parsed inbound commands
typedef void (*CommandHandler)(const Command& cmd);

// Lifecycle & connectivity
void initWebSocket();
void updateWebSocket();
bool isWiFiConnected();
bool isWebSocketConnected();

// Outgoing message dispatchers matching Section 4 contracts
bool send_reading(const SensorReading& reading, const char* room_id = nullptr);
bool send_event(const char* event_type, const char* room_id = nullptr);

// Callback registration
void setCommandHandler(CommandHandler handler);
