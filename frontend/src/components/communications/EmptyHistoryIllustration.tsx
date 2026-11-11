'use client';

import React from 'react';
import { Box } from '@mui/material';

export function EmptyHistoryIllustration() {
  return (
    <Box
      sx={{
        width: 190,
        height: 150,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        mx: 'auto',
      }}
    >
      <svg
        width="190"
        height="150"
        viewBox="0 0 190 150"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Potted Plant in Background */}
        <g id="potted-plant">
          {/* Wire Stand */}
          <path
            d="M136 68L133 76M148 68L151 76M142 68L142 76"
            stroke="#94a3b8"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
          {/* Pot body */}
          <ellipse cx="142" cy="56" rx="14" ry="4" fill="#ffffff" stroke="#cbd5e1" strokeWidth="1" />
          <path
            d="M128 56C128 64 133 68 142 68C151 68 156 64 156 56"
            fill="#ffffff"
            stroke="#cbd5e1"
            strokeWidth="1"
          />
          {/* Soil */}
          <ellipse cx="142" cy="56" rx="12" ry="3" fill="#cbd5e1" />
          {/* Blue plant leaves */}
          <path
            d="M142 54C140 46 137 38 134 32C138 35 142 42 142 54Z"
            fill="#38bdf8"
          />
          <path
            d="M142 54C143 44 146 36 150 30C148 35 145 44 142 54Z"
            fill="#0284c7"
          />
          <path
            d="M142 54C140 43 141 33 142 26C144 33 144 43 142 54Z"
            fill="#2563eb"
          />
          <path
            d="M137 54C134 48 130 42 127 38C132 42 136 48 137 54Z"
            fill="#60a5fa"
          />
          <path
            d="M147 54C150 48 153 43 156 39C152 43 148 49 147 54Z"
            fill="#0369a1"
          />
        </g>

        {/* Small Blue Notebook */}
        <g id="notebook" transform="translate(140, 68) rotate(20)">
          <rect x="0" y="0" width="22" height="28" rx="2" fill="#1d4ed8" />
          <rect x="0" y="0" width="4" height="28" rx="1" fill="#1e40af" />
          <line x1="8" y1="8" x2="18" y2="8" stroke="#93c5fd" strokeWidth="1.5" strokeLinecap="round" />
          <line x1="8" y1="13" x2="18" y2="13" stroke="#93c5fd" strokeWidth="1.5" strokeLinecap="round" />
          <line x1="8" y1="18" x2="15" y2="18" stroke="#93c5fd" strokeWidth="1.5" strokeLinecap="round" />
          {/* White Ribbon */}
          <path d="M12 28L12 34L14 32L16 34L16 28" fill="#ffffff" />
        </g>

        {/* Isometric Clipboard Document */}
        <g id="clipboard">
          {/* Clipboard Backing Sheet */}
          <path
            d="M60 66L126 92L100 128L34 102Z"
            fill="#dbeafe"
            stroke="#93c5fd"
            strokeWidth="1.2"
            strokeLinejoin="round"
          />
          {/* Clip at the top */}
          <path
            d="M74 65L86 70L80 77L68 72Z"
            fill="#94a3b8"
            stroke="#64748b"
            strokeWidth="1"
            strokeLinejoin="round"
          />
          {/* Profile Card / Photo thumbnail on clipboard */}
          <path
            d="M58 80L72 85L67 92L53 87Z"
            fill="#bfdbfe"
          />
          <circle cx="62" cy="85" r="2.5" fill="#3b82f6" />
          {/* Text Lines */}
          <path d="M76 83L98 92" stroke="#93c5fd" strokeWidth="2" strokeLinecap="round" />
          <path d="M74 88L94 96" stroke="#93c5fd" strokeWidth="2" strokeLinecap="round" />
          <path d="M54 96L88 109" stroke="#93c5fd" strokeWidth="1.8" strokeLinecap="round" />
          <path d="M51 102L85 115" stroke="#93c5fd" strokeWidth="1.8" strokeLinecap="round" />
          <path d="M48 108L76 119" stroke="#93c5fd" strokeWidth="1.8" strokeLinecap="round" />
        </g>

        {/* Magnifying Glass */}
        <g id="magnifying-glass">
          {/* Lens Outline */}
          <ellipse
            cx="115"
            cy="110"
            rx="9"
            ry="9"
            fill="#e0f2fe"
            fillOpacity="0.8"
            stroke="#1d4ed8"
            strokeWidth="2.5"
          />
          {/* Lens Glare */}
          <path
            d="M110 106C112 103 116 103 118 105"
            stroke="#ffffff"
            strokeWidth="1.2"
            strokeLinecap="round"
          />
          {/* Handle */}
          <line
            x1="121"
            y1="116"
            x2="134"
            y2="129"
            stroke="#1e3a8a"
            strokeWidth="3.5"
            strokeLinecap="round"
          />
        </g>
      </svg>
    </Box>
  );
}
