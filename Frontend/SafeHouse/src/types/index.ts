// Core domain types for SAFEROOM aligned with API_CONTRACT.md

// ── 1. API Response Envelope ──
export interface ApiSuccessResponse<T> {
  success: true;
  data: T;
  error: null;
  timestamp?: string;
}

export interface ApiErrorDetail {
  code: string;
  message: string;
}

export interface ApiErrorResponse {
  success: false;
  data: null;
  error: ApiErrorDetail;
  timestamp?: string;
}

export type ApiResponse<T> = ApiSuccessResponse<T> | ApiErrorResponse;

// ── 2. Sensor Reading Shape ──
export interface SensorReading {
  device_id: string;
  room_id: string;
  timestamp: string;
  pir_motion: boolean;
  gas_mq135: number;
  gas_mq2: number;
  ultrasonic_distance_cm: number;
  battery: number;
  temperature?: number;
  humidity?: number;
  sound_db?: number;
}

// ── 3. Room & Baseline Shape ──
export type MotionMode = 'expect_presence' | 'expect_absence' | 'ignore';

export interface RoomBaseline {
  gas_mq135_max: number;
  gas_mq2_max: number;
  motion_mode: MotionMode;
  no_motion_timeout_seconds: number;
}

export interface Room {
  id: string;
  name: string;
  type: string;
  x: number;
  y: number;
  enabled: boolean;
  baseline: RoomBaseline;
}

// ── 4. Alert Shape ──
export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical' | string;
export type AlertStatus = 'active' | 'acknowledged' | string;

export interface Alert {
  id: number;
  anomaly_id: number;
  room_id: string;
  severity: AlertSeverity;
  message: string;
  channel: string;
  status: AlertStatus;
  created_at: string;
  acknowledged_at: string | null;
}

// ── 5. Command Intents (Exact 15 from Section 5) ──
export type CommandIntent =
  | 'MOVE_FORWARD'
  | 'MOVE_BACKWARD'
  | 'TURN_LEFT'
  | 'TURN_RIGHT'
  | 'STOP_ROVER'
  | 'GO_TO_ROOM'
  | 'CHECK_ROOM'
  | 'START_PATROL'
  | 'STOP_PATROL'
  | 'RETURN_HOME'
  | 'GET_STATUS'
  | 'GET_ROOM_STATUS'
  | 'GET_HISTORY'
  | 'GET_ALERTS'
  | 'TAKE_SNAPSHOT';

export interface RobotCommandPayload {
  intent: CommandIntent;
  room_id?: string;
  priority?: number;
}

// ── 6. Robot Status ──
export type RobotState =
  | 'idle'
  | 'patrolling'
  | 'moving'
  | 'charging'
  | 'stopped'
  | 'emergency_stop'
  | string;

export interface RobotStatusData {
  device_id: string;
  status: RobotState;
  battery_level: number;
  has_obstacle: boolean;
  current_room_id: string | null;
  timestamp: string;
  name?: string;
  device_type?: string;
  firmware_version?: string;
  last_seen?: string | null;
}

// ── 7. Patrol Mission ──
export interface PatrolMission {
  id?: number | string;
  device_id?: string;
  status: 'in_progress' | 'completed' | 'stopped' | 'idle' | string;
  current_room_id?: string | null;
  started_at?: string;
  completed_at?: string | null;
  progress?: number;
}

export interface PatrolRecord {
  id: number | string;
  timestamp: string | number;
  status: string;
  message?: string;
}

// ── 8. Dashboard WebSocket Message ──
export type DashboardWebSocketMessage =
  | { type: 'sensor_update'; data: SensorReading }
  | { type: 'alert'; data: Alert };

// ── 9. UI / Terminal State ──
export interface ConsoleMessage {
  id: string;
  source: 'SYS' | 'YOU' | 'ERR';
  text: string;
  timestamp: number;
  kind?: 'info' | 'success' | 'warning' | 'critical';
}
