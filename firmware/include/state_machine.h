#pragma once

#include <Arduino.h>
#include "websocket_client.h"

/**
 * Robot device states mirrored from Section 7 of FIRMWARE_AGENTS.md:
 * IDLE, MOVING, SENSING, RETURNING_HOME, OBSTACLE, LOW_BATTERY, ERROR
 */
enum class RobotDeviceState {
    IDLE,
    MOVING,
    SENSING,
    RETURNING_HOME,
    OBSTACLE,
    LOW_BATTERY,
    ERROR
};

// Lifecycle and command execution
void initStateMachine();
void updateStateMachine();
void execute_command(const Command& cmd);
void transitionToState(RobotDeviceState newState);
RobotDeviceState getCurrentState();
const char* getStateString(RobotDeviceState state);
