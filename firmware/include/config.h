#pragma once

#include <Arduino.h>

/**
 * ============================================================================
 * SafeRoom ESP32 Rover - Central Configuration & Hardware Pin Placeholders
 * ============================================================================
 * NOTE: Per Section 2 of FIRMWARE_AGENTS.md, pin assignments are defined here
 * as clearly labeled placeholders to be adjusted when physical wiring is finalized.
 * Never hardcode pin numbers inline in logic files.
 */

// -----------------------------------------------------------------------------
// 1. Device Identity & Communication Configuration
// -----------------------------------------------------------------------------
#define DEVICE_ID               "rover_01"
#define FIRMWARE_VERSION        "v1.0.0-esp32"

// Wi-Fi Network Credentials (Placeholders - edit before deployment)
#define WIFI_SSID               "SafeRoom_WiFi"
#define WIFI_PASSWORD           "SafeRoom_Password"

// Backend Host & WebSocket Configuration
#define BACKEND_HOST            "192.168.1.100"  // IP or hostname of FastAPI backend
#define BACKEND_PORT            8000             // HTTP/WS Port
#define BACKEND_WS_PATH         "/ws/device/" DEVICE_ID
#define DEVICE_TOKEN            "secret_rover_auth_token"  // Matching backend settings.DEVICE_TOKEN

// -----------------------------------------------------------------------------
// 2. Hardware Pin Assignments (Placeholders / TODO: Confirm wiring)
// -----------------------------------------------------------------------------

// Environmental & Distance Sensors
#define PIN_PIR_MOTION          13   // Digital Input: PIR motion sensor (HIGH = motion)
#define PIN_MQ135_ANALOG        34   // ADC Input: MQ135 air quality / hazardous gas (ADC1 CH6)
#define PIN_MQ2_ANALOG          35   // ADC Input: MQ2 combustible gas & smoke (ADC1 CH7)
#define PIN_ULTRASONIC_TRIG     5    // Digital Output: HC-SR04 Ultrasonic Trigger
#define PIN_ULTRASONIC_ECHO     18   // Digital Input: HC-SR04 Ultrasonic Echo
#define PIN_BATTERY_ADC         36   // ADC Input: Battery voltage divider (ADC1 CH0 / VP)

// IR Line-Following Sensor Array (Navigation only - not reported as environmental telemetry)
#define PIN_LINE_LEFT           32   // Digital/Analog Input: Far-left line sensor
#define PIN_LINE_CENTER_LEFT    33   // Digital/Analog Input: Center-left line sensor
#define PIN_LINE_CENTER_RIGHT   25   // Digital/Analog Input: Center-right line sensor
#define PIN_LINE_RIGHT          26   // Digital/Analog Input: Far-right line sensor

// DC Motor Driver (H-Bridge / TB6612FNG or L298N Differential Skid Steering)
#define PIN_MOTOR_LEFT_PWM      14   // PWM Output: Left motor speed
#define PIN_MOTOR_LEFT_IN1      27   // Digital Output: Left motor direction 1
#define PIN_MOTOR_LEFT_IN2      12   // Digital Output: Left motor direction 2

#define PIN_MOTOR_RIGHT_PWM     15   // PWM Output: Right motor speed
#define PIN_MOTOR_RIGHT_IN1     2    // Digital Output: Right motor direction 1
#define PIN_MOTOR_RIGHT_IN2     4    // Digital Output: Right motor direction 2

// Actuator Servo (Purpose TBD / Placeholder: Sensor Pan or Steering Mechanism)
#define PIN_SERVO               19   // PWM/Pulse Output: Auxiliary Servo

// Status Indicator LED
#define PIN_STATUS_LED          22   // Digital Output: Onboard status/debug LED

// -----------------------------------------------------------------------------
// 3. Operational & Local Safety Thresholds
// -----------------------------------------------------------------------------
#define OBSTACLE_DISTANCE_THRESHOLD_CM  15.0f   // Emergency halt if ultrasonic distance < 15cm
#define LOW_BATTERY_THRESHOLD_PERCENT   15.0f   // Low battery warning threshold percentage
#define TELEMETRY_INTERVAL_MS           1000    // Telemetry push rate in milliseconds (1Hz)
#define OBSTACLE_CHECK_INTERVAL_MS      50      // Fast local obstacle check rate (20Hz)
#define NAVIGATION_LOOP_INTERVAL_MS     20      // Line-following PID loop rate (50Hz)
