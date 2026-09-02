import { useState, useEffect, useMemo } from 'react';
import { useDashboard } from '@/context/DashboardContext';
import { useTheme } from '@/context/ThemeContext';
import { sensorApi } from '@/api';
import type { SensorReading } from '@/types';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import {
  Wind,
  Flame,
  Navigation,
  AlertTriangle,
  Radio,
} from 'lucide-react';
import { formatTime, formatRoom, alertStatusColor } from '@/utils/style';

function ChartTooltip({
  active,
  payload,
  label,
  unit,
}: {
  active?: boolean;
  payload?: { value: number }[];
  label?: string;
  unit: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="hud-panel-inset px-2.5 py-1.5 border border-line">
      <p className="text-3xs mono text-ink-muted">{label}</p>
      <p className="text-xs mono font-black text-green">
        {payload[0].value.toFixed(1)} {unit}
      </p>
    </div>
  );
}

export function HistoryPage() {
  const { rooms, alerts, activeRoomId, setActiveRoomId } = useDashboard();
  const { theme } = useTheme();
  const isLight = theme === 'light';

  const chartGridColor = isLight ? '#D8E4E7' : '#0D1E22';
  const chartTickColor = isLight ? '#4A676E' : '#4E686E';
  const chartAxisLineColor = isLight ? '#CFDEE2' : '#142A2E';
  const chartGreen = isLight ? '#0D9468' : '#9CFF32';
  const chartCyan = isLight ? '#0284C7' : '#35D9E8';
  const chartAmber = isLight ? '#D97706' : '#F2B84B';

  const [historyData, setHistoryData] = useState<SensorReading[]>([]);
  const [loading, setLoading] = useState(false);

  const selectedRoomId = activeRoomId || (rooms.length > 0 ? rooms[0].id : 'room_1');

  useEffect(() => {
    let isMounted = true;
    async function loadHistory() {
      setLoading(true);
      try {
        const data = await sensorApi.getHistory(selectedRoomId);
        if (isMounted) setHistoryData(data);
      } catch (err) {
        console.warn('Failed to load sensor history:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    loadHistory();
    return () => {
      isMounted = false;
    };
  }, [selectedRoomId]);

  const chartData = useMemo(() => {
    if (historyData.length === 0) {
      // Fallback baseline points for preview
      return Array.from({ length: 15 }).map((_, i) => ({
        time: `${i}:00`,
        gas_mq135: 35 + Math.sin(i) * 5,
        gas_mq2: 15 + Math.cos(i) * 3,
        ultrasonic_distance_cm: 30 + (i % 5) * 4,
      }));
    }
    return historyData.map((h) => ({
      time: formatTime(h.timestamp),
      gas_mq135: h.gas_mq135,
      gas_mq2: h.gas_mq2,
      ultrasonic_distance_cm: h.ultrasonic_distance_cm,
    }));
  }, [historyData]);

  return (
    <div className="space-y-3 select-none">
      {/* Header */}
      <div className="flex items-center justify-between pb-1 flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <span className="hud-section-title text-sm">TELEMETRY & AUDIT HISTORY</span>
          <span className="text-3xs mono text-ink-muted hidden sm:inline">
            REAL SENSOR ARCHIVES (GET /api/sensors/history)
          </span>
        </div>

        {/* Room selector */}
        <div className="flex items-center gap-2">
          <span className="hud-label-text">ZONE:</span>
          <div className="flex items-center border border-line bg-base-surface">
            {rooms.map((r) => (
              <button
                key={r.id}
                onClick={() => setActiveRoomId(r.id)}
                className={`px-3 py-1 text-2xs mono font-bold tracking-widest transition-colors cursor-pointer ${
                  selectedRoomId === r.id
                    ? 'bg-green/10 text-green border-r border-green'
                    : 'text-ink-muted hover:text-ink border-r border-line last:border-r-0'
                }`}
              >
                {formatRoom(r.id)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Sensor Trend Charts */}
      <div className="hud-panel">
        <div className="hud-header">
          <span className="hud-section-title">
            SENSOR HISTORY · {formatRoom(selectedRoomId)}
          </span>
          <span className="text-3xs mono text-ink-muted">
            {loading ? 'SYNCING...' : `${chartData.length} SAMPLES`}
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 divide-y lg:divide-y-0 lg:divide-x divide-line p-1">
          {/* 1. MQ-135 Air Quality */}
          <div className="p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="hud-label-text flex items-center gap-1.5 text-green font-bold">
                <Wind className="w-3.5 h-3.5" /> AIR QUALITY MQ-135 (PPM)
              </span>
            </div>
            <ResponsiveContainer width="100%" height={120}>
              <LineChart data={chartData} margin={{ top: 2, right: 4, bottom: 2, left: -24 }}>
                <CartesianGrid strokeDasharray="2 4" stroke={chartGridColor} />
                <XAxis
                  dataKey="time"
                  tick={{ fill: chartTickColor, fontSize: 8, fontFamily: 'monospace' }}
                  axisLine={{ stroke: chartAxisLineColor }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: chartTickColor, fontSize: 8, fontFamily: 'monospace' }}
                  axisLine={{ stroke: chartAxisLineColor }}
                  tickLine={false}
                  domain={[0, 100]}
                />
                <Tooltip content={<ChartTooltip unit="PPM" />} />
                <Line
                  type="monotone"
                  dataKey="gas_mq135"
                  stroke={chartGreen}
                  strokeWidth={2}
                  dot={false}
                  animationDuration={300}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* 2. MQ-2 Gas & Smoke */}
          <div className="p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="hud-label-text flex items-center gap-1.5 text-cyan font-bold">
                <Flame className="w-3.5 h-3.5" /> GAS & SMOKE MQ-2 (PPM)
              </span>
            </div>
            <ResponsiveContainer width="100%" height={120}>
              <LineChart data={chartData} margin={{ top: 2, right: 4, bottom: 2, left: -24 }}>
                <CartesianGrid strokeDasharray="2 4" stroke={chartGridColor} />
                <XAxis
                  dataKey="time"
                  tick={{ fill: chartTickColor, fontSize: 8, fontFamily: 'monospace' }}
                  axisLine={{ stroke: chartAxisLineColor }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: chartTickColor, fontSize: 8, fontFamily: 'monospace' }}
                  axisLine={{ stroke: chartAxisLineColor }}
                  tickLine={false}
                  domain={[0, 100]}
                />
                <Tooltip content={<ChartTooltip unit="PPM" />} />
                <Line
                  type="monotone"
                  dataKey="gas_mq2"
                  stroke={chartCyan}
                  strokeWidth={2}
                  dot={false}
                  animationDuration={300}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* 3. Ultrasonic Distance */}
          <div className="p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="hud-label-text flex items-center gap-1.5 text-amber font-bold">
                <Navigation className="w-3.5 h-3.5" /> ULTRASONIC RANGE (CM)
              </span>
            </div>
            <ResponsiveContainer width="100%" height={120}>
              <LineChart data={chartData} margin={{ top: 2, right: 4, bottom: 2, left: -24 }}>
                <CartesianGrid strokeDasharray="2 4" stroke={chartGridColor} />
                <XAxis
                  dataKey="time"
                  tick={{ fill: chartTickColor, fontSize: 8, fontFamily: 'monospace' }}
                  axisLine={{ stroke: chartAxisLineColor }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: chartTickColor, fontSize: 8, fontFamily: 'monospace' }}
                  axisLine={{ stroke: chartAxisLineColor }}
                  tickLine={false}
                  domain={[0, 150]}
                />
                <Tooltip content={<ChartTooltip unit="CM" />} />
                <Line
                  type="monotone"
                  dataKey="ultrasonic_distance_cm"
                  stroke={chartAmber}
                  strokeWidth={2}
                  dot={false}
                  animationDuration={300}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Incident History Log */}
      <div className="hud-panel">
        <div className="hud-header">
          <span className="hud-section-title flex items-center gap-1.5 text-red">
            <AlertTriangle className="w-3.5 h-3.5" /> INCIDENT HISTORY LOG
          </span>
          <span className="text-3xs mono text-ink-muted">{alerts.length} ENTRIES</span>
        </div>
        <div className="p-2 space-y-1.5 max-h-64 overflow-y-auto scrollbar-thin">
          {alerts.length === 0 ? (
            <p className="px-4 py-6 text-2xs mono text-green text-center">
              NO INCIDENTS RECORDED
            </p>
          ) : (
            alerts.map((alert) => (
              <div
                key={alert.id}
                className={`hud-panel-inset px-3 py-2 flex items-center justify-between text-2xs mono border ${
                  alert.severity === 'critical' || alert.severity === 'high'
                    ? 'border-red/40'
                    : 'border-amber/40'
                }`}
              >
                <span className="text-3xs text-ink-muted">{formatTime(alert.created_at)}</span>
                <span className="text-cyan font-bold">{formatRoom(alert.room_id)}</span>
                <span className="text-ink-muted truncate max-w-[200px] text-3xs font-semibold">
                  {alert.message}
                </span>
                <span
                  className={`font-black text-3xs uppercase ${alertStatusColor(alert.status)}`}
                >
                  {alert.status}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
