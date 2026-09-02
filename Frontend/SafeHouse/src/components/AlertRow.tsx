import type { Alert } from '@/types';
import { formatTimeSec, formatRoom, alertStatusColor, severityColor } from '@/utils/style';

interface AlertRowProps {
  alert: Alert;
  onClick?: () => void;
  compact?: boolean;
}

export function AlertRow({ alert, onClick }: AlertRowProps) {
  const isCritical = alert.severity === 'critical' || alert.severity === 'high';
  const isActive = alert.status === 'active' || alert.status === 'ACTIVE';

  return (
    <div
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      className={`
        hud-panel-inset px-3 py-2 flex items-center justify-between gap-2.5 cursor-pointer
        border transition-all duration-150 text-2xs mono
        ${
          isCritical
            ? 'border-red/40 bg-[var(--card-critical-bg)] hover:border-red hover:bg-red/10'
            : 'border-amber/40 bg-[var(--card-warning-bg)] hover:border-amber hover:bg-amber/10'
        }
      `}
    >
      {/* Time */}
      <span className="text-ink-muted text-3xs tabular-nums shrink-0">
        {formatTimeSec(alert.created_at)}
      </span>

      <span className="text-ink-muted/40 shrink-0">·</span>

      {/* Room Badge */}
      <span
        className={`font-bold shrink-0 ${
          isCritical ? 'text-red' : 'text-amber'
        }`}
      >
        {formatRoom(alert.room_id)}
      </span>

      {/* Severity */}
      <span className={`font-bold text-3xs uppercase shrink-0 ${severityColor(alert.severity)}`}>
        [{alert.severity}]
      </span>

      {/* Message */}
      <span className="text-ink-muted flex-1 truncate text-3xs font-semibold">
        {alert.message}
      </span>

      {/* Status */}
      <span
        className={`font-black text-3xs shrink-0 tracking-widest uppercase ${alertStatusColor(
          alert.status
        )}`}
      >
        {alert.status}
      </span>
    </div>
  );
}
