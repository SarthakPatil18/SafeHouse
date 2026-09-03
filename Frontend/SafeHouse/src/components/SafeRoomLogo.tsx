import React from 'react';

interface LogoProps {
  className?: string;
  size?: number;
}

export function SafeRoomLogo({ className = '', size = 32 }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`shrink-0 ${className}`}
    >
      <defs>
        <linearGradient id="shieldGrad" x1="24" y1="4" x2="24" y2="44" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="currentColor" stopOpacity="0.15" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0.02" />
        </linearGradient>
        <radialGradient id="radarGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#10B981" stopOpacity="0.6" />
          <stop offset="100%" stopColor="#10B981" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* Outer Protective Shield Geometry */}
      <path
        d="M24 4L39 10.5V23C39 32.5 32.6 40.8 24 44C15.4 40.8 9 32.5 9 23V10.5L24 4Z"
        fill="url(#shieldGrad)"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Inner Precision Bevel */}
      <path
        d="M24 9L34.5 13.6V22.5C34.5 29.5 29.9 36 24 38.5C18.1 36 13.5 29.5 13.5 22.5V13.6L24 9Z"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeOpacity="0.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Center Radar Scanner Circle */}
      <circle cx="24" cy="23" r="7.5" fill="url(#radarGlow)" stroke="#10B981" strokeWidth="1.8" />
      <circle cx="24" cy="23" r="3.5" stroke="#10B981" strokeWidth="1" strokeDasharray="1.5 1.5" />
      <circle cx="24" cy="23" r="1.5" fill="#10B981" />

      {/* Autonomous Rover Antenna / Mast Sensor Line */}
      <line x1="24" y1="15.5" x2="24" y2="12" stroke="#10B981" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="24" cy="11.5" r="1" fill="#10B981" />

      {/* Directional Sensor Pulse */}
      <line x1="24" y1="23" x2="29" y2="19" stroke="#10B981" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}
