'use client';

import React from 'react';
import { Box } from '@mui/material';

/**
 * Exact vector illustration matching Screenshot 1 empty state:
 * - Isometric clipboard document with photo ID circle and text lines
 * - Potted succulent plant with blue leaves
 * - Blue notebook with white pencil
 * - Magnifying glass pointing towards document
 */
export function EmptyCandidatesIllustration({ width = 190, height = 140 }: { width?: number; height?: number }) {
  return (
    <Box sx={{ display: 'inline-block', width, height, userSelect: 'none' }}>
      <svg
        viewBox="0 0 240 180"
        width="100%"
        height="100%"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Soft shadow under elements */}
        <ellipse cx="120" cy="148" rx="85" ry="16" fill="#e2e8f0" opacity="0.6" />

        {/* ── 1. Clipboard / Resume Document ── */}
        <g transform="translate(42, 62) rotate(-8)">
          {/* Clipboard base */}
          <rect x="0" y="0" width="84" height="106" rx="6" fill="#bfdbfe" stroke="#93c5fd" strokeWidth="2" />
          {/* Paper sheet */}
          <rect x="5" y="7" width="74" height="92" rx="4" fill="#ffffff" />
          
          {/* Top Metal Clip */}
          <rect x="27" y="1" width="30" height="9" rx="3" fill="#cbd5e1" stroke="#94a3b8" strokeWidth="1.5" />
          <circle cx="42" cy="5.5" r="2" fill="#64748b" />

          {/* User Photo Avatar Box */}
          <rect x="12" y="18" width="22" height="22" rx="4" fill="#eff6ff" stroke="#bfdbfe" strokeWidth="1" />
          <circle cx="23" cy="25" r="4.5" fill="#3b82f6" />
          <path d="M16 36 C16 32, 30 32, 30 36" fill="#3b82f6" />

          {/* Resume Heading lines */}
          <rect x="40" y="20" width="30" height="3.5" rx="1.75" fill="#93c5fd" />
          <rect x="40" y="28" width="22" height="3" rx="1.5" fill="#cbd5e1" />
          <rect x="40" y="35" width="26" height="3" rx="1.5" fill="#cbd5e1" />

          {/* Horizontal divider */}
          <line x1="12" y1="46" x2="72" y2="46" stroke="#e2e8f0" strokeWidth="1.5" strokeDasharray="3 2" />

          {/* Resume Body content lines */}
          <rect x="12" y="52" width="58" height="3" rx="1.5" fill="#cbd5e1" />
          <rect x="12" y="59" width="48" height="3" rx="1.5" fill="#cbd5e1" />
          <rect x="12" y="66" width="54" height="3" rx="1.5" fill="#cbd5e1" />
          <rect x="12" y="73" width="38" height="3" rx="1.5" fill="#cbd5e1" />
          <rect x="12" y="80" width="50" height="3" rx="1.5" fill="#cbd5e1" />
          <rect x="12" y="87" width="32" height="3" rx="1.5" fill="#cbd5e1" />
        </g>

        {/* ── 2. Potted Plant with Blue Leaves ── */}
        <g transform="translate(130, 48)">
          {/* Plant Pot */}
          <path d="M16 48 L19 72 C19 75, 37 75, 37 72 L40 48 Z" fill="#f8fafc" stroke="#cbd5e1" strokeWidth="2" />
          {/* Pot Rim */}
          <ellipse cx="28" cy="48" rx="13" ry="3.5" fill="#e2e8f0" stroke="#cbd5e1" strokeWidth="1.5" />
          {/* Soil */}
          <ellipse cx="28" cy="48" rx="11" ry="2.5" fill="#64748b" />

          {/* Succulent Blue Leaves */}
          {/* Center Leaf */}
          <path d="M28 48 C25 32, 25 18, 28 8 C31 18, 31 32, 28 48 Z" fill="#0284c7" />
          {/* Left Leaf 1 */}
          <path d="M27 48 C20 36, 14 26, 17 15 C23 23, 27 34, 27 48 Z" fill="#38bdf8" />
          {/* Left Leaf 2 */}
          <path d="M26 48 C16 42, 9 38, 10 27 C18 32, 24 40, 26 48 Z" fill="#0ea5e9" />
          {/* Right Leaf 1 */}
          <path d="M29 48 C36 36, 42 26, 39 15 C33 23, 29 34, 29 48 Z" fill="#0284c7" />
          {/* Right Leaf 2 */}
          <path d="M30 48 C40 42, 47 38, 46 27 C38 32, 32 40, 30 48 Z" fill="#38bdf8" />
          {/* Front Center Leaflet */}
          <path d="M28 48 C26 38, 26 28, 28 22 C30 28, 30 38, 28 48 Z" fill="#bae6fd" />
        </g>

        {/* ── 3. Small Blue Notebook with White Pencil ── */}
        <g transform="translate(142, 98) rotate(14)">
          {/* Book Shadow */}
          <rect x="2" y="2" width="40" height="32" rx="3" fill="#94a3b8" opacity="0.3" />
          {/* Book Cover */}
          <rect x="0" y="0" width="40" height="32" rx="3" fill="#0284c7" />
          {/* Paper Edge Pages */}
          <path d="M38 4 L40 4 L40 28 L38 28 Z" fill="#ffffff" />
          <line x1="39" y1="6" x2="39" y2="26" stroke="#e2e8f0" strokeWidth="1" />
          {/* Bookmark ribbon */}
          <path d="M12 0 L12 12 L15 9 L18 12 L18 0 Z" fill="#f8fafc" />

          {/* White Pencil lying across */}
          <g transform="translate(6, 12) rotate(-35)">
            <rect x="0" y="0" width="28" height="3.5" rx="1" fill="#ffffff" stroke="#94a3b8" strokeWidth="0.8" />
            {/* Pencil Tip */}
            <polygon points="28,0 34,1.75 28,3.5" fill="#fde047" />
            <polygon points="32,1.2 34,1.75 32,2.3" fill="#1e293b" />
          </g>
        </g>

        {/* ── 4. Magnifying Glass ── */}
        <g transform="translate(118, 122) rotate(-28)">
          {/* Glass Rim */}
          <circle cx="16" cy="16" r="14" fill="#e0f2fe" fillOpacity="0.45" stroke="#0284c7" strokeWidth="3" />
          {/* Glare on Lens */}
          <path d="M8 12 A10 10 0 0 1 18 6" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round" opacity="0.9" />
          {/* Handle Base Ring */}
          <rect x="28" y="14" width="4" height="4" rx="1" fill="#64748b" />
          {/* Handle */}
          <rect x="31" y="13.5" width="22" height="5" rx="2.5" fill="#1e293b" />
        </g>
      </svg>
    </Box>
  );
}
