#include "state_machine.h"
#include "motors.h"
#include "navigation.h"
#include "sensors.h"
#include "websocket_client.h"

static RobotDeviceState currentState = RobotDeviceState::IDLE;

// -----------------------------------------------------------------------------
// State String Conversion Helper
// -----------------------------------------------------------------------------
const char* getStateString(RobotDeviceState state) {
    switch (state) {
        case RobotDeviceState::IDLE:           return "IDLE";
        case RobotDeviceState::MOVING:         return "MOVING";
        case RobotDeviceState::SENSING:        return "SENSING";
        case RobotDeviceState::RETURNING_HOME: return "RETURNING_HOME";
        case RobotDeviceState::OBSTACLE:       return "OBSTACLE";
        case RobotDeviceState::LOW_BATTERY:    return "LOW_BATTERY";
        case RobotDeviceState::ERROR:          return "ERROR";
        default:                               return "UNKNOWN";
    }
}

// -----------------------------------------------------------------------------
// State Transitions
// -----------------------------------------------------------------------------
void transitionToState(RobotDeviceState newState) {
    if (currentState != newState) {
        RobotDeviceState oldState = currentState;
        currentState = newState;

        Serial.printf("[StateMachine] State changed: %s -> %s\n",
                      getStateString(oldState), getStateString(newState));
    }
}

RobotDeviceState getCurrentState() {
    return currentState;
}

// -----------------------------------------------------------------------------
// Initialization
// -----------------------------------------------------------------------------
void initStateMachine() {
    Serial.println("[StateMachine] Initializing robot state machine...");
    currentState = RobotDeviceState::IDLE;
}

// -----------------------------------------------------------------------------
// Priority Stack Command Execution (Section 5 of FIRMWARE_AGENTS.md)
// Priority: EMERGENCY_STOP/STOP_ROVER > Obstacle > Inbound Command > Current Movement
// -----------------------------------------------------------------------------
void execute_command(const Command& cmd) {
    Serial.printf("[StateMachine] Evaluating command: intent='%s', room_id='%s'\n",
                  cmd.intent, cmd.room_id);

    // -------------------------------------------------------------------------
    // Priority 1: STOP_ROVER / EMERGENCY_STOP
    // Always preempts immediately regardless of current state or action.
    // -------------------------------------------------------------------------
    if (strcmp(cmd.intent, "STOP_ROVER") == 0 || strcmp(cmd.intent, "EMERGENCY_STOP") == 0) {
        Serial.println("[StateMachine] EMERGENCY / STOP_ROVER executed. Halting all motion.");
        stopMotors();
        cancelNavigation();
        transitionToState(RobotDeviceState::IDLE);
        return;
    }

    // -------------------------------------------------------------------------
    // Priority 2: Obstacle Active Rejection
    // Reject any movement or navigation command if an unresolved obstacle exists.
    // -------------------------------------------------------------------------
    if (currentState == RobotDeviceState::OBSTACLE || isObstacleBlocked()) {
        Serial.printf("[StateMachine] REJECTED: Cannot execute '%s' while obstacle is active.\n", cmd.intent);
        return;
    }

    // -------------------------------------------------------------------------
    // Priority 3: Low Battery Restrictions
    // Allow only RETURN_HOME when in LOW_BATTERY state.
    // -------------------------------------------------------------------------
    if (currentState == RobotDeviceState::LOW_BATTERY) {
        if (strcmp(cmd.intent, "RETURN_HOME") != 0) {
            Serial.printf("[StateMachine] REJECTED: Low battery active. Only RETURN_HOME permitted.\n");
            send_event("LOW_BATTERY", getCurrentRoom());
            return;
        }
    }

    // -------------------------------------------------------------------------
    // Priority 4: Command Execution & State Mapping
    // -------------------------------------------------------------------------
    if (strcmp(cmd.intent, "GO_TO_ROOM") == 0) {
        if (strlen(cmd.room_id) > 0) {
            if (startNavigationToRoom(cmd.room_id)) {
                transitionToState(RobotDeviceState::MOVING);
            } else {
                transitionToState(RobotDeviceState::ERROR);
            }
        }
    } else if (strcmp(cmd.intent, "RETURN_HOME") == 0) {
        if (startReturnHome()) {
            transitionToState(RobotDeviceState::RETURNING_HOME);
        } else {
            transitionToState(RobotDeviceState::ERROR);
        }
    } else if (strcmp(cmd.intent, "MOVE_FORWARD") == 0) {
        cancelNavigation();
        moveForward(200);
        transitionToState(RobotDeviceState::MOVING);
        send_event("MOTOR_STARTED", getCurrentRoom());
    } else if (strcmp(cmd.intent, "MOVE_BACKWARD") == 0) {
        cancelNavigation();
        moveBackward(200);
        transitionToState(RobotDeviceState::MOVING);
        send_event("MOTOR_STARTED", getCurrentRoom());
    } else if (strcmp(cmd.intent, "TURN_LEFT") == 0) {
        cancelNavigation();
        turnLeft(180);
        transitionToState(RobotDeviceState::MOVING);
        send_event("MOTOR_STARTED", getCurrentRoom());
    } else if (strcmp(cmd.intent, "TURN_RIGHT") == 0) {
        cancelNavigation();
        turnRight(180);
        transitionToState(RobotDeviceState::MOVING);
        send_event("MOTOR_STARTED", getCurrentRoom());
    } else {
        Serial.printf("[StateMachine] WARNING: Unhandled or unsupported command intent '%s'.\n", cmd.intent);
    }
}

// -----------------------------------------------------------------------------
// State Machine Periodic Update Loop
// -----------------------------------------------------------------------------
void updateStateMachine() {
    // 1. Sync Obstacle Detection State
    if (isObstacleBlocked()) {
        if (currentState != RobotDeviceState::OBSTACLE) {
            transitionToState(RobotDeviceState::OBSTACLE);
        }
    } else if (currentState == RobotDeviceState::OBSTACLE && !isObstacleBlocked()) {
        // Obstacle cleared -> Return to IDLE
        transitionToState(RobotDeviceState::IDLE);
    }

    // 2. Sync Navigation Arrival & Sensing States
    if (currentState == RobotDeviceState::MOVING || currentState == RobotDeviceState::RETURNING_HOME) {
        NavStatus navStatus = getNavigationStatus();
        if (navStatus == NavStatus::ARRIVED) {
            // Once rover reaches target room, transition to SENSING mode
            if (strcmp(getCurrentRoom(), "home") == 0) {
                transitionToState(RobotDeviceState::IDLE);
            } else {
                transitionToState(RobotDeviceState::SENSING);
            }
        } else if (navStatus == NavStatus::ERROR) {
            transitionToState(RobotDeviceState::ERROR);
        }
    }

    // 3. Monitor Low Battery Threshold
    float batteryPct = readBatteryPercent();
    if (batteryPct < LOW_BATTERY_THRESHOLD_PERCENT && currentState != RobotDeviceState::LOW_BATTERY) {
        Serial.printf("[StateMachine] WARNING: Battery low (%.1f%% < %.1f%%).\n",
                      batteryPct, LOW_BATTERY_THRESHOLD_PERCENT);
        transitionToState(RobotDeviceState::LOW_BATTERY);
        send_event("LOW_BATTERY", getCurrentRoom());
    }
}
