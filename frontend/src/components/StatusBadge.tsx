'use client';

import React from 'react';
import { Chip } from '@mui/material';
import CheckCircleOutlinedIcon from '@mui/icons-material/CheckCircleOutlined';
import DoneAllIcon from '@mui/icons-material/DoneAll';
import ErrorOutlinedIcon from '@mui/icons-material/ErrorOutlined';
import SendOutlinedIcon from '@mui/icons-material/SendOutlined';
import { MessageStatus } from '@/types';

interface StatusBadgeProps {
  status: MessageStatus;
}

const statusConfig: Record<MessageStatus, {
  label: string;
  color: 'success' | 'error' | 'info' | 'default';
  icon?: React.ReactElement;
}> = {
  read: {
    label: 'read',
    color: 'success',
    icon: <CheckCircleOutlinedIcon sx={{ fontSize: '14px !important' }} />,
  },
  delivered: {
    label: 'Delivered',
    color: 'info',
    icon: <DoneAllIcon sx={{ fontSize: '14px !important' }} />,
  },
  sent: {
    label: 'Sent',
    color: 'info',
    icon: <SendOutlinedIcon sx={{ fontSize: '13px !important' }} />,
  },
  failed: {
    label: 'Failed',
    color: 'error',
    icon: <ErrorOutlinedIcon sx={{ fontSize: '14px !important' }} />,
  },
  NA: {
    label: 'NA',
    color: 'default',
  },
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const config = statusConfig[status] ?? statusConfig['NA'];

  if (status === 'NA') {
    return (
      <span style={{ color: '#9e9e9e', fontSize: '0.875rem' }}>NA</span>
    );
  }

  return (
    <Chip
      label={config.label}
      color={config.color}
      icon={config.icon}
      size="small"
      variant="outlined"
      sx={{
        fontSize: '0.75rem',
        fontWeight: 500,
        height: 26,
        borderRadius: '6px',
        '& .MuiChip-label': { px: 1 },
        '& .MuiChip-icon': { ml: 0.5 },
        ...(status === 'read' && {
          borderColor: '#4caf50',
          color: '#4caf50',
          backgroundColor: '#f1f8e9',
          '& .MuiChip-icon': { color: '#4caf50', ml: 0.5 },
        }),
        ...(status === 'delivered' && {
          borderColor: '#0288d1',
          color: '#0288d1',
          backgroundColor: '#e1f5fe',
          '& .MuiChip-icon': { color: '#0288d1', ml: 0.5 },
        }),
        ...(status === 'failed' && {
          borderColor: '#f44336',
          color: '#f44336',
          backgroundColor: '#ffebee',
          '& .MuiChip-icon': { color: '#f44336', ml: 0.5 },
        }),
        ...(status === 'sent' && {
          borderColor: '#29b6f6',
          color: '#0288d1',
          backgroundColor: '#f0f9ff',
          '& .MuiChip-icon': { color: '#0288d1', ml: 0.5 },
        }),
      }}
    />
  );
}
