#include "navigation.h"
#include "motors.h"
#include "sensors.h"
#include "websocket_client.h"

// -----------------------------------------------------------------------------
// Hardcoded Room Path Table (Section 6 of FIRMWARE_AGENTS.md)
// -----------------------------------------------------------------------------
// NOTE: [TODO/PLACEHOLDER]: Hardcoded junction count and turn sequences below
// are placeholders to be calibrated once the physical floor tape track layout is taped.
static const RoomPath ROOM_PATHS[] = {
    {
        "room_1",  // Living Room
        1,
        { ACTION_LEFT, ACTION_STOP }
    },
    {
        "room_2",  // Master Bedroom
        2,
        { ACTION_STRAIGHT, ACTION_LEFT, ACTION_STOP }
    },
    {
        "room_3",  // Guest Bedroom
        2,
        { ACTION_STRAIGHT, ACTION_RIGHT, ACTION_STOP }
    },
    {
        "room_4",  // Kitchen
        3,
        { ACTION_RIGHT, ACTION_STRAIGHT, ACTION_LEFT, ACTION_STOP }
    },
    {
        "home",    // Base / Charging Dock
        2,
        { ACTION_UTURN, ACTION_STRAIGHT, ACTION_STOP }
    }
};

static const size_t NUM_PATHS = sizeof(ROOM_PATHS) / sizeof(ROOM_PATHS[0]);

// -----------------------------------------------------------------------------
// Navigation State & Variables
// -----------------------------------------------------------------------------
static NavStatus navStatus = NavStatus::IDLE;
static char activeRoomId[32] = "room_1";
static int currentPathIndex = -1;
static int currentJunctionIndex = 0;
static unsigned long lastJunctionTime = 0;
static const unsigned long JUNCTION_DEBOUNCE_MS = 1000;

// Non-blocking turn execution state
static bool turn_in_progress = false;
static unsigned long turn_start_time = 0;
static unsigned long turn_duration = 0;

// Motor speed constants
static const int BASE_SPEED = 180;
static const int CORRECTION_OFFSET = 50;

// Timing loops
static unsigned long lastNavLoop = 0;

// -----------------------------------------------------------------------------
// Hardware Initialization
// -----------------------------------------------------------------------------
void initNavigation() {
    Serial.println("[Navigation] Initializing IR line-following sensor array...");

    pinMode(PIN_LINE_LEFT, INPUT);
    pinMode(PIN_LINE_CENTER_LEFT, INPUT);
    pinMode(PIN_LINE_CENTER_RIGHT, INPUT);
    pinMode(PIN_LINE_RIGHT, INPUT);

    navStatus = NavStatus::IDLE;
    turn_in_progress = false;
    turn_start_time = 0;
    turn_duration = 0;
    strncpy(activeRoomId, "room_1", sizeof(activeRoomId) - 1);
    Serial.println("[Navigation] Line tracking subsystem ready.");
}

// -----------------------------------------------------------------------------
// Path Matching Helper
// -----------------------------------------------------------------------------
static int findPathIndex(const char* roomId) {
    if (!roomId) return -1;
    for (size_t i = 0; i < NUM_PATHS; ++i) {
        if (strcmp(ROOM_PATHS[i].room_id, roomId) == 0) {
            return static_cast<int>(i);
        }
    }
    return -1;
}

// -----------------------------------------------------------------------------
// High-Level Navigation Commands
// -----------------------------------------------------------------------------
bool startNavigationToRoom(const char* roomId) {
    int idx = findPathIndex(roomId);
    if (idx < 0) {
        Serial.printf("[Navigation] ERROR: No stored path found for target room '%s'.\n", roomId);
        navStatus = NavStatus::ERROR;
        return false;
    }

    turn_in_progress = false;
    currentPathIndex = idx;
    currentJunctionIndex = 0;
    lastJunctionTime = millis();
    strncpy(activeRoomId, roomId, sizeof(activeRoomId) - 1);
    navStatus = NavStatus::NAVIGATING;

    send_event("MOTOR_STARTED", activeRoomId);
    Serial.printf("[Navigation] Starting path navigation to '%s' (Junctions: %d)...\n",
                  roomId, ROOM_PATHS[idx].junction_count);
    return true;
}

bool startReturnHome() {
    return startNavigationToRoom("home");
}

void cancelNavigation() {
    // Immediately clear any active turn in progress and halt motors
    turn_in_progress = false;
    stopMotors();
    navStatus = NavStatus::IDLE;
    send_event("MOTOR_STOPPED", activeRoomId);
    Serial.println("[Navigation] Navigation cancelled. Rover stopped.");
}

NavStatus getNavigationStatus() {
    return navStatus;
}

const char* getCurrentRoom() {
    return activeRoomId;
}

bool isObstacleBlocked() {
    return (navStatus == NavStatus::BLOCKED);
}

bool isTurnInProgress() {
    return turn_in_progress;
}

// -----------------------------------------------------------------------------
// Non-blocking Turn Initiation
// -----------------------------------------------------------------------------
static void startTurn(TurnAction action) {
    turn_in_progress = true;
    turn_start_time = millis();

    switch (action) {
        case ACTION_LEFT:
            Serial.println("[Navigation] Junction -> Starting non-blocking turn LEFT (400ms)");
            turnLeft(200);
            turn_duration = 400;
            break;
        case ACTION_RIGHT:
            Serial.println("[Navigation] Junction -> Starting non-blocking turn RIGHT (400ms)");
            turnRight(200);
            turn_duration = 400;
            break;
        case ACTION_UTURN:
            Serial.println("[Navigation] Junction -> Starting non-blocking U-TURN (850ms)");
            turnLeft(220);
            turn_duration = 850;
            break;
        case ACTION_STRAIGHT:
        default:
            Serial.println("[Navigation] Junction -> Continuing STRAIGHT (200ms)");
            moveForward(BASE_SPEED);
            turn_duration = 200;
            break;
    }
}

// -----------------------------------------------------------------------------
// Main Non-blocking Navigation Loop
// -----------------------------------------------------------------------------
void updateNavigation() {
    unsigned long now = millis();
    if (now - lastNavLoop < NAVIGATION_LOOP_INTERVAL_MS) {
        return;
    }
    lastNavLoop = now;

    // -------------------------------------------------------------------------
    // CRITICAL SAFETY CHECK (Section 5 of FIRMWARE_AGENTS.md):
    // Local obstacle detection must immediately halt motors locally without
    // waiting for any backend response or network round-trip.
    // This runs on EVERY tick, even while a turn is in progress!
    // -------------------------------------------------------------------------
    float distanceCm = readUltrasonicDistanceCm();
    if (distanceCm < OBSTACLE_DISTANCE_THRESHOLD_CM) {
        if (navStatus != NavStatus::BLOCKED) {
            turn_in_progress = false;  // Immediately interrupt in-progress turn
            stopMotors();
            navStatus = NavStatus::BLOCKED;
            Serial.printf("[Safety] CRITICAL: Obstacle at %.1f cm (< %.1f cm). Local immediate halt!\n",
                          distanceCm, OBSTACLE_DISTANCE_THRESHOLD_CM);
            send_event("OBSTACLE_DETECTED", activeRoomId);
        }
        return;
    } else if (navStatus == NavStatus::BLOCKED && distanceCm >= (OBSTACLE_DISTANCE_THRESHOLD_CM + 8.0f)) {
        // Obstacle cleared with hysteresis
        Serial.printf("[Safety] Obstacle cleared (Distance: %.1f cm). Resuming navigation.\n", distanceCm);
        navStatus = NavStatus::NAVIGATING;
    }

    // Only process line following if actively navigating
    if (navStatus != NavStatus::NAVIGATING || currentPathIndex < 0) {
        return;
    }

    // -------------------------------------------------------------------------
    // Non-blocking Turn Progress Handling
    // -------------------------------------------------------------------------
    if (turn_in_progress) {
        if (now - turn_start_time >= turn_duration) {
            turn_in_progress = false;
            Serial.println("[Navigation] Non-blocking turn completed. Resuming line tracking.");
        } else {
            // Turn is still running: motor speeds were set at startTurn(),
            // yield back to loop() immediately without blocking.
            return;
        }
    }

    const RoomPath& activePath = ROOM_PATHS[currentPathIndex];

    // Read 4-channel line sensor array (HIGH = line detected, LOW = background)
    bool sLeft = (digitalRead(PIN_LINE_LEFT) == HIGH);
    bool sCenterLeft = (digitalRead(PIN_LINE_CENTER_LEFT) == HIGH);
    bool sCenterRight = (digitalRead(PIN_LINE_CENTER_RIGHT) == HIGH);
    bool sRight = (digitalRead(PIN_LINE_RIGHT) == HIGH);

    // 1. Check Junction Crossing (e.g. cross-line where 3+ sensors detect line)
    bool isJunction = (sLeft && sRight) && (sCenterLeft || sCenterRight);

    if (isJunction && (now - lastJunctionTime >= JUNCTION_DEBOUNCE_MS)) {
        lastJunctionTime = now;
        currentJunctionIndex++;

        Serial.printf("[Navigation] Crossed Junction %d of %d for room '%s'.\n",
                      currentJunctionIndex, activePath.junction_count, activePath.room_id);

        if (currentJunctionIndex >= activePath.junction_count) {
            // Target room reached!
            turn_in_progress = false;
            stopMotors();
            navStatus = NavStatus::ARRIVED;
            Serial.printf("[Navigation] SUCCESS: Arrived at '%s'!\n", activePath.room_id);
            send_event("ROOM_REACHED", activePath.room_id);
            send_event("MOTOR_STOPPED", activePath.room_id);
            return;
        } else {
            // Initiate non-blocking turn defined for this junction
            TurnAction turnToTake = activePath.turns[currentJunctionIndex - 1];
            startTurn(turnToTake);
            return;
        }
    }

    // 2. Line Tracking Proportional Differential Steering
    if (sCenterLeft && sCenterRight) {
        // Centered directly on track
        moveForward(BASE_SPEED);
    } else if (sCenterLeft && !sCenterRight) {
        // Slightly veering right -> adjust left
        setMotorSpeeds(BASE_SPEED - CORRECTION_OFFSET, BASE_SPEED + CORRECTION_OFFSET);
    } else if (!sCenterLeft && sCenterRight) {
        // Slightly veering left -> adjust right
        setMotorSpeeds(BASE_SPEED + CORRECTION_OFFSET, BASE_SPEED - CORRECTION_OFFSET);
    } else if (sLeft && !sRight) {
        // Hard left curve
        setMotorSpeeds(BASE_SPEED - (CORRECTION_OFFSET * 2), BASE_SPEED + CORRECTION_OFFSET);
    } else if (sRight && !sLeft) {
        // Hard right curve
        setMotorSpeeds(BASE_SPEED + CORRECTION_OFFSET, BASE_SPEED - (CORRECTION_OFFSET * 2));
    } else {
        // Line temporarily lost -> maintain steady crawl forward
        moveForward(BASE_SPEED - 30);
    }
}
