import { useState, useCallback, useRef, useMemo } from 'react';
import { RotateCcw, Crosshair, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import { useDashboard } from '@/context/DashboardContext';
import { useTheme } from '@/context/ThemeContext';
import { formatRoom } from '@/utils/style';
import type { Room } from '@/types';

interface PatrolMapProps {
  selectedRoom: string | null;
  onSelectRoom: (roomId: string) => void;
}

export function PatrolMap({ selectedRoom, onSelectRoom }: PatrolMapProps) {
  const { rooms, robotStatus, latestReadings, activeAlerts } = useDashboard();
  const { theme } = useTheme();
  const isLight = theme === 'light';

  // Theme-aware blueprint colors
  const cGreen = isLight ? '#0D9468' : '#9CFF32';
  const cCyan = isLight ? '#0284C7' : '#35D9E8';
  const cAmber = isLight ? '#D97706' : '#F2B84B';
  const cRed = isLight ? '#DC2626' : '#FF3B30';
  const cInk = isLight ? '#0C181B' : '#DDE8E8';
  const cInkMuted = isLight ? '#4A676E' : '#718385';
  const cBg = isLight ? '#F0F5F7' : '#03080A';
  const cGrid = isLight ? '#D8E4E7' : '#08181C';
  const cPerimeter = isLight ? '#B6CBD1' : '#0C262C';
  const cDefaultBorder = isLight ? '#C5D7DC' : '#16363E';
  const cBadgeBg = isLight ? '#E4EEF1' : '#0A181C';
  const cRoverBody = isLight ? '#E3EDF0' : '#040A0C';
  const cRoverWheel = isLight ? '#C6D8DC' : '#0B1619';
  const cCompassBg = isLight ? '#E8ECEF' : '#060E10';
  const cCompassBorder = isLight ? '#9EBEC5' : '#1F4046';

  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const svgRef = useRef<SVGSVGElement>(null);
  const dragRef = useRef<{
    startX: number;
    startY: number;
    startPanX: number;
    startPanY: number;
  } | null>(null);

  // Layout rooms dynamically across blueprint 570x310 viewport
  const positionedRooms = useMemo(() => {
    if (rooms.length === 0) {
      // Fallback placeholder rooms if backend has none yet
      return [
        {
          id: 'room_1',
          name: 'Server Room',
          type: 'infrastructure',
          x: 45,
          y: 50,
          w: 110,
          h: 88,
          enabled: true,
          baseline: {
            gas_mq135_max: 80,
            gas_mq2_max: 80,
            motion_mode: 'expect_presence' as const,
            no_motion_timeout_seconds: 28800,
          },
        },
        {
          id: 'room_2',
          name: 'Storage Area',
          type: 'storage',
          x: 230,
          y: 50,
          w: 110,
          h: 88,
          enabled: true,
          baseline: {
            gas_mq135_max: 80,
            gas_mq2_max: 80,
            motion_mode: 'expect_presence' as const,
            no_motion_timeout_seconds: 28800,
          },
        },
        {
          id: 'room_3',
          name: 'Main Concourse',
          type: 'hall',
          x: 415,
          y: 50,
          w: 110,
          h: 88,
          enabled: true,
          baseline: {
            gas_mq135_max: 80,
            gas_mq2_max: 80,
            motion_mode: 'expect_presence' as const,
            no_motion_timeout_seconds: 28800,
          },
        },
        {
          id: 'room_4',
          name: 'Workshop',
          type: 'maintenance',
          x: 230,
          y: 185,
          w: 110,
          h: 88,
          enabled: true,
          baseline: {
            gas_mq135_max: 80,
            gas_mq2_max: 80,
            motion_mode: 'expect_presence' as const,
            no_motion_timeout_seconds: 28800,
          },
        },
      ];
    }

    // Assign grid positions based on rooms array
    const defaultPositions = [
      { x: 45, y: 50 },
      { x: 230, y: 50 },
      { x: 415, y: 50 },
      { x: 230, y: 185 },
      { x: 45, y: 185 },
      { x: 415, y: 185 },
    ];

    return rooms.map((r: Room, idx: number) => {
      const pos = defaultPositions[idx % defaultPositions.length];
      return {
        ...r,
        x: r.x && r.x > 10 ? r.x : pos.x,
        y: r.y && r.y > 10 ? r.y : pos.y,
        w: 110,
        h: 88,
      };
    });
  }, [rooms]);

  // Determine current robot position in SVG coordinates
  const currentRoomObj = positionedRooms.find(
    (r) => r.id === robotStatus?.current_room_id
  ) || positionedRooms[0];

  const robotSvgX = currentRoomObj ? currentRoomObj.x + currentRoomObj.w / 2 : 285;
  const robotSvgY = currentRoomObj ? currentRoomObj.y + currentRoomObj.h / 2 : 94;

  const handleFitView = useCallback(() => {
    setPan({ x: 0, y: 0 });
    setZoom(1);
  }, []);

  const handleCenterRover = useCallback(() => {
    const vbW = 570;
    const vbH = 310;
    setPan({
      x: -(robotSvgX - vbW / 2),
      y: -(robotSvgY - vbH / 2),
    });
    setZoom(1.3);
  }, [robotSvgX, robotSvgY]);

  const handleReset = useCallback(() => {
    setPan({ x: 0, y: 0 });
    setZoom(1);
  }, []);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (e.button !== 0) return;
      dragRef.current = {
        startX: e.clientX,
        startY: e.clientY,
        startPanX: pan.x,
        startPanY: pan.y,
      };
    },
    [pan]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!dragRef.current) return;
      setPan({
        x: dragRef.current.startPanX + (e.clientX - dragRef.current.startX) / zoom,
        y: dragRef.current.startPanY + (e.clientY - dragRef.current.startY) / zoom,
      });
    },
    [zoom]
  );

  const handleMouseUp = useCallback(() => {
    dragRef.current = null;
  }, []);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    setZoom((z) => Math.min(Math.max(z + (e.deltaY > 0 ? -0.06 : 0.06), 0.7), 1.6));
  }, []);

  const vbW = 570;
  const vbH = 310;
  const cx = vbW / 2 + pan.x;
  const cy = vbH / 2 + pan.y;

  return (
    <div className="hud-panel relative overflow-hidden flex flex-col h-full select-none min-h-0">
      {/* Header */}
      <div className="hud-header">
        <div className="flex items-center gap-2">
          <span className="hud-section-title">LIVE FACILITY MAP</span>
          <span className="text-3xs mono text-ink-muted hidden sm:inline">
            DYNAMIC TOPOLOGY · REAL BACKEND LINK
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-3xs mono text-ink-muted">
            {robotStatus?.current_room_id
              ? `ROVER AT ${formatRoom(robotStatus.current_room_id)}`
              : 'ROVER STATUS: STANDBY'}
          </span>
        </div>
      </div>

      {/* Map Controls */}
      <div className="absolute top-10 right-2.5 flex flex-col gap-1 z-10">
        {[
          {
            icon: Maximize2,
            action: handleFitView,
            title: 'Fit View',
            cls: 'text-cyan hover:border-cyan hover:bg-cyan/10',
          },
          {
            icon: ZoomIn,
            action: () => setZoom((z) => Math.min(z + 0.15, 1.6)),
            title: 'Zoom In',
            cls: 'text-ink-muted hover:text-ink hover:border-line-strong',
          },
          {
            icon: ZoomOut,
            action: () => setZoom((z) => Math.max(z - 0.15, 0.7)),
            title: 'Zoom Out',
            cls: 'text-ink-muted hover:text-ink hover:border-line-strong',
          },
        ].map(({ icon: Icon, action, title, cls }) => (
          <button
            key={title}
            onClick={action}
            className={`w-6 h-6 flex items-center justify-center bg-base-elevated border border-line transition-colors cursor-pointer ${cls}`}
            title={title}
          >
            <Icon className="w-3 h-3" />
          </button>
        ))}
        <div className="h-px bg-line my-0.5" />
        <button
          onClick={handleCenterRover}
          className="w-6 h-6 flex items-center justify-center bg-base-elevated border border-line text-green hover:border-green hover:bg-green/10 transition-colors cursor-pointer"
          title="Center on Rover"
        >
          <Crosshair className="w-3 h-3" />
        </button>
        <button
          onClick={handleReset}
          className="w-6 h-6 flex items-center justify-center bg-base-elevated border border-line text-ink-muted hover:text-ink hover:border-line-strong transition-colors cursor-pointer"
          title="Reset View"
        >
          <RotateCcw className="w-3 h-3" />
        </button>
      </div>

      {/* SVG Canvas */}
      <div
        className="relative flex-1 overflow-hidden"
        style={{
          backgroundColor: cBg,
          cursor: dragRef.current ? 'grabbing' : 'grab',
          minHeight: 0,
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
      >
        <svg
          ref={svgRef}
          viewBox={`${cx - vbW / (2 * zoom)} ${cy - vbH / (2 * zoom)} ${vbW / zoom} ${
            vbH / zoom
          }`}
          className="w-full h-full"
          preserveAspectRatio="xMidYMid meet"
        >
          <defs>
            <pattern id="bpGrid" width="18" height="18" patternUnits="userSpaceOnUse">
              <path d="M 18 0 L 0 0 0 18" fill="none" stroke={cGrid} strokeWidth="0.5" />
            </pattern>
            <radialGradient id="sonarGrad" cx="50%" cy="100%" r="100%">
              <stop offset="0%" stopColor={cGreen} stopOpacity="0.4" />
              <stop offset="60%" stopColor={cGreen} stopOpacity="0.12" />
              <stop offset="100%" stopColor={cGreen} stopOpacity="0" />
            </radialGradient>
          </defs>

          {/* Background */}
          <rect
            x={cx - vbW / (2 * zoom)}
            y={cy - vbH / (2 * zoom)}
            width={vbW / zoom}
            height={vbH / zoom}
            fill={cBg}
          />
          <rect
            x={cx - vbW / (2 * zoom)}
            y={cy - vbH / (2 * zoom)}
            width={vbW / zoom}
            height={vbH / zoom}
            fill="url(#bpGrid)"
          />

          {/* Facility perimeter */}
          <rect
            x="25"
            y="25"
            width="520"
            height="260"
            fill="none"
            stroke={cPerimeter}
            strokeWidth="0.8"
            strokeDasharray="4 4"
          />

          {/* Route corridor connections between adjacent rooms */}
          <line
            x1="155"
            y1="94"
            x2="230"
            y2="94"
            stroke={cCyan}
            strokeWidth="1.6"
            strokeDasharray="4 3"
            opacity="0.85"
          />
          <line
            x1="340"
            y1="94"
            x2="415"
            y2="94"
            stroke={cCyan}
            strokeWidth="1.6"
            strokeDasharray="4 3"
            opacity="0.85"
          />
          <line
            x1="285"
            y1="138"
            x2="285"
            y2="185"
            stroke={cCyan}
            strokeWidth="1.6"
            strokeDasharray="4 3"
            opacity="0.85"
          />

          {/* Render dynamic rooms */}
          {positionedRooms.map((br, idx) => {
            const isRobotHere = robotStatus?.current_room_id === br.id;
            const isSelected = selectedRoom === br.id;
            const hasHazard = activeAlerts.some((a) => a.room_id === br.id);

            const borderColor =
              isRobotHere || isSelected
                ? cGreen
                : hasHazard
                ? cRed
                : cDefaultBorder;

            const roomBg = isRobotHere
              ? isLight
                ? 'rgba(13,148,104,0.08)'
                : 'rgba(156,255,50,0.06)'
              : isSelected
              ? isLight
                ? 'rgba(2,132,199,0.08)'
                : 'rgba(53,217,232,0.08)'
              : isLight
              ? '#FFFFFF'
              : '#050D10';

            return (
              <g
                key={br.id}
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectRoom(br.id);
                }}
                className="cursor-pointer"
              >
                <rect
                  x={br.x}
                  y={br.y}
                  width={br.w}
                  height={br.h}
                  fill={roomBg}
                  stroke={borderColor}
                  strokeWidth={isRobotHere || isSelected ? 1.6 : 1}
                />
                <rect
                  x={br.x + 3}
                  y={br.y + 3}
                  width={br.w - 6}
                  height={br.h - 6}
                  fill="none"
                  stroke={borderColor}
                  strokeWidth="0.4"
                  strokeDasharray="2 3"
                  opacity={0.5}
                />
                {/* Waypoint badge */}
                <rect
                  x={br.x + 6}
                  y={br.y + 6}
                  width="28"
                  height="11"
                  fill={cBadgeBg}
                  stroke={borderColor}
                  strokeWidth="0.5"
                  rx="1"
                />
                <text
                  x={br.x + 20}
                  y={br.y + 14.5}
                  textAnchor="middle"
                  fill={borderColor}
                  fontSize="6.5"
                  fontFamily="'JetBrains Mono', monospace"
                  fontWeight="bold"
                >
                  W0{idx + 1}
                </text>
                {/* Room label */}
                <text
                  x={br.x + br.w / 2}
                  y={br.y + (isRobotHere ? 38 : br.h / 2 + 3)}
                  textAnchor="middle"
                  fill={isRobotHere ? cGreen : hasHazard ? cRed : cInk}
                  fontSize="10"
                  fontFamily="'JetBrains Mono', monospace"
                  fontWeight="bold"
                  letterSpacing="0.08em"
                >
                  {formatRoom(br.id)}
                </text>
                {/* Room name / type */}
                {!isRobotHere && (
                  <text
                    x={br.x + br.w / 2}
                    y={br.y + br.h / 2 + 15}
                    textAnchor="middle"
                    fill={cInkMuted}
                    fontSize="7"
                    fontFamily="'JetBrains Mono', monospace"
                  >
                    {br.name || br.type}
                  </text>
                )}
              </g>
            );
          })}

          {/* Rover Graphic Positioned on Current Room */}
          <g transform={`translate(${robotSvgX}, ${robotSvgY})`}>
            <path
              d="M -26,-4 C -26,-28 26,-28 26,-4 Z"
              fill="url(#sonarGrad)"
              stroke={cGreen}
              strokeWidth="0.8"
              opacity="0.8"
            />
            <path
              d="M -18,-4 C -18,-20 18,-20 18,-4"
              fill="none"
              stroke={cGreen}
              strokeWidth="0.6"
              strokeDasharray="2 2"
            />
            <g transform="translate(-12, -7)">
              <rect
                x="2"
                y="2"
                width="20"
                height="10"
                rx="2"
                fill={cRoverBody}
                stroke={cGreen}
                strokeWidth="1.2"
              />
              <circle cx="4" cy="12" r="3" fill={cRoverWheel} stroke={cGreen} strokeWidth="1" />
              <circle cx="20" cy="12" r="3" fill={cRoverWheel} stroke={cGreen} strokeWidth="1" />
              <circle cx="12" cy="2" r="2" fill={cGreen} />
            </g>
          </g>

          {/* Compass */}
          <g transform="translate(520, 48)">
            <circle
              cx="0"
              cy="0"
              r="10"
              fill={cCompassBg}
              stroke={cCompassBorder}
              strokeWidth="0.8"
            />
            <text
              x="0"
              y="3"
              textAnchor="middle"
              fill={cInkMuted}
              fontSize="7"
              fontFamily="'JetBrains Mono', monospace"
              fontWeight="bold"
            >
              N
            </text>
            <polygon points="0,-9 -2,-4 2,-4" fill={cGreen} />
            <polygon points="0,9 -2,4 2,4" fill={cCompassBorder} />
          </g>
        </svg>
      </div>
    </div>
  );
}
