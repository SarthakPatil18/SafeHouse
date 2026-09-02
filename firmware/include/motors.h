#pragma once

#include <Arduino.h>
#include "config.h"

// -----------------------------------------------------------------------------
// Differential Drive & Motor Control Primitives
// -----------------------------------------------------------------------------

void initMotors();
void moveForward(int speed = 200);
void moveBackward(int speed = 200);
void turnLeft(int speed = 180);
void turnRight(int speed = 180);
void stopMotors();
void setMotorSpeeds(int leftSpeed, int rightSpeed);

/**
 * Generic Servo Position Control (0 - 180 degrees).
 * NOTE: [TODO/PLACEHOLDER]: Servo function is TBD per Section 2 of FIRMWARE_AGENTS.md
 * (sensor pan vs steering mechanism).
 */
void setServoPosition(int angle);
