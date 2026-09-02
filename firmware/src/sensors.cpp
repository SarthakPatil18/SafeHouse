#include "sensors.h"
#include "websocket_client.h"

// -----------------------------------------------------------------------------
// Sensor Hardware Initialization
// -----------------------------------------------------------------------------
void initSensors() {
    Serial.println("[Sensors] Initializing environmental & ultrasonic sensors...");

    // PIR Motion Digital Input
    pinMode(PIN_PIR_MOTION, INPUT);

    // HC-SR04 Ultrasonic Trigger & Echo
    pinMode(PIN_ULTRASONIC_TRIG, OUTPUT);
    pinMode(PIN_ULTRASONIC_ECHO, INPUT);
    digitalWrite(PIN_ULTRASONIC_TRIG, LOW);

    // Configure ESP32 ADC resolution (12-bit: 0 - 4095)
    analogReadResolution(12);

    Serial.println("[Sensors] Hardware sensors configured.");
}

// -----------------------------------------------------------------------------
// Individual Sensor Read Functions
// -----------------------------------------------------------------------------

/**
 * Read PIR Digital Motion Sensor.
 * Returns true if motion is detected (HIGH), false otherwise.
 */
bool readPIR() {
    int val = digitalRead(PIN_PIR_MOTION);
    return (val == HIGH);
}

/**
 * Read MQ135 Air Quality / Hazardous Gas Sensor.
 * Returns estimated ppm level (0.0 - 500.0 ppm range).
 * Sanity bounds: Analog readings stuck at 0 or 4095 indicate disconnected/shorted sensor.
 */
float readMQ135(bool* errorOut) {
    int rawAdc = analogRead(PIN_MQ135_ANALOG);

    // Sanity check bounds: 0 (disconnected/grounded) or 4095 (rail short)
    bool isError = (rawAdc <= 0 || rawAdc >= 4095);
    if (isError) {
        Serial.printf("[Sensors] WARNING: MQ135 raw ADC out of bounds (%d). Sensor error suspected.\n", rawAdc);
    }
    if (errorOut != nullptr) {
        *errorOut = isError;
    }

    // Convert raw 12-bit ADC (0 - 4095) to estimated ppm (0.0 - 250.0 ppm nominal scale)
    float ppm = (static_cast<float>(rawAdc) / 4095.0f) * 250.0f;
    return ppm;
}

/**
 * Read MQ2 Combustible Gas & Smoke Sensor.
 * Returns estimated ppm level (0.0 - 500.0 ppm range).
 * Sanity bounds: Analog readings stuck at 0 or 4095 indicate disconnected/shorted sensor.
 */
float readMQ2(bool* errorOut) {
    int rawAdc = analogRead(PIN_MQ2_ANALOG);

    // Sanity check bounds: 0 (disconnected/grounded) or 4095 (rail short)
    bool isError = (rawAdc <= 0 || rawAdc >= 4095);
    if (isError) {
        Serial.printf("[Sensors] WARNING: MQ2 raw ADC out of bounds (%d). Sensor error suspected.\n", rawAdc);
    }
    if (errorOut != nullptr) {
        *errorOut = isError;
    }

    // Convert raw 12-bit ADC (0 - 4095) to estimated ppm (0.0 - 300.0 ppm nominal scale)
    float ppm = (static_cast<float>(rawAdc) / 4095.0f) * 300.0f;
    return ppm;
}

/**
 * Read HC-SR04 Ultrasonic Distance Sensor.
 * Sends a 10µs HIGH trigger pulse and measures the echo pulse duration in microseconds.
 * Returns distance in centimeters (cm).
 */
float readUltrasonicDistanceCm() {
    // Ensure clean LOW pulse before triggering
    digitalWrite(PIN_ULTRASONIC_TRIG, LOW);
    delayMicroseconds(2);

    // Send 10µs trigger pulse
    digitalWrite(PIN_ULTRASONIC_TRIG, HIGH);
    delayMicroseconds(10);
    digitalWrite(PIN_ULTRASONIC_TRIG, LOW);

    // Read echo pulse with 30,000µs (30ms) timeout (~500cm max range)
    unsigned long durationUs = pulseIn(PIN_ULTRASONIC_ECHO, HIGH, 30000);

    // If timeout or 0, object is either out of range or sensor is disconnected
    if (durationUs == 0) {
        return 400.0f;  // Return safe max distance (400cm)
    }

    // Sound speed = 343 m/s = 0.0343 cm/µs. Distance = (duration * 0.0343) / 2
    float distanceCm = (static_cast<float>(durationUs) * 0.0343f) / 2.0f;
    return distanceCm;
}

/**
 * Read Battery Percentage via ADC Voltage Divider.
 * NOTE: [TODO/PLACEHOLDER]: Resistor divider calibration values (e.g. 10k/10k for 2S Li-ion battery).
 * Returns percentage (0.0% - 100.0%).
 */
float readBatteryPercent() {
    int rawAdc = analogRead(PIN_BATTERY_ADC);

    // [TODO/PLACEHOLDER]: If battery voltage divider circuit is unpopulated or reading near 0, default to nominal 95%
    if (rawAdc <= 10) {
        return 95.0f;
    }

    // 2S Li-ion battery range: ~6.4V (empty) to ~8.4V (full)
    // ADC reference: 3.3V with 1:2 divider (max measured 6.6V - 8.4V requires ~1:3 divider)
    float measuredVoltage = (static_cast<float>(rawAdc) / 4095.0f) * 3.3f * 2.8f;  // Approx divider multiplier
    float percent = ((measuredVoltage - 6.4f) / (8.4f - 6.4f)) * 100.0f;

    if (percent > 100.0f) percent = 100.0f;
    if (percent < 0.0f) percent = 0.0f;

    return percent;
}

// -----------------------------------------------------------------------------
// Unified Sensor Package & Sanity Checking
// -----------------------------------------------------------------------------

/**
 * Read all environmental and ultrasonic sensors into a single SensorReading package.
 * Performs basic sanity checks per Section 8 of FIRMWARE_AGENTS.md:
 * - Stuck analog readings (0 or 4095) or ultrasonic timeouts are reported as SENSOR_ERROR.
 */
SensorReading readAllSensors(bool* errorOut) {
    SensorReading reading;
    bool mq135Err = false;
    bool mq2Err = false;

    reading.pir_motion = readPIR();
    reading.gas_mq135 = readMQ135(&mq135Err);
    reading.gas_mq2 = readMQ2(&mq2Err);
    reading.ultrasonic_distance_cm = readUltrasonicDistanceCm();
    reading.battery = readBatteryPercent();

    bool hasError = mq135Err || mq2Err;
    reading.has_sensor_error = hasError;

    // Report SENSOR_ERROR event if sensor hardware is suspect (Section 8: report, don't silently drop)
    if (hasError) {
        send_event("SENSOR_ERROR");
    }

    if (errorOut != nullptr) {
        *errorOut = hasError;
    }

    return reading;
}
