#pragma once

#include <Arduino.h>
#include "config.h"

// Operational status of line-following navigation
enum class NavStatus {
    IDLE,
    NAVIGATING,
    ARRIVED,
    BLOCKED,
    ERROR
};

// Turn action at line track junctions
enum TurnAction {
    ACTION_STRAIGHT,
    ACTION_LEFT,
    ACTION_RIGHT,
    ACTION_UTURN,
    ACTION_STOP
};

/**
 * Hardcoded Room Path Definition per Section 6 of FIRMWARE_AGENTS.md:
 * Defines sequence of junction count and turns from Home/Dock to the target room.
 */
struct RoomPath {
    const char* room_id;
    int junction_count;
    TurnAction turns[8];
};

// Function prototypes
void initNavigation();
void updateNavigation();
bool startNavigationToRoom(const char* roomId);
bool startReturnHome();
void cancelNavigation();
NavStatus getNavigationStatus();
const char* getCurrentRoom();
bool isObstacleBlocked();
bool isTurnInProgress();
