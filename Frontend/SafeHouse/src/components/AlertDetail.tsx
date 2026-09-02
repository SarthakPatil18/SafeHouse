import { X, CheckCircle2, AlertTriangle, ShieldAlert } from 'lucide-react';
import { useDashboard } from '@/context/DashboardContext';
import { useTheme } from '@/context/ThemeContext';
import { alertStatusColor, formatTimeSec, formatRoom, severityColor } from '@/utils/style';

interface AlertDetailProps {
  alertId: number | string;
  onClose: () => void;
  onAcknowledge: (alertId: number | string) => void;
}

export function AlertDetail({ alertId, onClose, onAcknowledge }: AlertDetailProps) {
  const { alerts } = useDashboard();
  const { theme } = useTheme();
  const isLight = theme === 'light';

  const alert = alerts.find((a) => String(a.id) === String(alertId));
  if (!alert) return null;

  const isActive = alert.status === 'active' || alert.status === 'ACTIVE';
  const isCritical = alert.severity === 'critical' || alert.severity === 'high';

  const severityBorderColor = isCritical
    ? isLight
      ? '#DC2626'
      : '#FF3B30'
    : isLight
    ? '#D97706'
    : '#F2B84B';

  const severityGlowClass = isCritical ? 'hud-glow-red' : 'hud-glow-amber';

  return (
    <div
      className="fixed inset-0 bg-black/75 z-50 flex items-center justify-center p-4 animate-fade-in"
      onClick={onClose}
    >
      <div
        className={`hud-panel w-full max-w-sm animate-slide-in ${severityGlowClass}`}
        style={{ borderTop: `2px solid ${severityBorderColor}` }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="hud-header">
          <div className="flex items-center gap-2">
            <ShieldAlert className={`w-3.5 h-3.5 ${severityColor(alert.severity)}`} />
            <span className="hud-section-title">INCIDENT DETAIL</span>
          </div>
          <button
            onClick={onClose}
            className="text-ink-muted hover:text-ink transition-colors cursor-pointer"
            aria-label="Close alert detail"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-4 space-y-3 bg-base-surface">
          {/* Severity + status row */}
          <div className="flex items-center justify-between py-2 border-b border-line">
            <span
              className={`text-sm mono font-black tracking-widest uppercase ${severityColor(
                alert.severity
              )}`}
            >
              {alert.severity} SEVERITY
            </span>
            <span
              className={`text-2xs mono font-bold tracking-widest uppercase ${alertStatusColor(
                alert.status
              )}`}
            >
              {alert.status}
            </span>
          </div>

          {/* Detail rows */}
          <div className="space-y-2.5">
            {[
              { label: 'INCIDENT ID', value: `#${alert.id}` },
              { label: 'ANOMALY ID',  value: `#${alert.anomaly_id}` },
              { label: 'ZONE',        value: formatRoom(alert.room_id) },
              { label: 'CHANNEL',     value: alert.channel.toUpperCase() },
              { label: 'DETECTED AT', value: formatTimeSec(alert.created_at) },
              ...(alert.acknowledged_at
                ? [{ label: 'ACKNOWLEDGED', value: formatTimeSec(alert.acknowledged_at) }]
                : []),
            ].map(({ label, value }) => (
              <div key={label} className="flex items-center justify-between">
                <span className="hud-label-text">{label}</span>
                <span className="text-xs mono text-ink font-semibold">{value}</span>
              </div>
            ))}

            <div>
              <span className="hud-label-text block mb-1">INCIDENT MESSAGE</span>
              <p
                className={`text-xs mono font-semibold leading-relaxed ${
                  isCritical ? 'text-red' : 'text-amber'
                }`}
              >
                {alert.message}
              </p>
            </div>
          </div>

          {/* Acknowledge action */}
          {isActive && (
            <button
              onClick={() => {
                onAcknowledge(alertId);
                onClose();
              }}
              className="btn-hud btn-hud-green w-full justify-center mt-2 cursor-pointer"
              aria-label="Acknowledge alert"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              ACKNOWLEDGE ALERT
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
