'use client';

import React from 'react';
import { Box } from '@mui/material';
import CheckIcon from '@mui/icons-material/Check';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import { MessageStatus } from '@/types';

interface StatusBadgeProps {
  status: MessageStatus | string;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const norm = (status || 'NA').toLowerCase();

  if (norm === 'na' || !status) {
    return (
      <span style={{ color: '#757575', fontSize: '0.85rem', fontWeight: 400 }}>
        NA
      </span>
    );
  }

  if (norm === 'read') {
    return (
      <Box
        component="span"
        sx={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 0.5,
          backgroundColor: '#e8f5e9',
          color: '#2e7d32',
          px: 1.25,
          py: 0.25,
          borderRadius: '16px',
          fontSize: '0.75rem',
          fontWeight: 500,
          lineHeight: 1.5,
          border: '1px solid #c8e6c9',
        }}
      >
        <CheckIcon sx={{ fontSize: 13, color: '#2e7d32' }} />
        <span>read</span>
      </Box>
    );
  }

  if (norm === 'failed') {
    return (
      <Box
        component="span"
        sx={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 0.5,
          backgroundColor: '#ffebee',
          color: '#d32f2f',
          px: 1.25,
          py: 0.25,
          borderRadius: '16px',
          fontSize: '0.75rem',
          fontWeight: 500,
          lineHeight: 1.5,
          border: '1px solid #ffcdd2',
        }}
      >
        <ErrorOutlineIcon sx={{ fontSize: 14, color: '#d32f2f' }} />
        <span>Failed</span>
      </Box>
    );
  }

  if (norm === 'sent') {
    return (
      <Box
        component="span"
        sx={{
          display: 'inline-flex',
          alignItems: 'center',
          backgroundColor: '#e1f5fe',
          color: '#0288d1',
          px: 1.5,
          py: 0.25,
          borderRadius: '16px',
          fontSize: '0.75rem',
          fontWeight: 500,
          lineHeight: 1.5,
          border: '1px solid #b3e5fc',
        }}
      >
        <span>Sent</span>
      </Box>
    );
  }

  if (norm === 'scheduled' || norm === 'pending') {
    return (
      <Box
        component="span"
        sx={{
          display: 'inline-flex',
          alignItems: 'center',
          backgroundColor: '#fff8e1',
          color: '#f57c00',
          px: 1.5,
          py: 0.25,
          borderRadius: '16px',
          fontSize: '0.75rem',
          fontWeight: 500,
          lineHeight: 1.5,
          border: '1px solid #ffe082',
        }}
      >
        <span>Scheduled</span>
      </Box>
    );
  }

  if (norm === 'delivered') {
    return (
      <Box
        component="span"
        sx={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 0.5,
          backgroundColor: '#e0f2fe',
          color: '#0284c7',
          px: 1.25,
          py: 0.25,
          borderRadius: '16px',
          fontSize: '0.75rem',
          fontWeight: 500,
          lineHeight: 1.5,
          border: '1px solid #bae6fd',
        }}
      >
        <CheckIcon sx={{ fontSize: 13, color: '#0284c7' }} />
        <span>Delivered</span>
      </Box>
    );
  }

  return (
    <span style={{ color: '#757575', fontSize: '0.85rem' }}>
      {status}
    </span>
  );
}
