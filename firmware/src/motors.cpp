#include "motors.h"

// -----------------------------------------------------------------------------
// Hardware Pin Initialization
// -----------------------------------------------------------------------------
void initMotors() {
    Serial.println("[Motors] Initializing differential motor driver pins...");

    pinMode(PIN_MOTOR_LEFT_IN1, OUTPUT);
    pinMode(PIN_MOTOR_LEFT_IN2, OUTPUT);
    pinMode(PIN_MOTOR_LEFT_PWM, OUTPUT);

    pinMode(PIN_MOTOR_RIGHT_IN1, OUTPUT);
    pinMode(PIN_MOTOR_RIGHT_IN2, OUTPUT);
    pinMode(PIN_MOTOR_RIGHT_PWM, OUTPUT);

    // Auxiliary Servo Pin
    pinMode(PIN_SERVO, OUTPUT);

    stopMotors();
    Serial.println("[Motors] Motor driver ready.");
}

// -----------------------------------------------------------------------------
// Core Speed & Direction Control
// -----------------------------------------------------------------------------

/**
 * Set individual left and right motor speeds with direction clamping.
 * Range: -255 (full reverse) to +255 (full forward).
 */
void setMotorSpeeds(int leftSpeed, int rightSpeed) {
    // Left Motor Direction & PWM
    if (leftSpeed > 0) {
        digitalWrite(PIN_MOTOR_LEFT_IN1, HIGH);
        digitalWrite(PIN_MOTOR_LEFT_IN2, LOW);
        analogWrite(PIN_MOTOR_LEFT_PWM, min(leftSpeed, 255));
    } else if (leftSpeed < 0) {
        digitalWrite(PIN_MOTOR_LEFT_IN1, LOW);
        digitalWrite(PIN_MOTOR_LEFT_IN2, HIGH);
        analogWrite(PIN_MOTOR_LEFT_PWM, min(-leftSpeed, 255));
    } else {
        digitalWrite(PIN_MOTOR_LEFT_IN1, LOW);
        digitalWrite(PIN_MOTOR_LEFT_IN2, LOW);
        analogWrite(PIN_MOTOR_LEFT_PWM, 0);
    }

    // Right Motor Direction & PWM
    if (rightSpeed > 0) {
        digitalWrite(PIN_MOTOR_RIGHT_IN1, HIGH);
        digitalWrite(PIN_MOTOR_RIGHT_IN2, LOW);
        analogWrite(PIN_MOTOR_RIGHT_PWM, min(rightSpeed, 255));
    } else if (rightSpeed < 0) {
        digitalWrite(PIN_MOTOR_RIGHT_IN1, LOW);
        digitalWrite(PIN_MOTOR_RIGHT_IN2, HIGH);
        analogWrite(PIN_MOTOR_RIGHT_PWM, min(-rightSpeed, 255));
    } else {
        digitalWrite(PIN_MOTOR_RIGHT_IN1, LOW);
        digitalWrite(PIN_MOTOR_RIGHT_IN2, LOW);
        analogWrite(PIN_MOTOR_RIGHT_PWM, 0);
    }
}

// -----------------------------------------------------------------------------
// Movement Primitives
// -----------------------------------------------------------------------------

void moveForward(int speed) {
    setMotorSpeeds(speed, speed);
}

void moveBackward(int speed) {
    setMotorSpeeds(-speed, -speed);
}

void turnLeft(int speed) {
    setMotorSpeeds(-speed, speed);
}

void turnRight(int speed) {
    setMotorSpeeds(speed, -speed);
}

void stopMotors() {
    setMotorSpeeds(0, 0);
}

// -----------------------------------------------------------------------------
// Auxiliary Servo Control
// -----------------------------------------------------------------------------

/**
 * Generic Servo Position (0 - 180 degrees).
 * NOTE: [TODO/PLACEHOLDER]: Real function of this servo (e.g. sensor pan vs steering)
 * will be assigned once physical assembly is verified.
 */
void setServoPosition(int angle) {
    int clampedAngle = constrain(angle, 0, 180);
    // Standard 50Hz RC servo pulse width: ~500µs (0 deg) to ~2400µs (180 deg)
    int pulseUs = map(clampedAngle, 0, 180, 500, 2400);

    // Software PWM pulse implementation for generic servo output
    digitalWrite(PIN_SERVO, HIGH);
    delayMicroseconds(pulseUs);
    digitalWrite(PIN_SERVO, LOW);
}
