import { useState } from 'react';
import { Play, Square, CheckCircle2, Circle, ArrowRight, Shield } from 'lucide-react';
import { useDashboard } from '@/context/DashboardContext';
import { formatRoom } from '@/utils/style';
import { SensorCards } from '@/components/SensorCard';
import { PatrolMap } from '@/components/PatrolMap';

export function PatrolPage() {
  const {
    robotStatus,
    rooms,
    activeRoomId,
    setActiveRoomId,
    startPatrol,
    stopPatrol,
  } = useDashboard();

  const [actionLoading, setActionLoading] = useState(false);

  const statusStr = robotStatus?.status || 'idle';
  const isPatrolling = statusStr === 'patrolling' || statusStr === 'moving';
  const statusColor = isPatrolling
    ? 'text-green'
    : statusStr === 'emergency_stop'
    ? 'text-red'
    : 'text-ink-muted';

  const handleStart = async () => {
    try {
      setActionLoading(true);
      await startPatrol();
    } catch (err) {
      console.error('Failed to start patrol:', err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleStop = async () => {
    try {
      setActionLoading(true);
      await stopPatrol();
    } catch (err) {
      console.error('Failed to stop patrol:', err);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-3 select-none">
      {/* Header */}
      <div className="flex items-center justify-between pb-1">
        <div className="flex items-center gap-3">
          <span className="hud-section-title text-sm">PATROL OPERATIONS</span>
          <span className="text-3xs mono text-ink-muted hidden sm:inline">
            AUTONOMOUS WAYPOINT SWEEP · MISSION CONTROL
          </span>
        </div>
      </div>

      {/* Live Map Centerpiece */}
      <div className="h-[380px] sm:h-[420px] lg:h-[460px]">
        <PatrolMap
          selectedRoom={activeRoomId}
          onSelectRoom={(id) => setActiveRoomId(activeRoomId === id ? null : id)}
        />
      </div>

      {/* Mission Status & Controls */}
      <div className="hud-panel">
        <div className="hud-header">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span
                className={`status-dot ${
                  isPatrolling ? 'bg-green animate-pulse-green' : 'bg-ink-muted'
                }`}
              />
              <span className={`text-sm mono font-black tracking-widest uppercase ${statusColor}`}>
                {statusStr}
              </span>
            </div>
            <span className="text-2xs mono text-ink-muted">
              DEVICE: {robotStatus?.device_id || 'rover_01'}
            </span>
          </div>
          <span className="text-3xs mono text-ink-muted">
            LOCATION: {formatRoom(robotStatus?.current_room_id)}
          </span>
        </div>

        <div className="p-4 space-y-4">
          {/* Waypoints Grid */}
          <div>
            <span className="hud-label-text block mb-2">CONFIGURED PATROL WAYPOINTS</span>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              {rooms.map((room, idx) => {
                const isCurrent = robotStatus?.current_room_id === room.id;
                return (
                  <div
                    key={room.id}
                    className={`hud-panel-inset p-3 border transition-all ${
                      isCurrent
                        ? 'border-green hud-glow-green bg-green/10'
                        : 'border-line'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      {isCurrent ? (
                        <ArrowRight className="w-3.5 h-3.5 text-green animate-pulse" />
                      ) : (
                        <Circle className="w-3.5 h-3.5 text-ink-faint" />
                      )}
                      <span className="text-xs mono font-black text-ink">
                        {formatRoom(room.id)}
                      </span>
                    </div>
                    <p className="text-3xs mono text-cyan truncate font-semibold">
                      {room.name || room.type}
                    </p>
                    <p
                      className={`text-3xs mono font-bold tracking-widest mt-1 ${
                        isCurrent ? 'text-green' : 'text-ink-muted'
                      }`}
                    >
                      {isCurrent ? 'ACTIVE TARGET' : `WAYPOINT #0${idx + 1}`}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Action Buttons: Only Start & Stop (No Pause/Resume) */}
          <div className="flex items-center gap-2 pt-2 border-t border-line">
            {!isPatrolling ? (
              <button
                onClick={handleStart}
                disabled={actionLoading}
                className="btn-hud btn-hud-green disabled:opacity-50 cursor-pointer"
              >
                <Play className="w-3.5 h-3.5" /> START PATROL
              </button>
            ) : (
              <button
                onClick={handleStop}
                disabled={actionLoading}
                className="btn-hud btn-hud-red disabled:opacity-50 cursor-pointer"
              >
                <Square className="w-3.5 h-3.5" /> STOP PATROL
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Telemetry Strip */}
      <SensorCards />
    </div>
  );
}
