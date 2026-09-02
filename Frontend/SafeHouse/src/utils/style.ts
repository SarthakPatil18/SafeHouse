import type { AlertSeverity, AlertStatus } from '@/types';

export function severityColor(severity: AlertSeverity): string {
  const s = String(severity).toLowerCase();
  switch (s) {
    case 'critical':
    case 'high':
      return 'text-red';
    case 'warning':
    case 'medium':
      return 'text-amber';
    case 'low':
    case 'info':
    default:
      return 'text-ink-muted';
  }
}

export function severityBg(severity: AlertSeverity): string {
  const s = String(severity).toLowerCase();
  switch (s) {
    case 'critical':
    case 'high':
      return 'bg-red-tint text-red';
    case 'warning':
    case 'medium':
      return 'bg-amber-tint text-amber';
    case 'low':
    case 'info':
    default:
      return 'bg-base-hover text-ink-muted';
  }
}

export function alertStatusColor(status: AlertStatus): string {
  const s = String(status).toLowerCase();
  switch (s) {
    case 'active':
      return 'text-red';
    case 'acknowledged':
      return 'text-amber';
    case 'resolved':
      return 'text-green';
    default:
      return 'text-ink-muted';
  }
}

export function severityDot(severity: AlertSeverity): string {
  const s = String(severity).toLowerCase();
  switch (s) {
    case 'critical':
    case 'high':
      return 'bg-red';
    case 'warning':
    case 'medium':
      return 'bg-amber';
    default:
      return 'bg-ink-faint';
  }
}

export function formatTime(ts: string | number): string {
  if (!ts) return '—';
  const d = new Date(ts);
  if (isNaN(d.getTime())) return String(ts);
  return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

export function formatTimeSec(ts: string | number): string {
  if (!ts) return '—';
  const d = new Date(ts);
  if (isNaN(d.getTime())) return String(ts);
  return d.toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function formatRoom(roomId: string | number | null | undefined): string {
  if (!roomId) return 'UNKNOWN';
  const str = String(roomId).trim();
  const digitMatch = str.match(/\d+/);
  if (digitMatch) {
    return `ROOM ${digitMatch[0].padStart(2, '0')}`;
  }
  return str.toUpperCase();
}

export function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}m ${s}s`;
}
