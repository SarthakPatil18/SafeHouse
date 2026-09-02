import {
  Crosshair,
  Route,
  AlertTriangle,
  History,
  X,
  ChevronRight,
  Radio,
  Sun,
  Moon,
  Battery,
  Shield,
  AlertOctagon,
} from 'lucide-react';
import { useDashboard } from '@/context/DashboardContext';
import { useTheme } from '@/context/ThemeContext';
import { formatRoom } from '@/utils/style';
import type { PageId } from '@/App';

interface SidebarProps {
  currentPage: PageId;
  onNavigate: (page: PageId) => void;
  isOpen: boolean;
  onClose: () => void;
}

const NAV_ITEMS: { id: PageId; label: string; icon: typeof Crosshair }[] = [
  { id: 'overview', label: 'Overview', icon: Crosshair },
  { id: 'patrol', label: 'Patrol & Map', icon: Route },
  { id: 'alerts', label: 'Alerts', icon: AlertTriangle },
  { id: 'history', label: 'History & Logs', icon: History },
];

export function Sidebar({ currentPage, onNavigate, isOpen, onClose }: SidebarProps) {
  const { robotStatus, activeAlerts, wsConnected } = useDashboard();
  const { theme, toggleTheme } = useTheme();

  const battery = robotStatus?.battery_level ?? 100;
  const batteryColor =
    battery > 50 ? 'bg-green' : battery > 20 ? 'bg-amber' : 'bg-red';
  const statusStr = robotStatus?.status || 'idle';
  const isPatrolling = statusStr === 'patrolling' || statusStr === 'moving';

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div className="fixed inset-0 bg-black/60 z-40 lg:hidden backdrop-blur-xs" onClick={onClose} />
      )}

      <aside
        className={`fixed lg:static inset-y-0 left-0 z-50 w-[240px] bg-base-surface border-r border-line flex flex-col shrink-0 transition-transform duration-200 select-none overflow-y-auto scrollbar-thin ${
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Mobile close */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-line lg:hidden">
          <span className="text-xs font-bold text-ink uppercase tracking-wider">Navigation</span>
          <button onClick={onClose} className="text-ink-muted hover:text-ink cursor-pointer">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation Menu */}
        <div className="p-3">
          <span className="text-3xs font-bold text-ink-muted uppercase tracking-wider px-2 block mb-2">
            Mission Navigation
          </span>
          <nav className="space-y-1">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = currentPage === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    onNavigate(item.id);
                    onClose();
                  }}
                  className={`w-full hud-nav-item ${isActive ? 'active' : ''}`}
                >
                  <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-green' : 'text-ink-muted'}`} />
                  <span className="flex-1 text-left font-medium">{item.label}</span>
                  {item.id === 'alerts' && activeAlerts.length > 0 ? (
                    <span className="w-5 h-5 rounded-full bg-red text-white font-bold text-3xs flex items-center justify-center tabular-nums">
                      {activeAlerts.length}
                    </span>
                  ) : (
                    <ChevronRight className="w-3.5 h-3.5 opacity-40" />
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        <div className="border-t border-line/60 mx-3 my-1" />

        {/* Robot Device Status Card */}
        <div className="p-3 space-y-3">
          <span className="text-3xs font-bold text-ink-muted uppercase tracking-wider px-1 block">
            Rover Telemetry
          </span>

          <div className="hud-panel-inset p-3 space-y-2.5">
            {/* Status & Location */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span
                  className={`status-dot ${
                    isPatrolling
                      ? 'bg-green animate-pulse-green'
                      : statusStr === 'emergency_stop'
                      ? 'bg-red'
                      : 'bg-cyan'
                  }`}
                />
                <span className="text-xs font-bold uppercase tracking-wider text-ink">
                  {statusStr}
                </span>
              </div>
              <span className="text-3xs mono text-ink-muted">
                {robotStatus?.device_id || 'rover_01'}
              </span>
            </div>

            <p className="text-2xs text-ink-muted">
              Location:{' '}
              <strong className="text-ink font-semibold">
                {robotStatus?.current_room_id
                  ? formatRoom(robotStatus.current_room_id)
                  : 'Docked (Base)'}
              </strong>
            </p>

            {/* Battery bar */}
            <div>
              <div className="flex items-center justify-between text-3xs font-semibold mb-1">
                <span className="text-ink-muted flex items-center gap-1">
                  <Battery className="w-3 h-3 text-ink-muted" /> Battery
                </span>
                <span className="text-ink mono">{Math.round(battery)}%</span>
              </div>
              <div className="h-1.5 bg-base rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-300 ${batteryColor}`}
                  style={{ width: `${Math.max(0, Math.min(100, battery))}%` }}
                />
              </div>
            </div>

            {/* Obstacle status */}
            <div className="pt-2 border-t border-line/60 flex items-center justify-between text-3xs">
              <span className="text-ink-muted flex items-center gap-1">
                <AlertOctagon className="w-3 h-3 text-ink-muted" /> Obstacle
              </span>
              <span
                className={`font-semibold ${
                  robotStatus?.has_obstacle ? 'text-red font-bold animate-pulse' : 'text-green'
                }`}
              >
                {robotStatus?.has_obstacle ? 'DETECTED' : 'CLEAR'}
              </span>
            </div>
          </div>
        </div>

        {/* Footer & Quick Controls */}
        <div className="mt-auto p-3 border-t border-line/60 space-y-2">
          {/* Theme switcher */}
          <button
            onClick={toggleTheme}
            className="w-full hud-panel-inset px-3 py-2 flex items-center justify-between hover:bg-base-elevated transition-colors cursor-pointer text-xs"
            title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
          >
            <div className="flex items-center gap-2 text-ink">
              {theme === 'dark' ? (
                <Sun className="w-3.5 h-3.5 text-amber" />
              ) : (
                <Moon className="w-3.5 h-3.5 text-cyan" />
              )}
              <span className="font-medium">Theme</span>
            </div>
            <span className="text-3xs font-bold text-green uppercase tracking-wider">
              {theme}
            </span>
          </button>

          {/* WebSocket status pill */}
          <div className="hud-panel-inset px-3 py-2 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2 text-ink">
              <Radio className="w-3.5 h-3.5 text-cyan animate-pulse shrink-0" />
              <span className="font-medium text-2xs">Backend Stream</span>
            </div>
            <span
              className={`text-3xs mono font-bold ${
                wsConnected ? 'text-green' : 'text-amber'
              }`}
            >
              {wsConnected ? 'CONNECTED' : 'CONNECTING'}
            </span>
          </div>
        </div>
      </aside>
    </>
  );
}
