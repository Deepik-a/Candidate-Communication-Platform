'use client';

import React from 'react';
import { Box, Typography } from '@mui/material';
import { CommunicationHealth } from '@/types';

interface ServiceHealthBarProps {
  health: CommunicationHealth | null;
}

function statusColor(status: string | undefined) {
  if (status === 'operational') return '#2e7d32';
  if (status === 'degraded') return '#f57c00';
  return '#d32f2f';
}

export function ServiceHealthBar({ health }: ServiceHealthBarProps) {
  if (!health) return null;

  const color = statusColor(health.status);

  return (
    <Box sx={{ px: 3.5, pb: 2 }}>
      <Box
        sx={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: 2.5,
          px: 2,
          py: 1.25,
          border: '1px solid #eeeeee',
          borderRadius: '6px',
          backgroundColor: '#fafafa',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 220 }}>
          <Box sx={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: color }} />
          <Typography sx={{ fontSize: '0.8125rem', fontWeight: 600, color: '#1a1a2e' }}>
            Communication Service
          </Typography>
          <Typography sx={{ fontSize: '0.8125rem', fontWeight: 600, color }}>
            {health.label}
          </Typography>
        </Box>
        <Typography sx={{ fontSize: '0.8rem', color: '#424242' }}>
          Messages Sent <b>{health.messages_sent}</b>
        </Typography>
        <Typography sx={{ fontSize: '0.8rem', color: '#424242' }}>
          Messages Delivered <b>{health.messages_delivered}</b>
        </Typography>
        <Typography sx={{ fontSize: '0.8rem', color: '#424242' }}>
          Messages Failed <b>{health.messages_failed}</b>
        </Typography>
        {health.messages_scheduled > 0 && (
          <Typography sx={{ fontSize: '0.8rem', color: '#424242' }}>
            Scheduled <b>{health.messages_scheduled}</b>
          </Typography>
        )}
      </Box>
      {health.recruiter_notice && (
        <Typography sx={{ mt: 1, fontSize: '0.78rem', color: '#c62828' }}>
          {health.recruiter_notice}
        </Typography>
      )}
    </Box>
  );
}
