/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    screens: {
      xs:  '480px',
      sm:  '640px',
      md:  '768px',
      lg:  '1024px',
      xl:  '1280px',
      '2xl': '1536px',
    },
    extend: {
      borderRadius: {
        // xs sits between none and sm — used for subtle technical corners
        xs: '2px',
      },
      colors: {
        // Mission control backgrounds
        base: {
          DEFAULT: 'rgb(var(--color-base) / <alpha-value>)',
          surface: 'rgb(var(--color-base-surface) / <alpha-value>)',
          elevated: 'rgb(var(--color-base-elevated) / <alpha-value>)',
          hover: 'rgb(var(--color-base-hover) / <alpha-value>)',
        },
        // Borders — thin technical cyan-slate
        line: {
          DEFAULT: 'rgb(var(--color-line) / <alpha-value>)',
          strong: 'rgb(var(--color-line-strong) / <alpha-value>)',
          faint: 'rgb(var(--color-line-faint) / <alpha-value>)',
          accent: 'rgb(var(--color-line-accent) / <alpha-value>)',
        },
        // Primary SafeRoom neon green (dark) / cyber emerald (light)
        green: {
          DEFAULT: 'rgb(var(--color-green) / <alpha-value>)',
          dim: 'rgb(var(--color-green-dim) / <alpha-value>)',
          bright: 'rgb(var(--color-green-bright) / <alpha-value>)',
          glow: 'var(--color-green-glow)',
          tint: 'var(--color-green-tint)',
        },
        // Technical cyan — navigation, coordinates, sensors
        cyan: {
          DEFAULT: 'rgb(var(--color-cyan) / <alpha-value>)',
          dim: 'rgb(var(--color-cyan-dim) / <alpha-value>)',
          bright: 'rgb(var(--color-cyan-bright) / <alpha-value>)',
          tint: 'var(--color-cyan-tint)',
          glow: 'var(--color-cyan-glow)',
        },
        // Warning amber
        amber: {
          DEFAULT: 'rgb(var(--color-amber) / <alpha-value>)',
          dim: 'rgb(var(--color-amber-dim) / <alpha-value>)',
          glow: 'var(--color-amber-glow)',
          tint: 'var(--color-amber-tint)',
        },
        // Critical red
        red: {
          DEFAULT: 'rgb(var(--color-red) / <alpha-value>)',
          dim: 'rgb(var(--color-red-dim) / <alpha-value>)',
          glow: 'var(--color-red-glow)',
          tint: 'var(--color-red-tint)',
        },
        // Text hierarchy
        ink: {
          DEFAULT: 'rgb(var(--color-ink) / <alpha-value>)',
          muted: 'rgb(var(--color-ink-muted) / <alpha-value>)',
          faint: 'rgb(var(--color-ink-faint) / <alpha-value>)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
        '3xs': ['0.5625rem', { lineHeight: '0.875rem' }],
      },
      animation: {
        'pulse-green':      'pulse-green 2s ease-in-out infinite',
        'pulse-red':        'pulse-red 1s ease-in-out infinite',
        'pulse-amber':      'pulse-amber 1.5s ease-in-out infinite',
        'slide-in':         'slide-in 0.25s ease-out',
        'fade-in':          'fade-in 0.25s ease-out',
        'heartbeat':        'heartbeat 1.4s ease-in-out infinite',
        'telemetry-flow':   'telemetry-flow 8s linear infinite',
        'waveform':         'waveform 0.8s ease-in-out infinite alternate',
      },
      keyframes: {
        'pulse-green': {
          '0%, 100%': { opacity: '1' },
          '50%':       { opacity: '0.4' },
        },
        'pulse-red': {
          '0%, 100%': { opacity: '1' },
          '50%':       { opacity: '0.4' },
        },
        'pulse-amber': {
          '0%, 100%': { opacity: '1' },
          '50%':       { opacity: '0.5' },
        },
        'slide-in': {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to:   { opacity: '1' },
        },
        'heartbeat': {
          '0%':   { transform: 'scaleY(1)' },
          '10%':  { transform: 'scaleY(2.2)' },
          '20%':  { transform: 'scaleY(0.8)' },
          '30%':  { transform: 'scaleY(1.6)' },
          '40%':  { transform: 'scaleY(1)' },
          '100%': { transform: 'scaleY(1)' },
        },
        'telemetry-flow': {
          '0%':   { transform: 'translateY(0%)' },
          '100%': { transform: 'translateY(-50%)' },
        },
        'waveform': {
          from: { transform: 'scaleY(0.3)' },
          to:   { transform: 'scaleY(1)' },
        },
      },
    },
  },
  plugins: [],
};
