import { useRef, useState, useCallback, useEffect } from 'react';

// Minimal type declarations for Web Speech API
interface SpeechRecognitionEventLike {
  results: {
    length: number;
    [index: number]: { 0: { transcript: string }; isFinal: boolean };
  };
}

interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((e: SpeechRecognitionEventLike) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
}

type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

function getRecognitionCtor(): SpeechRecognitionCtor | null {
  if (typeof window === 'undefined') return null;
  const w = window as unknown as Record<string, unknown>;
  return (w.SpeechRecognition || w.webkitSpeechRecognition) as SpeechRecognitionCtor | null;
}

export type MicState = 'idle' | 'listening' | 'processing' | 'error' | 'unsupported';

export function useSpeechRecognition(onTranscript: (text: string) => void) {
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const [micState, setMicState] = useState<MicState>('idle');
  const isSupported = getRecognitionCtor() !== null;

  const start = useCallback(() => {
    const Ctor = getRecognitionCtor();
    if (!Ctor) {
      setMicState('unsupported');
      return;
    }

    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }

    const recognition = new Ctor();
    recognition.lang = 'en-US';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onresult = (e: SpeechRecognitionEventLike) => {
      const transcript = e.results[0]?.[0]?.transcript || '';
      setMicState('processing');
      if (transcript) {
        onTranscript(transcript);
      }
      setTimeout(() => setMicState('idle'), 800);
    };

    recognition.onerror = () => {
      setMicState('error');
      setTimeout(() => setMicState('idle'), 2000);
    };

    recognition.onend = () => {
      setMicState((prev) => (prev === 'listening' ? 'idle' : prev));
    };

    recognitionRef.current = recognition;
    recognition.start();
    setMicState('listening');
  }, [onTranscript]);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
    setMicState('idle');
  }, []);

  return { micState, start, stop, isSupported };
}

export function useSpeechSynthesis() {
  const [enabled, setEnabled] = useState(true);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const speak = useCallback(
    (text: string) => {
      if (!enabled || typeof window === 'undefined' || !window.speechSynthesis) return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.95;
      utterance.pitch = 0.9;
      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);
      window.speechSynthesis.speak(utterance);
    },
    [enabled]
  );

  const cancel = useCallback(() => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  }, []);

  const toggle = useCallback(() => setEnabled((e) => !e), []);

  useEffect(() => {
    return () => {
      if (typeof window !== 'undefined' && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  return { enabled, speak, cancel, toggle, isSpeaking };
}
