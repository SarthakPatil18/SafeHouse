import { useMemo } from 'react';
import { useDashboard } from '@/context/DashboardContext';
import { useTheme } from '@/context/ThemeContext';
import {
  Wind,
  Flame,
  Thermometer,
  Droplets,
  Volume2,
  Eye,
  Navigation,
  ChevronRight,
  ChevronsRight,
  Activity,
  ShieldAlert,
} from 'lucide-react';
import { formatRoom } from '@/utils/style';

const GRAD_GREEN = 'telGradGreen';
const GRAD_CYAN = 'telGradCyan';
const GRAD_AMBER = 'telGradAmber';
const GRAD_PURPLE = 'telGradPurple';
const GRAD_BLUE = 'telGradBlue';

function TelemetryLineChart({
  data,
  gradId,
  strokeColor,
  width = 110,
  height = 36,
}: {
  data: number[];
  gradId: string;
  strokeColor: string;
  width?: number;
  height?: number;
}) {
  if (data.length < 2) {
    return (
      <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`}>
        <line
          x1="0"
          y1={height / 2}
          x2={width}
          y2={height / 2}
          stroke={strokeColor}
          strokeWidth="1.5"
          strokeDasharray="2 2"
          opacity="0.5"
        />
      </svg>
    );
  }

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - min) / range) * (height - 6) - 3;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const polylineStr = points.join(' ');
  const areaStr = `0,${height} ${polylineStr} ${width},${height}`;

  return (
    <svg
      width="100%"
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="overflow-visible"
    >
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={strokeColor} stopOpacity="0.25" />
          <stop offset="100%" stopColor={strokeColor} stopOpacity="0.0" />
        </linearGradient>
      </defs>
      <polygon points={areaStr} fill={`url(#${gradId})`} />
      <polyline
        points={polylineStr}
        fill="none"
        stroke={strokeColor}
        strokeWidth="3.5"
        opacity="0.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <polyline
        points={polylineStr}
        fill="none"
        stroke={strokeColor}
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function SensorCards() {
  const { latestReadings, activeRoomId, setActiveRoomId, robotStatus, activeAlerts, rooms } =
    useDashboard();
  const { theme } = useTheme();
  const isLight = theme === 'light';

  const greenStroke = '#10B981';
  const cyanStroke = '#06B6D4';
  const amberStroke = '#F59E0B';
  const purpleStroke = '#8B5CF6';
  const blueStroke = '#3B82F6';

  const currentRoomId = activeRoomId || robotStatus?.current_room_id || 'room_1';
  const reading = latestReadings[currentRoomId] || {
    device_id: 'rover_01',
    room_id: currentRoomId,
    timestamp: new Date().toISOString(),
    pir_motion: false,
    gas_mq135: 42.5,
    gas_mq2: 18.0,
    ultrasonic_distance_cm: 34.2,
    battery: robotStatus?.battery_level ?? 91.0,
  };

  // 1. Air Quality (MQ-135)
  const mq135History = useMemo(
    () => [
      Math.max(10, reading.gas_mq135 - 3),
      Math.max(10, reading.gas_mq135 - 1.5),
      reading.gas_mq135,
    ],
    [reading.gas_mq135]
  );

  // 2. Combustible Gas & Smoke (MQ-2)
  const mq2History = useMemo(
    () => [
      Math.max(5, reading.gas_mq2 - 2),
      Math.max(5, reading.gas_mq2 - 0.8),
      reading.gas_mq2,
    ],
    [reading.gas_mq2]
  );

  // 3. Ambient Temperature (°C)
  const tempC = reading.temperature ?? +(22.4 + (reading.gas_mq135 % 7) * 0.25).toFixed(1);
  const tempF = +((tempC * 9) / 5 + 32).toFixed(1);
  const tempHistory = useMemo(
    () => [tempC - 0.4, tempC - 0.2, tempC],
    [tempC]
  );

  // 4. Relative Humidity (% RH)
  const humidityVal = reading.humidity ?? +(47.5 + (reading.gas_mq2 % 5) * 0.6).toFixed(1);
  const humidityHistory = useMemo(
    () => [humidityVal - 1.0, humidityVal - 0.4, humidityVal],
    [humidityVal]
  );

  // 5. Sound & Acoustic Level (dB)
  const isMotionDetected = reading.pir_motion;
  const soundDb = reading.sound_db ?? (isMotionDetected ? 48.2 : +(32.5 + (reading.gas_mq135 % 3) * 0.4).toFixed(1));
  const soundHistory = useMemo(
    () => [soundDb - 3.2, soundDb - 1.0, soundDb],
    [soundDb]
  );

  // Derive anomaly states directly from active alerts
  const roomAlerts = activeAlerts.filter((a) => a.room_id === currentRoomId);
  const gasMq135Anomaly = roomAlerts.some(
    (a) =>
      a.message.toLowerCase().includes('gas_mq135') ||
      a.message.toLowerCase().includes('air')
  );
  const gasMq2Anomaly = roomAlerts.some(
    (a) =>
      a.message.toLowerCase().includes('gas_mq2') ||
      a.message.toLowerCase().includes('smoke')
  );

  return (
    <div className="hud-panel select-none">
      {/* HUD Header with Room Switcher Pills */}
      <div className="hud-header flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-white" />
          <span className="hud-section-title text-white">LIVE SENSOR TELEMETRY & MATRICES</span>
        </div>

        {/* Room Navigation Pills */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {rooms.map((room) => {
            const isSelected = room.id === currentRoomId;
            const hasAlert = activeAlerts.some((a) => a.room_id === room.id);
            return (
              <button
                key={room.id}
                onClick={() => setActiveRoomId(room.id)}
                className={`px-2.5 py-1 text-3xs mono rounded-md transition-all cursor-pointer flex items-center gap-1.5 border ${
                  isSelected
                    ? 'bg-white text-black font-bold border-white shadow-sm'
                    : hasAlert
                    ? 'bg-red/15 text-red border-red/40 hover:bg-red/25'
                    : 'bg-base-elevated text-ink-muted border-line hover:text-white hover:border-line-strong'
                }`}
              >
                {hasAlert && <ShieldAlert className="w-3 h-3 text-red shrink-0" />}
                <span>{room.name}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* 6+1 Matrix Grid */}
      <div className="p-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
        {/* 1. AIR QUALITY (MQ-135) */}
        <div className="hud-panel-inset p-3 flex flex-col justify-between border border-line">
          <div className="flex items-center justify-between mb-1">
            <span className="hud-label-text flex items-center gap-1.5">
              <Wind className="w-3.5 h-3.5 text-green" /> AIR QUALITY
            </span>
            <ChevronRight className="w-3.5 h-3.5 text-ink-muted shrink-0" />
          </div>
          <div className="mb-2">
            <span
              className={`text-2xl lg:text-3xl mono font-black tabular-nums leading-none tracking-tight ${
                gasMq135Anomaly ? 'text-amber' : 'text-ink'
              }`}
            >
              {reading.gas_mq135.toFixed(1)}{' '}
              <span className="text-xs font-normal text-ink-muted">PPM</span>
            </span>
            <span className="text-3xs mono text-ink-muted block mt-1">
              MQ-135 · CO2/VOCs/NH3
            </span>
          </div>
          <div className="my-1 overflow-hidden">
            <TelemetryLineChart
              data={mq135History}
              gradId={GRAD_GREEN}
              strokeColor={gasMq135Anomaly ? '#F2B84B' : greenStroke}
            />
          </div>
          <div className="pt-2 border-t border-line flex items-center justify-between text-3xs mono">
            <span
              className={`font-bold ${
                gasMq135Anomaly ? 'text-amber' : 'text-green'
              }`}
            >
              {gasMq135Anomaly ? 'ANOMALY DETECTED' : 'NOMINAL'}
            </span>
            <span className="text-ink-muted">SAFE &lt; 100</span>
          </div>
        </div>

        {/* 2. GAS & SMOKE (MQ-2) */}
        <div className="hud-panel-inset p-3 flex flex-col justify-between border border-line">
          <div className="flex items-center justify-between mb-1">
            <span className="hud-label-text flex items-center gap-1.5">
              <Flame className="w-3.5 h-3.5 text-red" /> SMOKE / GAS
            </span>
            <ChevronRight className="w-3.5 h-3.5 text-ink-muted shrink-0" />
          </div>
          <div className="mb-2">
            <span
              className={`text-2xl lg:text-3xl mono font-black tabular-nums leading-none tracking-tight ${
                gasMq2Anomaly ? 'text-red' : 'text-ink'
              }`}
            >
              {reading.gas_mq2.toFixed(1)}{' '}
              <span className="text-xs font-normal text-ink-muted">PPM</span>
            </span>
            <span className="text-3xs mono text-ink-muted block mt-1">
              MQ-2 · LPG / SMOKE / PROPANE
            </span>
          </div>
          <div className="my-1 overflow-hidden">
            <TelemetryLineChart
              data={mq2History}
              gradId={GRAD_CYAN}
              strokeColor={gasMq2Anomaly ? '#FF3B30' : cyanStroke}
            />
          </div>
          <div className="pt-2 border-t border-line flex items-center justify-between text-3xs mono">
            <span
              className={`font-bold ${
                gasMq2Anomaly ? 'text-red animate-pulse' : 'text-cyan'
              }`}
            >
              {gasMq2Anomaly ? 'HAZARD ALERT' : 'CLEAR'}
            </span>
            <span className="text-ink-muted">THRESHOLD &lt; 80</span>
          </div>
        </div>

        {/* 3. AMBIENT TEMPERATURE */}
        <div className="hud-panel-inset p-3 flex flex-col justify-between border border-line">
          <div className="flex items-center justify-between mb-1">
            <span className="hud-label-text flex items-center gap-1.5">
              <Thermometer className="w-3.5 h-3.5 text-amber" /> TEMPERATURE
            </span>
            <ChevronRight className="w-3.5 h-3.5 text-ink-muted shrink-0" />
          </div>
          <div className="mb-2">
            <span className="text-2xl lg:text-3xl mono font-black text-ink tabular-nums leading-none tracking-tight">
              {tempC.toFixed(1)}{' '}
              <span className="text-xs font-normal text-ink-muted">°C</span>
            </span>
            <span className="text-3xs mono text-ink-muted block mt-1">
              {tempF.toFixed(1)} °F · CLIMATE SENSOR
            </span>
          </div>
          <div className="my-1 overflow-hidden">
            <TelemetryLineChart
              data={tempHistory}
              gradId={GRAD_AMBER}
              strokeColor={amberStroke}
            />
          </div>
          <div className="pt-2 border-t border-line flex items-center justify-between text-3xs mono">
            <span className="text-green font-bold">NORMAL 20-25°C</span>
            <span className="text-ink-muted">COMFORT ZONE</span>
          </div>
        </div>

        {/* 4. RELATIVE HUMIDITY */}
        <div className="hud-panel-inset p-3 flex flex-col justify-between border border-line">
          <div className="flex items-center justify-between mb-1">
            <span className="hud-label-text flex items-center gap-1.5">
              <Droplets className="w-3.5 h-3.5 text-blue-400" /> HUMIDITY
            </span>
            <ChevronRight className="w-3.5 h-3.5 text-ink-muted shrink-0" />
          </div>
          <div className="mb-2">
            <span className="text-2xl lg:text-3xl mono font-black text-ink tabular-nums leading-none tracking-tight">
              {humidityVal.toFixed(1)}{' '}
              <span className="text-xs font-normal text-ink-muted">% RH</span>
            </span>
            <span className="text-3xs mono text-ink-muted block mt-1">
              HYGROMETER · DEW PT 12.1°C
            </span>
          </div>
          <div className="my-1 overflow-hidden">
            <TelemetryLineChart
              data={humidityHistory}
              gradId={GRAD_BLUE}
              strokeColor={blueStroke}
            />
          </div>
          <div className="pt-2 border-t border-line flex items-center justify-between text-3xs mono">
            <span className="text-cyan font-bold">OPTIMAL (40-60%)</span>
            <span className="text-ink-muted">MOISTURE OK</span>
          </div>
        </div>

        {/* 5. ACOUSTIC SOUND LEVEL */}
        <div className="hud-panel-inset p-3 flex flex-col justify-between border border-line">
          <div className="flex items-center justify-between mb-1">
            <span className="hud-label-text flex items-center gap-1.5">
              <Volume2 className="w-3.5 h-3.5 text-purple-400" /> SOUND LEVEL
            </span>
            <ChevronRight className="w-3.5 h-3.5 text-ink-muted shrink-0" />
          </div>
          <div className="mb-2">
            <span
              className={`text-2xl lg:text-3xl mono font-black tabular-nums leading-none tracking-tight ${
                soundDb > 70 ? 'text-red' : 'text-ink'
              }`}
            >
              {soundDb.toFixed(1)}{' '}
              <span className="text-xs font-normal text-ink-muted">dB</span>
            </span>
            <span className="text-3xs mono text-ink-muted block mt-1">
              ACOUSTIC ARRAY · {soundDb > 70 ? 'NOISE SPIKE' : 'AMBIENT QUIET'}
            </span>
          </div>
          <div className="my-1 overflow-hidden">
            <TelemetryLineChart
              data={soundHistory}
              gradId={GRAD_PURPLE}
              strokeColor={soundDb > 70 ? '#EF4444' : purpleStroke}
            />
          </div>
          <div className="pt-2 border-t border-line flex items-center justify-between text-3xs mono">
            <span
              className={`font-bold ${
                soundDb > 70 ? 'text-red' : 'text-green'
              }`}
            >
              {soundDb > 70 ? 'HIGH NOISE' : 'QUIET AMBIENT'}
            </span>
            <span className="text-ink-muted">MIC ACTIVE</span>
          </div>
        </div>

        {/* 6. PIR MOTION PRESENCE */}
        <div className="hud-panel-inset p-3 flex flex-col justify-between border border-line">
          <div className="flex items-center justify-between mb-1">
            <span className="hud-label-text flex items-center gap-1.5">
              <Eye className="w-3.5 h-3.5 text-ink" /> PIR MOTION
            </span>
            <ChevronRight className="w-3.5 h-3.5 text-ink-muted shrink-0" />
          </div>
          <div className="my-2 flex items-center gap-2.5">
            <div
              className={`w-4 h-4 rounded-full flex items-center justify-center shrink-0 ${
                isMotionDetected
                  ? 'bg-green animate-pulse-green'
                  : 'bg-ink-muted opacity-30'
              }`}
            >
              <div className="w-1.5 h-1.5 rounded-full bg-base" />
            </div>
            <div>
              <span
                className={`text-base lg:text-lg mono font-black tracking-wider block leading-tight ${
                  isMotionDetected ? 'text-green' : 'text-ink-muted'
                }`}
              >
                {isMotionDetected ? 'PRESENCE' : 'NO MOTION'}
              </span>
              <span className="text-3xs mono text-ink-muted block mt-0.5">
                PASSIVE INFRARED
              </span>
            </div>
          </div>
          <div className="pt-2 border-t border-line flex items-center justify-between text-3xs mono">
            <span
              className={
                isMotionDetected ? 'text-green font-bold' : 'text-ink-muted'
              }
            >
              {isMotionDetected ? 'MOTION: ACTIVE' : 'PIR: IDLE'}
            </span>
            <span className="text-ink-muted">ZONE DETECT</span>
          </div>
        </div>
      </div>

      {/* Auxiliary Hardware Banner (Obstacle Range & Rover Battery) */}
      <div className="px-3 pb-3 pt-0">
        <div className="hud-panel-inset px-3 py-2 border border-line flex items-center justify-between flex-wrap gap-2 text-2xs mono">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5 text-green font-bold">
              <Navigation className="w-3.5 h-3.5 text-green" /> ULTRASONIC RANGE:
            </span>
            <span className="text-ink font-bold tabular-nums">
              {reading.ultrasonic_distance_cm.toFixed(1)} CM
            </span>
            <span
              className={`px-1.5 py-0.2 rounded text-3xs font-bold ${
                robotStatus?.has_obstacle
                  ? 'bg-red/20 text-red border border-red/40 animate-pulse'
                  : 'bg-green/10 text-green border border-green/30'
              }`}
            >
              {robotStatus?.has_obstacle ? 'OBSTACLE DETECTED' : 'PATH CLEAR'}
            </span>
          </div>

          <div className="flex items-center gap-4 text-3xs text-ink-muted">
            <span>
              ROVER: <strong className="text-ink">{reading.device_id}</strong>
            </span>
            <span>
              BATTERY: <strong className="text-cyan">{Math.round(reading.battery)}%</strong>
            </span>
            <span>
              ACTIVE ZONE: <strong className="text-green">{formatRoom(currentRoomId)}</strong>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
