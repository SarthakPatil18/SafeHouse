import { useDashboard } from '@/context/DashboardContext';
import { AlertRow } from './AlertRow';

interface AlertPanelProps {
  onViewAll: () => void;
  onSelectAlert: (alertId: number) => void;
  maxItems?: number;
}

export function AlertPanel({ onViewAll, onSelectAlert, maxItems = 4 }: AlertPanelProps) {
  const { alerts } = useDashboard();
  const displayAlerts = alerts.slice(0, maxItems);

  return (
    <div className="hud-panel flex flex-col h-full select-none">
      {/* Header */}
      <div className="hud-header">
        <span className="text-xs mono font-black text-red tracking-wider">ALERT CONSOLE</span>
        <button
          onClick={onViewAll}
          className="text-3xs mono text-ink-muted hover:text-ink transition-colors tracking-widest cursor-pointer"
        >
          VIEW ALL →
        </button>
      </div>

      {/* Alert list */}
      <div className="p-3 space-y-2 flex-1 overflow-y-auto scrollbar-thin">
        {displayAlerts.length === 0 ? (
          <div className="py-6 text-center text-xs mono text-green">
            NO ACTIVE ALERTS · ALL PARAMETERS NORMAL
          </div>
        ) : (
          displayAlerts.map((alert) => (
            <AlertRow
              key={alert.id}
              alert={alert}
              onClick={() => onSelectAlert(alert.id)}
            />
          ))
        )}
      </div>
    </div>
  );
}
