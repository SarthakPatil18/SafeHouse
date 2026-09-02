# SafeRoom — Firmware Agent Context

Read this fully before every task. This firmware talks to the backend defined in
AGENTS.md (backend repo) — the two must agree on every field name and message shape
below. Do not invent new fields or change the contract from this side; if something
here seems wrong or incomplete, stop and ask rather than deciding unilaterally.

## 1. What this firmware does

Runs on the ESP32 mounted on the SafeRoom rover. Responsibilities:
- Connect to Wi-Fi and hold a persistent WebSocket connection to the backend.
- Execute movement commands received from the backend (line-following navigation
  between rooms, not free navigation/SLAM).
- Read sensors (PIR, MQ135, MQ2, ultrasonic) and push readings to the backend.
- Run local obstacle-avoidance and emergency-stop logic that does NOT wait for a
  backend round-trip — safety-critical behavior must be local-first.
- Report its own state (IDLE/MOVING/SENSING/etc.) so the backend/dashboard stay in sync.

This firmware does NOT decide what an anomaly is, does NOT talk to any AI, and does NOT
make patrol-ordering decisions — all of that is backend logic (see AGENTS.md). This
firmware is a dumb-but-reliable executor: it does what it's told, reports what it senses,
and protects itself/the space it's in even if the backend connection drops.

## 2. Hardware (FINAL)

- MCU: ESP32
- Sensors: PIR (digital, motion), MQ135 (analog, air quality), MQ2 (analog, smoke/gas),
  HC-SR04 ultrasonic (trigger/echo, obstacle distance), IR line-following sensor array
  (digital, multiple channels — used for navigation, not reported to backend as sensor data)
- Actuation: 4x DC motor + motor driver (differential/skid steering), 1x servo
  (purpose TBD by whoever wires it — do not assume steering vs sensor-pan; if a task
  needs to know, ask), buck converter for power regulation
- No camera. Do not write any camera code or leave camera stubs.

Pin assignments are NOT decided in this file — the first firmware prompt will ask you to
create a single `pins.h` / `config.h` with clearly named placeholder pins that get edited
once the physical wiring is confirmed. Never hardcode pin numbers inline in logic files.

## 3. FINAL tech decisions

| Choice | Why |
|---|---|
| Arduino framework via PlatformIO (not ESP-IDF raw, not Arduino IDE) | fastest to iterate, still leaves room for real project structure |
| WebSocketsClient (Links2004/arduinoWebSockets) | persistent connection, matches backend's WebSocket-first design |
| ArduinoJson | for building/parsing the JSON payloads below |
| No RTOS task juggling beyond what Arduino's loop() + simple non-blocking timers give you | keep it debuggable under hackathon time pressure |
| Line-following navigation only | IR array follows a physical line; room arrival is detected by junction/marker counting along a hardcoded path per room, not SLAM or mapping |

## 4. Communication contract (must match backend exactly)

WebSocket URL: `ws://<backend-host>/ws/device/{device_id}`
Auth: send `DEVICE_TOKEN` (matching backend's .env value) as a header or first message
per whatever the backend's `verify_device_token` implementation expects — check the
backend repo's Prompt 20 output for the exact mechanism before assuming.

**Outgoing (firmware → backend), sensor reading:**
```json
{
  "device_id": "rover_01",
  "room_id": "room_2",
  "pir_motion": true,
  "gas_mq135": 42.5,
  "gas_mq2": 18.0,
  "ultrasonic_distance_cm": 34.2,
  "battery": 91.0
}
```
Field names must match this exactly — these are the same names as `sensor_readings` in
the backend's AGENTS.md Section 5.

**Outgoing, state/event updates (so backend can log robot_events and update dashboard):**
```json
{ "type": "event", "device_id": "rover_01", "event_type": "ROOM_REACHED", "room_id": "room_2" }
```
event_type values must be from the backend's Section 5 list: CONNECTED, DISCONNECTED,
MOTOR_STARTED, MOTOR_STOPPED, OBSTACLE_DETECTED, ROOM_REACHED, SENSOR_ERROR,
LOW_BATTERY, PATROL_STARTED, PATROL_COMPLETED. Firmware only ever sends events it's
actually responsible for (movement/sensor-related); backend generates CONNECTED/
DISCONNECTED itself on WebSocket open/close, firmware doesn't need to send those.

**Incoming (backend → firmware), command:**
```json
{ "intent": "GO_TO_ROOM", "room_id": "room_2", "priority": "normal" }
```
Only these intents are ever sent to firmware (subset of the backend's full intent list —
GET_STATUS/GET_HISTORY/GET_ALERTS/START_PATROL/STOP_PATROL orchestration stay backend-side):
```
MOVE_FORWARD, MOVE_BACKWARD, TURN_LEFT, TURN_RIGHT,
STOP_ROVER, GO_TO_ROOM, RETURN_HOME
```

## 5. Priority stack — same as backend, enforced LOCALLY too

```
EMERGENCY_STOP/STOP_ROVER > obstacle detected > any received command > current movement
```
Critical rule: obstacle avoidance and STOP_ROVER must work even if the WebSocket
connection is down. Never make safety behavior depend on a live backend connection.
If ultrasonic distance drops below a safe threshold mid-movement, stop locally
immediately, THEN report OBSTACLE_DETECTED if connected — don't wait for backend
permission to stop.

## 6. Room navigation model

Each room has a hardcoded path definition (junction count + turn sequence from home/last
known position) stored locally on the ESP32 — this is NOT sent by the backend, the
backend only ever says "go to room_2" and firmware knows how to get there via its own
stored path table. Keep this table in one clearly named file, easy to edit once the
physical track layout is finalized.

## 7. State reporting

Mirror the backend's device states where it makes sense for firmware to report them:
IDLE, MOVING, SENSING, RETURNING_HOME, OBSTACLE, LOW_BATTERY, ERROR. Firmware sends its
current state on every change so the dashboard stays live.

## 8. Non-goals

No camera. No SLAM/mapping. No onboard AI/inference. No autonomous decision-making about
what counts as an anomaly — sensor values go to the backend as-is, unprocessed, except
for basic sanity bounds (e.g. reject an obviously-invalid analog read) which should be
reported as SENSOR_ERROR, not silently dropped.

## 9. How to work

Each task is a scoped, numbered prompt. Do only what it asks. If a prompt requires a
pin number, hardware timing value, or physical path detail nobody has specified yet, use
a clearly marked placeholder/TODO and flag it explicitly in your summary — don't guess a
real-looking value that hides the fact it's unverified.
