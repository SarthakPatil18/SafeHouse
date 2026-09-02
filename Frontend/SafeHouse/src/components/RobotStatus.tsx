import { Battery, Shield, AlertOctagon } from 'lucide-react';
import type { RobotStatusData } from '@/types';
import { formatRoom } from '@/utils/style';

interface RobotStatusProps {
  robot: RobotStatusData;
}

function ProgressBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="h-1.5 bg-base-hover rounded-sm overflow-hidden">
      <div
        className={`h-full rounded-sm transition-all duration-500 ${color}`}
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
      />
    </div>
  );
}

export function RobotStatus({ robot }: RobotStatusProps) {
  const isPatrolling = robot.status === 'patrolling' || robot.status === 'moving';
  const stateColor = isPatrolling
    ? 'text-green'
    : robot.status === 'emergency_stop'
    ? 'text-red'
    : 'text-cyan';

  const stateDot = isPatrolling
    ? 'bg-green'
    : robot.status === 'emergency_stop'
    ? 'bg-red'
    : 'bg-cyan';

  return (
    <div className="panel p-3 space-y-3">
      {/* State */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span
            className={`w-2 h-2 rounded-full ${stateDot} ${
              isPatrolling ? 'animate-pulse-green' : ''
            }`}
          />
          <span className={`text-xs mono font-medium tracking-wider uppercase ${stateColor}`}>
            {robot.status}
          </span>
        </div>
        <p className="text-2xs mono text-ink-muted">
          {robot.current_room_id
            ? `AT ${formatRoom(robot.current_room_id)}`
            : 'LOCATION: DOCKED'}
        </p>
      </div>

      {/* Battery */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="label-text flex items-center gap-1">
            <Battery className="w-3 h-3" /> BATTERY
          </span>
          <span className="text-2xs mono text-ink-muted">{Math.round(robot.battery_level)}%</span>
        </div>
        <ProgressBar
          value={robot.battery_level}
          color={
            robot.battery_level > 50
              ? 'bg-green'
              : robot.battery_level > 20
              ? 'bg-amber'
              : 'bg-red'
          }
        />
      </div>

      {/* Obstacle Proximity Status */}
      <div className="flex items-center justify-between pt-1 border-t border-line">
        <span className="label-text flex items-center gap-1">
          <AlertOctagon className="w-3 h-3" /> OBSTACLE
        </span>
        <span
          className={`text-2xs mono font-bold ${
            robot.has_obstacle ? 'text-red animate-pulse' : 'text-green'
          }`}
        >
          {robot.has_obstacle ? 'DETECTED' : 'CLEAR'}
        </span>
      </div>

      {/* Device Info */}
      <div className="flex items-center justify-between pt-1 border-t border-line">
        <span className="label-text flex items-center gap-1">
          <Shield className="w-3 h-3" /> DEVICE ID
        </span>
        <span className="text-2xs mono text-ink font-medium">{robot.device_id}</span>
      </div>
    </div>
  );
}
