// System Configuration and Projection Helpers

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string) || 'http://localhost:8000/api';

export const WS_DASHBOARD_URL: string =
  (import.meta.env.VITE_WS_URL as string) || 'ws://localhost:8000/ws/dashboard';

// Blueprint Map Viewport Dimensions
export const MAP_DIMENSIONS = { width: 570, height: 310 };

// Normalization boundaries for mapping arbitrary backend room (x, y) coordinates into blueprint SVG space
export const MAP_BOUNDS = {
  minX: 45,
  maxX: 525,
  minY: 50,
  maxY: 275,
};

/** Convert room grid (x, y) into blueprint SVG coordinates */
export function roomToSvgCoord(
  x: number,
  y: number,
  allRooms: { x: number; y: number }[]
): { x: number; y: number } {
  if (allRooms.length === 0) return { x: 100, y: 100 };
  const xs = allRooms.map((r) => r.x);
  const ys = allRooms.map((r) => r.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  const spanX = maxX - minX || 1;
  const spanY = maxY - minY || 1;

  const normalizedX = (x - minX) / spanX;
  const normalizedY = (y - minY) / spanY;

  return {
    x: MAP_BOUNDS.minX + normalizedX * (MAP_BOUNDS.maxX - MAP_BOUNDS.minX - 110),
    y: MAP_BOUNDS.minY + normalizedY * (MAP_BOUNDS.maxY - MAP_BOUNDS.minY - 88),
  };
}
