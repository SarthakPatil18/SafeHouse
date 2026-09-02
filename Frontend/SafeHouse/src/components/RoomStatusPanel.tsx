import { useDashboard } from '@/context/DashboardContext';
import { RoomCard } from './RoomCard';
import { LayoutGrid } from 'lucide-react';

interface RoomStatusPanelProps {
  selectedRoom: string | null;
  onSelectRoom: (roomId: string) => void;
  onViewAllRooms?: () => void;
}

export function RoomStatusPanel({ selectedRoom, onSelectRoom, onViewAllRooms }: RoomStatusPanelProps) {
  const { rooms, latestReadings, activeAlerts } = useDashboard();

  return (
    <div className="hud-panel flex flex-col h-full select-none">
      {/* Header */}
      <div className="hud-header">
        <span className="hud-section-title">ROOM STATUS</span>
        <span className="text-3xs mono text-ink-muted">{rooms.length} ZONES CONFIGURED</span>
      </div>

      {/* Room list */}
      <div className="p-3 space-y-2.5 overflow-y-auto scrollbar-thin flex-1">
        {rooms.length === 0 ? (
          <div className="py-8 text-center text-xs mono text-ink-muted">
            NO ROOMS CONFIGURED
          </div>
        ) : (
          rooms.map((room) => {
            const hasAlert = activeAlerts.some((a) => a.room_id === room.id);
            return (
              <RoomCard
                key={room.id}
                room={room}
                reading={latestReadings[room.id]}
                hasActiveAlert={hasAlert}
                isSelected={selectedRoom === room.id}
                onClick={() => onSelectRoom(room.id)}
              />
            );
          })
        )}
      </div>

      {/* Footer: VIEW ALL ROOMS */}
      {onViewAllRooms && (
        <div className="p-3 border-t border-line shrink-0">
          <button
            onClick={onViewAllRooms}
            className="w-full btn-hud btn-hud-green flex items-center justify-center gap-2 py-2 text-2xs mono font-bold tracking-widest cursor-pointer"
          >
            <LayoutGrid className="w-3.5 h-3.5" />
            <span>VIEW ALL ROOMS</span>
          </button>
        </div>
      )}
    </div>
  );
}
