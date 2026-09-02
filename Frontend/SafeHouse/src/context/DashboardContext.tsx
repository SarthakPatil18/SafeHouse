import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { WS_DASHBOARD_URL } from '@/config';
import { robotApi, roomApi, alertApi, sensorApi, aiApi, patrolApi } from '@/api';
import type {
  SensorReading,
  Alert,
  Room,
  RobotStatusData,
  RobotCommandPayload,
  DashboardWebSocketMessage,
} from '@/types';

interface DashboardContextType {
  wsConnected: boolean;
  robotStatus: RobotStatusData | null;
  rooms: Room[];
  latestReadings: Record<string, SensorReading>;
  activeRoomId: string | null;
  setActiveRoomId: (id: string | null) => void;
  alerts: Alert[];
  activeAlerts: Alert[];
  refreshAlerts: () => Promise<void>;
  refreshRooms: () => Promise<void>;
  refreshRobotStatus: () => Promise<void>;
  acknowledgeAlert: (alertId: number | string) => Promise<void>;
  sendRobotCommand: (payload: RobotCommandPayload) => Promise<unknown>;
  sendAiCommand: (text: string) => Promise<any>;
  startPatrol: () => Promise<unknown>;
  stopPatrol: (patrolId?: string | number) => Promise<unknown>;
  error: string | null;
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

export const DashboardProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [wsConnected, setWsConnected] = useState(false);
  const [robotStatus, setRobotStatus] = useState<RobotStatusData | null>(null);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [latestReadings, setLatestReadings] = useState<Record<string, SensorReading>>({});
  const [activeRoomId, setActiveRoomId] = useState<string | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Fetch initial REST data
  const refreshRooms = useCallback(async () => {
    try {
      const roomList = await roomApi.getRooms();
      setRooms(roomList);
      if (roomList.length > 0 && !activeRoomId) {
        setActiveRoomId(roomList[0].id);
      }
    } catch (err: unknown) {
      console.warn('Failed to fetch rooms from backend:', err);
    }
  }, [activeRoomId]);

  const refreshAlerts = useCallback(async () => {
    try {
      const alertList = await alertApi.getAlerts();
      setAlerts(alertList);
    } catch (err: unknown) {
      console.warn('Failed to fetch alerts from backend:', err);
    }
  }, []);

  const refreshRobotStatus = useCallback(async () => {
    try {
      const status = await robotApi.getStatus();
      setRobotStatus(status);
    } catch (err: unknown) {
      console.warn('Failed to fetch robot status from backend:', err);
    }
  }, []);

  const refreshLatestSensors = useCallback(async () => {
    try {
      const latest = await sensorApi.getLatest();
      if (Array.isArray(latest)) {
        const map: Record<string, SensorReading> = {};
        for (const r of latest) {
          if (r.room_id) map[r.room_id] = r;
        }
        setLatestReadings((prev) => ({ ...prev, ...map }));
      } else if (latest && latest.room_id) {
        setLatestReadings((prev) => ({ ...prev, [latest.room_id]: latest }));
      }
    } catch (err: unknown) {
      console.warn('Failed to fetch latest sensors from backend:', err);
    }
  }, []);

  // WebSocket Live Connection (/ws/dashboard per Section 8)
  useEffect(() => {
    let isMounted = true;

    function connectWs() {
      if (!isMounted) return;
      try {
        const ws = new WebSocket(WS_DASHBOARD_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          if (!isMounted) return;
          setWsConnected(true);
          setError(null);
        };

        ws.onmessage = (event) => {
          if (!isMounted) return;
          try {
            const msg: DashboardWebSocketMessage = JSON.parse(event.data);
            if (msg.type === 'sensor_update' && msg.data) {
              const reading = msg.data;
              if (reading.room_id) {
                setLatestReadings((prev) => ({
                  ...prev,
                  [reading.room_id]: reading,
                }));
              }
              // Update robot's battery & location from live telemetry if matched
              setRobotStatus((prev) => {
                if (!prev) return prev;
                return {
                  ...prev,
                  battery_level: reading.battery ?? prev.battery_level,
                  current_room_id: reading.room_id ?? prev.current_room_id,
                };
              });
            } else if (msg.type === 'alert' && msg.data) {
              const newAlert = msg.data;
              setAlerts((prev) => {
                const exists = prev.some((a) => a.id === newAlert.id);
                if (exists) {
                  return prev.map((a) => (a.id === newAlert.id ? newAlert : a));
                }
                return [newAlert, ...prev];
              });
            }
          } catch (err) {
            console.error('Failed to parse WebSocket message:', err);
          }
        };

        ws.onclose = () => {
          if (!isMounted) return;
          setWsConnected(false);
          // Auto-reconnect after 3 seconds
          reconnectTimeoutRef.current = setTimeout(connectWs, 3000);
        };

        ws.onerror = () => {
          if (!isMounted) return;
          setWsConnected(false);
          ws.close();
        };
      } catch (err) {
        if (!isMounted) return;
        setWsConnected(false);
        reconnectTimeoutRef.current = setTimeout(connectWs, 4000);
      }
    }

    connectWs();
    refreshRooms();
    refreshAlerts();
    refreshRobotStatus();
    refreshLatestSensors();

    // Periodic poll as background fallback
    const intervalId = setInterval(() => {
      refreshRobotStatus();
      refreshAlerts();
    }, 5000);

    return () => {
      isMounted = false;
      clearInterval(intervalId);
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [refreshRooms, refreshAlerts, refreshRobotStatus, refreshLatestSensors]);

  // Acknowledge alert via real backend POST /api/alerts/{id}/acknowledge
  const acknowledgeAlert = useCallback(async (alertId: number | string) => {
    await alertApi.acknowledge(alertId);
    setAlerts((prev) =>
      prev.map((a) =>
        a.id === alertId
          ? { ...a, status: 'acknowledged', acknowledged_at: new Date().toISOString() }
          : a
      )
    );
  }, []);

  const sendRobotCommand = useCallback(
    async (payload: RobotCommandPayload) => {
      const res = await robotApi.sendCommand(payload);
      await refreshRobotStatus();
      return res;
    },
    [refreshRobotStatus]
  );

  const sendAiCommand = useCallback(
    async (text: string) => {
      const res = await aiApi.sendCommand(text);
      await refreshRobotStatus();
      await refreshAlerts();
      return res;
    },
    [refreshRobotStatus, refreshAlerts]
  );

  const startPatrol = useCallback(async () => {
    const res = await patrolApi.start();
    await refreshRobotStatus();
    return res;
  }, [refreshRobotStatus]);

  const stopPatrol = useCallback(
    async (patrolId?: string | number) => {
      const res = await patrolApi.stop(patrolId);
      await refreshRobotStatus();
      return res;
    },
    [refreshRobotStatus]
  );

  const activeAlerts = alerts.filter(
    (a) => a.status === 'active' || a.status === 'ACTIVE'
  );

  return (
    <DashboardContext.Provider
      value={{
        wsConnected,
        robotStatus,
        rooms,
        latestReadings,
        activeRoomId,
        setActiveRoomId,
        alerts,
        activeAlerts,
        refreshAlerts,
        refreshRooms,
        refreshRobotStatus,
        acknowledgeAlert,
        sendRobotCommand,
        sendAiCommand,
        startPatrol,
        stopPatrol,
        error,
      }}
    >
      {children}
    </DashboardContext.Provider>
  );
};

export function useDashboard(): DashboardContextType {
  const context = useContext(DashboardContext);
  if (!context) {
    throw new Error('useDashboard must be used within a DashboardProvider');
  }
  return context;
}
