import { useState, useEffect } from 'react';
import { useDashboard } from '@/context/DashboardContext';
import { useTheme } from '@/context/ThemeContext';
import { SafeRoomLogo } from '@/components/SafeRoomLogo';
import { Sun, Moon, Radio } from 'lucide-react';

function formatClock(date: Date): string {
  return date.toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function formatDate(date: Date): string {
  return date
    .toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
    .toUpperCase();
}

export function Header({ onAlertClick }: { onAlertClick: () => void }) {
  const { wsConnected, robotStatus, activeAlerts } = useDashboard();
  const { theme, toggleTheme } = useTheme();
  const [currentDate, setCurrentDate] = useState<Date>(new Date());

  useEffect(() => {
    const timer = setInterval(() => setCurrentDate(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const alertCount = activeAlerts.length;

  return (
    <header className="flex items-center justify-between h-[60px] bg-base-surface border-b border-line px-4 lg:px-6 shrink-0 z-30 relative select-none">
      {/* 1. Left Branding */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 flex items-center justify-center border border-line bg-base-elevated rounded-lg text-ink shadow-xs">
          <SafeRoomLogo size={22} />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-base font-bold tracking-wider text-ink mono leading-none">
              SAFEROOM
            </span>
          </div>
          <p className="text-3xs text-ink-muted tracking-wider mono mt-0.5">
            AUTONOMOUS PATROL & SAFETY PLATFORM
          </p>
        </div>
      </div>

      {/* 2. Center Inset Status Modules */}
      <div className="hidden md:flex items-center gap-2">
        {/* Module A: Backend System Status */}
        <div className="hud-panel-inset px-3 py-1.5 flex items-center gap-2.5 border border-line">
          <div className="flex flex-col">
            <span className="hud-label-text text-3xs">BACKEND LINK</span>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span
                className={`status-dot ${
                  wsConnected ? 'bg-green animate-pulse-green' : 'bg-amber animate-pulse-amber'
                }`}
              />
              <span
                className={`text-2xs mono font-semibold tracking-wider ${
                  wsConnected ? 'text-green' : 'text-amber'
                }`}
              >
                {wsConnected ? 'WS LIVE' : 'OFFLINE'}
              </span>
            </div>
          </div>
        </div>

        {/* Module B: Robot Status */}
        <div className="hud-panel-inset px-3 py-1.5 flex items-center gap-2.5 border border-line">
          <div className="flex flex-col">
            <span className="hud-label-text text-3xs">ROVER STATE</span>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span
                className={`status-dot ${
                  robotStatus?.status === 'patrolling' || robotStatus?.status === 'moving'
                    ? 'bg-green animate-pulse-green'
                    : robotStatus?.status === 'emergency_stop'
                    ? 'bg-red'
                    : 'bg-cyan'
                }`}
              />
              <span className="text-2xs mono font-bold text-ink tracking-wider uppercase">
                {robotStatus?.status || 'IDLE'}
              </span>
            </div>
          </div>
          <Radio className="w-3.5 h-3.5 text-ink-muted" />
        </div>
      </div>

      {/* 3. Right Status: Theme Toggle, Clock & Active Alerts */}
      <div className="flex items-center gap-2">
        {/* Theme Toggle Button */}
        <button
          onClick={toggleTheme}
          className="hud-panel-inset px-2.5 py-1.5 flex items-center gap-2 border border-line hover:border-line-strong text-ink-muted hover:text-ink transition-colors cursor-pointer"
          title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Theme`}
          aria-label={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Theme`}
        >
          {theme === 'dark' ? (
            <Sun className="w-3.5 h-3.5 text-amber" />
          ) : (
            <Moon className="w-3.5 h-3.5 text-cyan" />
          )}
          <span className="text-3xs mono font-bold hidden sm:inline text-ink">
            {theme === 'dark' ? 'LIGHT' : 'DARK'}
          </span>
        </button>

        {/* Time & Date */}
        <div className="hud-panel-inset px-3 py-1.5 flex flex-col items-center justify-center border border-line min-w-[100px]">
          <span className="text-xs mono font-bold text-ink tracking-wider leading-none tabular-nums">
            {formatClock(currentDate)}
          </span>
          <span className="text-3xs mono text-ink-muted tracking-wider mt-0.5">
            {formatDate(currentDate)}
          </span>
        </div>

        {/* Active Alerts Box - Pops in Red only when alertCount > 0 */}
        <button
          onClick={onAlertClick}
          className={`hud-panel px-3 py-1.5 flex items-center gap-2.5 cursor-pointer transition-all ${
            alertCount > 0
              ? 'border-red bg-red/10 hud-glow-red hover:bg-red/20'
              : 'border-line hover:border-line-strong'
          }`}
          aria-label={`${alertCount} active alerts`}
        >
          <span
            className={`text-xl mono font-black leading-none tabular-nums ${
              alertCount > 0 ? 'text-red' : 'text-ink-muted'
            }`}
          >
            {alertCount}
          </span>
          <div className="flex flex-col items-start leading-tight">
            <span
              className={`text-3xs mono font-bold tracking-wider ${
                alertCount > 0 ? 'text-red' : 'text-ink-muted'
              }`}
            >
              ALERTS
            </span>
          </div>
        </button>
      </div>
    </header>
  );
}
