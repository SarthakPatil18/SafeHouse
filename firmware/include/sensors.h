#pragma once

#include <Arduino.h>
#include "config.h"

/**
 * SensorReading struct matching Section 4 JSON contract exactly:
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
struct SensorReading {
    bool pir_motion;
    float gas_mq135;
    float gas_mq2;
    float ultrasonic_distance_cm;
    float battery;
    bool has_sensor_error;
};

// Aliased to SensorData for backward compatibility across modules
typedef SensorReading SensorData;

// Function prototypes
void initSensors();
bool readPIR();
float readMQ135(bool* errorOut = nullptr);
float readMQ2(bool* errorOut = nullptr);
float readUltrasonicDistanceCm();
float readBatteryPercent();
SensorReading readAllSensors(bool* errorOut = nullptr);
