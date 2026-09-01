# SafeRoom — Backend Agent Context

This file is the source of truth for architecture decisions. Read it before every task.
Do not silently change any decision marked FINAL below — if you think one is wrong, stop and ask instead of substituting your own choice.

## 1. What we're building

SafeRoom: a mobile rover that patrols predefined rooms/waypoints, reads environmental
sensors (temperature, humidity, sound, obstacle distance), compares readings against
per-room baselines, detects anomalies, optionally rechecks to confirm, and proactively
alerts a caregiver/staff dashboard — with natural-language voice/text control.

Core loop: PATROL → SENSE → STORE → COMPARE TO BASELINE → ANOMALY? → RECHECK → AI REASONING → ALERT
Command loop: USER TEXT/VOICE → PARSE → STRUCTURED COMMAND → VALIDATE/AUTHORIZE → ROBOT → RESULT → RESPONSE

This is the backend only. Hardware (ESP32 firmware) and frontend are separate repos/agents;
we connect to them later over documented contracts (Section 6 and 7). Don't build firmware
or frontend code from this context — build the FastAPI backend in isolation, but design every
contract as if the other two already exist.

## 2. FINAL tech stack decisions — do not swap these

| Layer | Choice | Why (don't relitigate) |
|---|---|---|
| Backend framework | FastAPI (Python) | native WebSocket + async support |
| Database | Supabase Postgres | Realtime (logical replication) pushes DB changes to browser without hand-rolled broadcast code |
| ORM | SQLAlchemy (async) + Pydantic schemas | standard, debuggable |
| AI provider | Gemini, single provider | strongest structured-output/schema-conformance guarantee — matters because AI output can trigger robot commands |
| AI framework | Direct Gemini SDK calls, NO LangChain/LangGraph | workflow is simple: prompt → structured JSON → validate → execute |
| Command parsing | Deterministic keyword/rule matcher is the PRIMARY path. Gemini is only called when the rule matcher can't confidently classify the input. If Gemini fails/times out, fall back to the rule matcher automatically. | zero-dependency default path = resilient by construction, not just "has a fallback" |
| Anomaly detection | 100% deterministic rule engine (threshold comparisons). NEVER send raw sensor readings to an LLM to "decide" if something is wrong. | predictable, testable, explainable |
| AI's actual job | (1) parse ambiguous natural language into a structured command, (2) explain an ALREADY-CONFIRMED anomaly in plain language. AI never decides severity and never decides anomaly status. | rule engine = truth, AI = interpretation only |
| Hardware transport | WebSocket between backend and ESP32 | low latency, no polling |
| Browser transport | REST for initial state + WebSocket for live updates | |
| Explicitly NOT using | MQTT, RAG/pgvector, LangChain, computer vision, any trained/fine-tuned ML model, Docker/K8s | overengineering for this project's actual needs |
| Simulation mode | Required. A fake-ESP32 module that can replay scripted sensor scenarios (normal / cold room / loud sound / humidity spike / sensor failure / offline) so the backend is fully demoable with zero real hardware connected. | demo insurance, also useful for automated tests |

## 3. Command schema (the only intents that exist — do not invent new ones)

```
MOVE_FORWARD, MOVE_BACKWARD, TURN_LEFT, TURN_RIGHT,
STOP_ROVER, GO_TO_ROOM, CHECK_ROOM,
START_PATROL, STOP_PATROL, RETURN_HOME,
GET_STATUS, GET_ROOM_STATUS, GET_HISTORY, GET_ALERTS,
TAKE_SNAPSHOT
```

Command object shape:
```json
{
  "intent": "CHECK_ROOM",
  "room_id": "room_4",
  "priority": "normal",
  "confirmation_required": false
}
```

## 4. Priority stack (highest wins, always)

```
EMERGENCY_STOP > STOP > RETURN_HOME > RECHECK > PATROL > NORMAL_MOVEMENT
```

Hard rejection rules the backend must enforce regardless of what any command says:
- reject START_PATROL if device status == LOW_BATTERY or OFFLINE
- reject any movement command if an unresolved OBSTACLE event is active
- STOP_ROVER / EMERGENCY_STOP always executes immediately, interrupting anything in progress

## 5. Data model (Postgres/Supabase — build exactly this, tables not listed here should not be created without asking)

`devices, rooms, sensor_readings, room_baselines, anomalies, alerts, patrols, patrol_stops, robot_events, ai_interactions`

Key fields per table:
- **devices**: id, name, device_type, status, battery_level, last_seen, firmware_version, created_at
- **rooms**: id, name, type, x, y, order_index, enabled, created_at
- **sensor_readings**: id, device_id, room_id, timestamp, temperature, humidity, sound_level, battery
- **room_baselines**: id, room_id, temperature_min, temperature_max, humidity_min, humidity_max, sound_threshold, updated_at
- **anomalies**: id, room_id, reading_id, type, severity, value, expected_min, expected_max, status, detected_at, resolved_at
- **alerts**: id, anomaly_id, room_id, severity, message, channel, status, created_at, acknowledged_at
- **patrols**: id, device_id, status, started_at, completed_at
- **patrol_stops**: id, patrol_id, room_id, sequence, status, arrived_at, departed_at
- **robot_events**: id, device_id, event_type, payload, timestamp  (CONNECTED, DISCONNECTED, MOTOR_STARTED, OBSTACLE_DETECTED, ROOM_REACHED, SENSOR_ERROR, LOW_BATTERY, PATROL_STARTED, PATROL_COMPLETED)
- **ai_interactions**: id, user_input, intent, model, latency_ms, success, created_at (do not log indefinitely by default — this is a care-monitoring product; keep it short-retention/debug-only)

## 6. Robot device states (for dashboard status + state machine)

```
IDLE, MOVING, TURNING, PATROLLING, SENSING, RECHECKING,
RETURNING_HOME, OBSTACLE, LOW_BATTERY, ERROR, OFFLINE
```

## 7. API envelope — every endpoint returns this shape

```json
{ "success": true, "data": {}, "error": null, "timestamp": "..." }
{ "success": false, "data": null, "error": { "code": "ROBOT_OFFLINE", "message": "..." } }
```

## 8. Folder structure (target — build toward this, don't collapse it flat)

```
backend/
├── app/
│   ├── main.py
│   ├── api/routes/        # robot.py, rooms.py, sensors.py, patrols.py, alerts.py, analytics.py, ai.py
│   ├── core/               # config.py, security.py, logging.py
│   ├── models/             # SQLAlchemy: device.py, room.py, reading.py, patrol.py, alert.py
│   ├── schemas/            # Pydantic: commands.py, sensors.py, responses.py
│   ├── services/            # robot_service.py, patrol_service.py, sensor_service.py, alert_service.py, analytics_service.py
│   ├── ai/                  # command_agent.py, reasoning_agent.py, prompts.py, schemas.py
│   ├── robotics/            # controller.py, navigation.py, state_machine.py
│   └── workers/             # patrol_worker.py, anomaly_worker.py
├── simulation/               # fake ESP32 + scripted scenarios
├── tests/
├── requirements.txt
└── .env.example
```

## 9. Non-goals — do not add these unless explicitly asked

Medical diagnosis claims, guaranteed fall detection, guaranteed crying detection, accurate
gas/CO2 measurement, autonomous hospital navigation, human-level camera understanding,
guaranteed emergency detection. This is a prototype anomaly-detection platform, not certified
medical equipment.

## 10. How to work

Each task will be given as a scoped, numbered prompt. Do only what that prompt asks.
If a prompt seems to require inventing something not covered in this file (a new table,
a new intent, a new dependency), stop and ask rather than deciding unilaterally.
