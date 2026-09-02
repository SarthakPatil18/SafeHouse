import type { Room, SensorReading } from '@/types';
import { Shield, AlertTriangle, Wind, Flame, Eye } from 'lucide-react';
import { formatRoom } from '@/utils/style';

interface RoomCardProps {
  room: Room;
  reading?: SensorReading;
  hasActiveAlert?: boolean;
  isSelected: boolean;
  onClick: () => void;
}

export function RoomCard({ room, reading, hasActiveAlert = false, isSelected, onClick }: RoomCardProps) {
  const mq135 = reading?.gas_mq135 ?? 30;
  const mq2 = reading?.gas_mq2 ?? 15;
  const motion = reading?.pir_motion ?? false;

  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') onClick();
      }}
      className={`
        hud-panel p-3 cursor-pointer transition-all duration-150 relative select-none
        ${
          isSelected
            ? 'hud-glow-cyan border-cyan bg-[var(--card-selected-bg)]'
            : hasActiveAlert
            ? 'hud-glow-red border-red bg-[var(--card-critical-bg)]'
            : 'border-line hover:border-line-strong hover:bg-base-elevated'
        }
      `}
    >
      {/* Top Row: Room Label & Name */}
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs mono font-black text-ink tracking-widest">
          {formatRoom(room.id)}
        </span>
        <span className="text-3xs mono text-cyan uppercase font-semibold">
          {room.name || room.type}
        </span>
      </div>

      {/* State Badge: Derived directly from backend alert state */}
      <div className="flex items-center gap-2 mb-2.5">
        {hasActiveAlert ? (
          <div className="flex items-center gap-1.5 text-red">
            <AlertTriangle className="w-4 h-4 text-red animate-pulse" />
            <span className="text-xs mono font-black tracking-widest">ACTIVE ANOMALY</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 text-green">
            <Shield className="w-4 h-4 text-green" />
            <span className="text-xs mono font-black tracking-widest">ALL CLEAR</span>
          </div>
        )}
      </div>

      {/* Bottom Row: Real Telemetry (MQ-135, MQ-2, PIR) */}
      <div className="flex items-center justify-between text-2xs mono pt-1.5 border-t border-line/60">
        {/* Air Quality MQ-135 */}
        <div className="flex items-center gap-1">
          <Wind className="w-3 h-3 text-green" />
          <span className="tabular-nums font-semibold text-ink">
            {mq135.toFixed(0)} <span className="text-3xs text-ink-muted">PPM</span>
          </span>
        </div>

        {/* Smoke/Gas MQ-2 */}
        <div className="flex items-center gap-1">
          <Flame className="w-3 h-3 text-cyan" />
          <span className="tabular-nums font-semibold text-ink">
            {mq2.toFixed(0)} <span className="text-3xs text-ink-muted">PPM</span>
          </span>
        </div>

        {/* Motion Indicator */}
        <div className="flex items-center gap-1">
          <Eye className={`w-3 h-3 ${motion ? 'text-green' : 'text-ink-muted opacity-40'}`} />
          <span
            className={`font-bold tracking-wider text-3xs ${
              motion ? 'text-green' : 'text-ink-muted'
            }`}
          >
            {motion ? 'MOTION' : 'CLEAR'}
          </span>
        </div>
      </div>
    </div>
  );
}
