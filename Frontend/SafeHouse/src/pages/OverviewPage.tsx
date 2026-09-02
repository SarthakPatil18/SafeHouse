import { useState } from 'react';
import { RoomStatusPanel } from '@/components/RoomStatusPanel';
import { SensorCards } from '@/components/SensorCard';
import { AlertPanel } from '@/components/AlertPanel';
import { CommandConsole } from '@/components/CommandConsole';
import { AlertDetail } from '@/components/AlertDetail';
import { useDashboard } from '@/context/DashboardContext';

interface OverviewPageProps {
  onNavigateAlerts: () => void;
}

export function OverviewPage({ onNavigateAlerts }: OverviewPageProps) {
  const { alerts, activeRoomId, setActiveRoomId, acknowledgeAlert } = useDashboard();
  const [selectedAlert, setSelectedAlert] = useState<number | null>(null);

  const handleSelectRoom = (roomId: string) => {
    setActiveRoomId(activeRoomId === roomId ? null : roomId);
  };

  const handleSelectAlert = (alertId: number) => {
    setSelectedAlert(alertId);
    const alert = alerts.find((a) => a.id === alertId);
    if (alert && alert.room_id) {
      setActiveRoomId(alert.room_id);
    }
  };

  return (
    <div className="space-y-3">
      {/* Subheader Toolbar */}
      <div className="flex items-center justify-between pb-1">
        <div className="flex items-center gap-3">
          <span className="hud-section-title text-sm">SYSTEM OVERVIEW</span>
          <span className="text-3xs mono text-ink-muted hidden sm:inline">
            LIVE ENVIRONMENTAL MATRICES & TELEMETRY STREAM
          </span>
        </div>
      </div>

      {/* 1. Live Telemetry Matrices AT TOP */}
      <SensorCards />

      {/* 2. Room Status, Active Alerts & AI Command Console */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 items-stretch">
        {/* Left Column: Room Status Matrix */}
        <div className="lg:col-span-4 min-h-[380px]">
          <RoomStatusPanel
            selectedRoom={activeRoomId}
            onSelectRoom={handleSelectRoom}
            onViewAllRooms={onNavigateAlerts}
          />
        </div>

        {/* Right Column: Alerts & AI Command Console */}
        <div className="lg:col-span-8 flex flex-col gap-3">
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-3 flex-1">
            <AlertPanel onViewAll={onNavigateAlerts} onSelectAlert={handleSelectAlert} />
            <CommandConsole onSelectAlert={handleSelectAlert} />
          </div>
        </div>
      </div>

      {/* Alert Detail Modal */}
      {selectedAlert !== null && (
        <AlertDetail
          alertId={selectedAlert}
          onClose={() => setSelectedAlert(null)}
          onAcknowledge={(id) => acknowledgeAlert(id)}
        />
      )}
    </div>
  );
}
