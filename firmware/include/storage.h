#pragma once

#include <Arduino.h>
#include "config.h"
#include "sensors.h"

/**
 * ============================================================================
 * SafeRoom ESP32 Rover - MicroSD Storage & Offline Buffer Sync Module
 * ============================================================================
 * Per FIRMWARE_AGENTS.md Section 2 and 4a:
 * - Local storage wrapping SD read/write/append over SPI.
 * - Appends unsynced telemetry to a local JSON-lines buffer file.
 * - On WebSocket connect/reconnect, performs non-blocking chunked POST to
 *   /api/sensors/sync without blocking motor loops or obstacle detection.
 * - Graceful degradation on SD failure reporting SENSOR_ERROR without halting.
 */

// Lifecycle
bool initStorage();
bool isStorageAvailable();

// Telemetry Logging
void logReadingToSD(const SensorReading& reading, const char* room_id);

// Sync Execution (Called from WebSocket connect callback and main loop)
void triggerStorageSync();
void updateStorageSync();

// Status
size_t getUnsyncedCount();
