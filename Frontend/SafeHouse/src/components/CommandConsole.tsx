import { useState, useRef, useEffect, useCallback } from 'react';
import { ArrowRight, Mic, Volume2, VolumeX, Loader2 } from 'lucide-react';
import { useDashboard } from '@/context/DashboardContext';
import { useSpeechRecognition, useSpeechSynthesis, type MicState } from '@/hooks/useSpeech';
import type { ConsoleMessage } from '@/types';

interface CommandConsoleProps {
  onSelectAlert?: (alertId: number) => void;
}

const HINTS = [
  'Start patrol',
  'Stop rover',
  'Go to room 2',
  'Check room 1',
  'Get status',
  'Get alerts',
];

function micLabel(state: MicState, isSending: boolean, acceptedFlash: boolean): string {
  if (isSending)              return '◌ SENDING TO AI...';
  if (state === 'listening')   return '● LISTENING...';
  if (state === 'processing')  return '◌ PROCESSING...';
  if (state === 'error')       return '⚠ VOICE ERROR';
  if (state === 'unsupported') return 'NO MIC';
  if (acceptedFlash)           return '✓ PROCESSED';
  return 'SPEAK COMMAND...';
}

function formatBackendResponse(res: any): { text: string; kind: ConsoleMessage['kind'] } {
  if (!res) {
    return { text: 'Command processed successfully by backend.', kind: 'success' };
  }

  // Handle various return payload shapes from /api/ai/command
  if (typeof res === 'string') {
    return { text: res, kind: 'info' };
  }

  if (res.message) {
    return { text: res.message, kind: 'info' };
  }

  if (res.result) {
    if (typeof res.result === 'string') return { text: res.result, kind: 'success' };
    if (res.result.message) return { text: res.result.message, kind: 'success' };
    return { text: JSON.stringify(res.result), kind: 'success' };
  }

  if (res.status) {
    const s = res.status;
    return {
      text: `Rover ${s.device_id || 'RVR-01'} is ${s.status || 'idle'}. Battery: ${s.battery_level ?? 100}%. Obstacle: ${s.has_obstacle ? 'YES' : 'NONE'}.`,
      kind: 'info',
    };
  }

  if (res.alerts && Array.isArray(res.alerts)) {
    return {
      text: `Retrieved ${res.alerts.length} alert(s) from safety monitoring.`,
      kind: res.alerts.length > 0 ? 'warning' : 'success',
    };
  }

  if (res.rooms && Array.isArray(res.rooms)) {
    return {
      text: `Found ${res.rooms.length} configured zone(s).`,
      kind: 'info',
    };
  }

  if (res.intent) {
    return {
      text: `Executed intent: ${res.intent}`,
      kind: 'success',
    };
  }

  return { text: JSON.stringify(res), kind: 'info' };
}

export function CommandConsole({ onSelectAlert: _onSelectAlert }: CommandConsoleProps) {
  const { sendAiCommand } = useDashboard();
  const [messages, setMessages] = useState<ConsoleMessage[]>([
    {
      id: 'sys-init',
      source: 'SYS',
      text: 'AI Natural Language Command Interface active. Direct link to backend /api/ai/command.',
      timestamp: Date.now(),
      kind: 'info',
    },
  ]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [acceptedFlash, setAcceptedFlash] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const { enabled: voiceEnabled, toggle: toggleVoice, speak } = useSpeechSynthesis();

  const executeCommand = useCallback(
    async (raw: string) => {
      const trimmed = raw.trim();
      if (!trimmed || isSending) return;

      const userMsg: ConsoleMessage = {
        id: `you-${Date.now()}`,
        source: 'YOU',
        text: `"${trimmed}"`,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsSending(true);

      try {
        // Send raw text to backend /api/ai/command per Section 7
        const res = await sendAiCommand(trimmed);
        const { text: responseText, kind } = formatBackendResponse(res);

        const sysMsg: ConsoleMessage = {
          id: `sys-${Date.now()}`,
          source: 'SYS',
          text: responseText,
          timestamp: Date.now(),
          kind,
        };
        setMessages((prev) => [...prev, sysMsg]);
        setAcceptedFlash(true);
        setTimeout(() => setAcceptedFlash(false), 3000);

        if (voiceEnabled) {
          speak(responseText);
        }
      } catch (err: unknown) {
        const errorMsg =
          err instanceof Error ? err.message : 'Failed to execute command on backend.';
        const errSysMsg: ConsoleMessage = {
          id: `err-${Date.now()}`,
          source: 'ERR',
          text: errorMsg,
          timestamp: Date.now(),
          kind: 'critical',
        };
        setMessages((prev) => [...prev, errSysMsg]);
        if (voiceEnabled) {
          speak(errorMsg);
        }
      } finally {
        setIsSending(false);
      }
    },
    [sendAiCommand, voiceEnabled, speak, isSending]
  );

  const { micState, start, stop } = useSpeechRecognition((transcript) => {
    executeCommand(transcript);
  });

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = () => {
    if (!input.trim() || isSending) return;
    executeCommand(input.trim());
    setInput('');
  };

  const buttonLabel = micLabel(micState, isSending, acceptedFlash);

  const micBtnClass = isSending
    ? 'border-cyan bg-cyan/10 text-cyan animate-pulse'
    : micState === 'listening'
    ? 'border-green bg-green/20 text-green animate-pulse'
    : micState === 'processing'
    ? 'border-amber bg-amber/10 text-amber'
    : micState === 'error'
    ? 'border-red bg-red/10 text-red'
    : micState === 'unsupported'
    ? 'border-line text-ink-muted opacity-50 cursor-not-allowed'
    : acceptedFlash
    ? 'border-green/60 bg-green/10 text-green'
    : 'border-green/40 bg-green/10 text-green hover:border-green hover:bg-green/15';

  return (
    <div className="hud-panel flex flex-col h-full select-none">
      {/* Header */}
      <div className="hud-header">
        <span className="hud-section-title">AI VOICE & COMMAND CONSOLE</span>
        <button
          onClick={toggleVoice}
          className={`flex items-center gap-1 text-3xs mono font-bold cursor-pointer transition-colors ${
            voiceEnabled ? 'text-green' : 'text-ink-muted hover:text-ink'
          }`}
          title="Toggle Voice Readout"
        >
          {voiceEnabled ? <Volume2 className="w-3 h-3" /> : <VolumeX className="w-3 h-3" />}
          <span className="hidden sm:inline">{voiceEnabled ? 'TTS ON' : 'TTS OFF'}</span>
        </button>
      </div>

      {/* Terminal message stream */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto scrollbar-thin p-3 bg-[var(--terminal-bg)] space-y-1.5 font-mono text-xs"
        style={{ minHeight: '130px', maxHeight: '200px' }}
      >
        {messages.map((msg) => {
          const isUser = msg.source === 'YOU';
          const isErr = msg.source === 'ERR';
          return (
            <div key={msg.id} className="flex items-start gap-2.5 leading-tight">
              <span
                className={`font-bold text-3xs w-7 shrink-0 ${
                  isUser ? 'text-cyan' : isErr ? 'text-red' : 'text-green'
                }`}
              >
                {msg.source}
              </span>
              <span
                className={`text-xs break-words min-w-0 ${
                  isUser
                    ? 'text-cyan font-semibold'
                    : isErr || msg.kind === 'critical'
                    ? 'text-red font-bold'
                    : msg.kind === 'warning'
                    ? 'text-amber'
                    : msg.kind === 'success'
                    ? 'text-ink'
                    : 'text-ink-muted'
                }`}
              >
                {msg.text}
              </span>
            </div>
          );
        })}
      </div>

      {/* Quick-command hint chips */}
      <div className="px-2.5 py-1.5 bg-[var(--hints-bg)] border-t border-line flex items-center gap-1.5 overflow-x-auto scrollbar-thin flex-wrap">
        <span className="text-3xs mono text-ink-muted shrink-0">INTENT HINTS:</span>
        {HINTS.map((hint) => (
          <button
            key={hint}
            disabled={isSending}
            onClick={() => executeCommand(hint)}
            className="px-1.5 py-0.5 bg-base-elevated border border-line hover:border-green text-3xs mono text-ink-muted hover:text-green transition-colors shrink-0 cursor-pointer disabled:opacity-40"
            style={{ borderRadius: 1 }}
          >
            {hint}
          </button>
        ))}
      </div>

      {/* Input bar */}
      <div className="p-2 border-t border-line bg-base-surface flex items-center gap-2">
        {/* Voice button */}
        <button
          onClick={() => (micState === 'listening' ? stop() : start())}
          disabled={micState === 'unsupported' || isSending}
          className={`flex items-center gap-1.5 px-2 py-1.5 border transition-all cursor-pointer shrink-0 ${micBtnClass}`}
          style={{ borderRadius: 2, minWidth: 0 }}
          title="Toggle Voice Command"
          aria-label={buttonLabel}
        >
          {isSending ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" />
          ) : (
            <Mic className="w-3.5 h-3.5 shrink-0" />
          )}
          <span className="text-3xs mono font-black tracking-widest whitespace-nowrap hidden xs:inline sm:inline">
            {buttonLabel}
          </span>
          {micState === 'listening' && (
            <span className="flex items-center gap-[2px] h-3 ml-1">
              {[4, 8, 12, 6, 10, 4].map((h, i) => (
                <span
                  key={i}
                  className="w-[2px] bg-green animate-hud-wave inline-block"
                  style={{ height: `${h}px`, animationDelay: `${i * 0.1}s` }}
                />
              ))}
            </span>
          )}
        </button>

        {/* Text input */}
        <input
          ref={inputRef}
          type="text"
          value={input}
          disabled={isSending}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          placeholder="SEND COMMAND TO /api/ai/command..."
          className="flex-1 min-w-0 bg-transparent text-xs mono text-ink placeholder:text-ink-faint focus:outline-none tracking-wider px-1"
          aria-label="Enter natural language command"
        />

        {/* Send button */}
        <button
          onClick={handleSubmit}
          disabled={!input.trim() || isSending}
          className="w-7 h-7 flex items-center justify-center border border-line hover:border-green text-ink-muted hover:text-green disabled:opacity-30 transition-colors shrink-0 cursor-pointer"
          style={{ borderRadius: 2 }}
          aria-label="Send command"
        >
          {isSending ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <ArrowRight className="w-3.5 h-3.5" />
          )}
        </button>
      </div>
    </div>
  );
}
