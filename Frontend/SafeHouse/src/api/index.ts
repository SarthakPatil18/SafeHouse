import { API_BASE_URL } from '@/config';
import type {
  ApiResponse,
  RobotStatusData,
  RobotCommandPayload,
  Room,
  SensorReading,
  Alert,
  PatrolMission,
} from '@/types';

export class ApiClientError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.name = 'ApiClientError';
    this.code = code;
  }
}

/** Base helper to execute real HTTP fetch requests and unwrap the API envelope */
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL.replace(/\/+$/, '')}/${endpoint.replace(/^\/+/, '')}`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Network request failed';
    throw new ApiClientError('NETWORK_ERROR', msg);
  }

  let json: ApiResponse<T>;
  try {
    json = (await response.json()) as ApiResponse<T>;
  } catch {
    throw new ApiClientError(
      'INVALID_RESPONSE',
      `Failed to parse JSON response from ${endpoint} (status ${response.status})`
    );
  }

  if (!json.success || json.error) {
    const err = json.error || { code: 'UNKNOWN_ERROR', message: 'API operation failed' };
    throw new ApiClientError(err.code, err.message);
  }

  return json.data as T;
}

// ── Robot Endpoints (Section 6) ──
export const robotApi = {
  /** GET /api/robot/status */
  getStatus(): Promise<RobotStatusData> {
    return request<RobotStatusData>('robot/status');
  },

  /** POST /api/robot/command */
  sendCommand(payload: RobotCommandPayload): Promise<unknown> {
    return request<unknown>('robot/command', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};

// ── Rooms Endpoints (Section 6) ──
export const roomApi = {
  /** GET /api/rooms */
  getRooms(): Promise<Room[]> {
    return request<Room[]>('rooms');
  },

  /** GET /api/rooms/{room_id} */
  getRoom(roomId: string): Promise<Room> {
    return request<Room>(`rooms/${encodeURIComponent(roomId)}`);
  },

  /** POST /api/rooms */
  createRoom(room: Partial<Room>): Promise<Room> {
    return request<Room>('rooms', {
      method: 'POST',
      body: JSON.stringify(room),
    });
  },

  /** PUT /api/rooms/{room_id} */
  updateRoom(roomId: string, room: Partial<Room>): Promise<Room> {
    return request<Room>(`rooms/${encodeURIComponent(roomId)}`, {
      method: 'PUT',
      body: JSON.stringify(room),
    });
  },
};

// ── Sensors Endpoints (Section 6) ──
export const sensorApi = {
  /** GET /api/sensors/latest */
  getLatest(): Promise<SensorReading | SensorReading[]> {
    return request<SensorReading | SensorReading[]>('sensors/latest');
  },

  /** GET /api/sensors/history?room_id=... */
  getHistory(roomId?: string): Promise<SensorReading[]> {
    const query = roomId ? `?room_id=${encodeURIComponent(roomId)}` : '';
    return request<SensorReading[]>(`sensors/history${query}`);
  },
};

// ── Patrols Endpoints (Section 6) ──
export const patrolApi = {
  /** GET /api/patrols */
  getPatrols(): Promise<PatrolMission[]> {
    return request<PatrolMission[]>('patrols');
  },

  /** POST /api/patrols */
  start(deviceId: string = 'rover_01'): Promise<unknown> {
    return request<unknown>('patrols', {
      method: 'POST',
      body: JSON.stringify({ device_id: deviceId }),
    });
  },

  /** POST /api/patrols/{id}/stop */
  stop(patrolId?: string | number): Promise<unknown> {
    const endpoint = patrolId ? `patrols/${patrolId}/stop` : 'patrols/stop';
    return request<unknown>(endpoint, {
      method: 'POST',
      body: JSON.stringify({ device_id: 'rover_01' }),
    });
  },
};

// ── Alerts Endpoints (Section 6) ──
export const alertApi = {
  /** GET /api/alerts?status=...&room_id=... */
  getAlerts(params?: { status?: string; room_id?: string }): Promise<Alert[]> {
    const search = new URLSearchParams();
    if (params?.status) search.set('status', params.status);
    if (params?.room_id) search.set('room_id', params.room_id);
    const qs = search.toString() ? `?${search.toString()}` : '';
    return request<Alert[]>(`alerts${qs}`);
  },

  /** POST /api/alerts/{id}/acknowledge */
  acknowledge(alertId: number | string): Promise<unknown> {
    return request<unknown>(`alerts/${alertId}/acknowledge`, {
      method: 'POST',
    });
  },
};

// ── AI Voice / Natural Language Command (Section 7) ──
export const aiApi = {
  /** POST /api/ai/command { text: "..." } */
  sendCommand(text: string): Promise<any> {
    return request<any>('ai/command', {
      method: 'POST',
      body: JSON.stringify({ text }),
    });
  },
};

// ── System Health ──
export const systemApi = {
  /** GET /health */
  getHealth(): Promise<{ status: string }> {
    return request<{ status: string }>('health');
  },
};
