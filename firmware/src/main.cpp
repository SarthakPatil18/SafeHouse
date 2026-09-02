#include <Arduino.h>
#include "config.h"
#include "sensors.h"
#include "motors.h"
#include "navigation.h"
#include "websocket_client.h"
#include "state_machine.h"

// Non-blocking timer for periodic telemetry push (TELEMETRY_INTERVAL_MS in config.h)
static unsigned long lastTelemetrySend = 0;

void setup() {
    Serial.begin(115200);
    delay(500);

    Serial.println("\n==================================================");
    Serial.println(" SafeRoom Rover - ESP32 Firmware Booting ");
    Serial.printf(" Device ID: %s | Firmware: %s\n", DEVICE_ID, FIRMWARE_VERSION);
    Serial.println("==================================================");

    // 1. Initialize hardware subsystems (Sensors, Motors, Line Navigation)
    initSensors();
    initMotors();
    initNavigation();
    initStateMachine();

    // 2. Register state machine command executor callback with the WebSocket client
    // When incoming JSON commands arrive over WebSocket, onMessage parses them into
    // Command structs and passes them directly to execute_command().
    setCommandHandler(execute_command);

    // 3. Initialize Wi-Fi connection and persistent WebSocket client
    initWebSocket();

    Serial.println("[Setup] All hardware and communication subsystems ready.");
}

void loop() {
    // 1. Process WebSocket networking, Wi-Fi backoff reconnect, and inbound command queue
    updateWebSocket();

    // 2. CRITICAL LOCAL SAFETY & NAVIGATION (Prompt F4 / Section 5):
    // Always runs local obstacle checking (ultrasonic < safe threshold) every tick
    // and halts motors immediately if blocked, completely independent of backend status.
    updateNavigation();

    // 3. Process state machine transitions, battery monitoring, and room arrival
    updateStateMachine();

    // 4. Non-blocking periodic sensor telemetry push (Prompt F2 / Section 4)
    unsigned long now = millis();
    if (now - lastTelemetrySend >= TELEMETRY_INTERVAL_MS) {
        lastTelemetrySend = now;

        // Sample environmental and distance sensors
        SensorReading reading = readAllSensors();

        // Push telemetry payload matching Section 4 JSON contract
        if (isWebSocketConnected()) {
            send_reading(reading, getCurrentRoom());
        }
    }

    // Cooperative yield for ESP32 background tasks and watchdog timer
    delay(2);
}
