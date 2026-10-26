'use client';

import React, { useEffect, useState, useCallback } from 'react';
import {
  Drawer,
  Box,
  Typography,
  IconButton,
  CircularProgress,
  Tooltip,
  Button,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import CheckIcon from '@mui/icons-material/Check';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import ReplayIcon from '@mui/icons-material/Replay';
import { useToast } from '@/context/ToastContext';

import { Candidate, Message } from '@/types';
import { communicationsApi } from '@/lib/api';
import { EmptyHistoryIllustration } from './EmptyHistoryIllustration';

interface CandidateDetailModalProps {
  open: boolean;
  onClose: () => void;
  candidate: Candidate | null;
  onSendMessage?: (candidate: Candidate) => void;
}

/** Formats timestamp to match Screenshot 2: "25-10-2026 | 9:47 AM" */
function formatHistoryDateTime(dateStr: string | null): string {
  if (!dateStr) return 'NA';
  try {
    const d = new Date(dateStr);
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    let hours = d.getHours();
    const minutes = String(d.getMinutes()).padStart(2, '0');
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12 || 12;
    return `${day}-${month}-${year} | ${hours}:${minutes} ${ampm}`;
  } catch {
    return dateStr;
  }
}

/** Status Pill badge matching Screenshot 2 */
function renderHistoryStatusBadge(status: string) {
  const norm = (status || '').toLowerCase();

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
          fontSize: '0.72rem',
          fontWeight: 500,
          border: '1px solid #c8e6c9',
          lineHeight: 1.4,
        }}
      >
        <CheckIcon sx={{ fontSize: 13, color: '#2e7d32' }} />
        <span>read</span>
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
          fontSize: '0.72rem',
          fontWeight: 500,
          border: '1px solid #bae6fd',
          lineHeight: 1.4,
        }}
      >
        <CheckIcon sx={{ fontSize: 13, color: '#0284c7' }} />
        <span>Delivered</span>
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
          fontSize: '0.72rem',
          fontWeight: 500,
          border: '1px solid #ffe082',
          lineHeight: 1.4,
        }}
      >
        <span>Scheduled</span>
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
          fontSize: '0.72rem',
          fontWeight: 500,
          border: '1px solid #ffcdd2',
          lineHeight: 1.4,
        }}
      >
        <ErrorOutlineIcon sx={{ fontSize: 13, color: '#d32f2f' }} />
        <span>Failed</span>
      </Box>
    );
  }

  // Default: Sent
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
        fontSize: '0.72rem',
        fontWeight: 500,
        border: '1px solid #b3e5fc',
        lineHeight: 1.4,
      }}
    >
      <span>Sent</span>
    </Box>
  );
}

export function CandidateDetailModal({
  open,
  onClose,
  candidate,
}: CandidateDetailModalProps) {
  const { showToast } = useToast();
  const [messages, setMessages] = useState<Message[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [retryingId, setRetryingId] = useState<number | null>(null);

  const fetchHistory = useCallback(async () => {
    if (!candidate) return;
    setLoadingHistory(true);
    try {
      const history = await communicationsApi.getHistory(candidate.id);
      // Ensure sorted recent to oldest
      const sorted = [...history].sort((a, b) => {
        const timeA = new Date(a.sent_at || 0).getTime();
        const timeB = new Date(b.sent_at || 0).getTime();
        return timeB - timeA;
      });
      setMessages(sorted);
    } catch {
      setMessages([]);
    } finally {
      setLoadingHistory(false);
    }
  }, [candidate]);

  useEffect(() => {
    if (open && candidate) {
      fetchHistory();
    } else {
      setMessages([]);
    }
  }, [open, candidate, fetchHistory]);

  const handleRetry = async (message: Message) => {
    setRetryingId(message.id);
    try {
      const outcome = await communicationsApi.retry(message.id);
      if (outcome.success) {
        showToast('Message retried successfully.', 'success');
      } else {
        showToast(outcome.error_message || 'Retry failed.', 'error');
      }
      await fetchHistory();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { error_message?: string; detail?: string } } })?.response?.data
          ?.error_message ||
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'This message cannot be retried.';
      showToast(detail, 'error');
    } finally {
      setRetryingId(null);
    }
  };

  if (!candidate) return null;

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: {
          width: { xs: '100%', sm: 480, md: 520 },
          backgroundColor: '#ffffff',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '-4px 0 24px rgba(0,0,0,0.08)',
          p: 0,
        },
      }}
    >
      {/* ── Top Header matching Screenshots 2 & 3 ─────────────────────────── */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          pt: 3.5,
          px: 3.5,
          pb: 2,
        }}
      >
        <Typography
          variant="h6"
          sx={{
            fontWeight: 700,
            fontSize: '1.2rem',
            color: '#1a1a2e',
            letterSpacing: '-0.01em',
          }}
        >
          Communication history
        </Typography>
        <IconButton
          onClick={onClose}
          size="small"
          sx={{
            color: '#757575',
            p: 0.5,
            '&:hover': { backgroundColor: '#f5f5f5' },
          }}
        >
          <CloseIcon sx={{ fontSize: 20 }} />
        </IconButton>
      </Box>

      {/* ── Candidate Profile Information matching Screenshots 2 & 3 ─────── */}
      <Box sx={{ px: 3.5, pt: 1, pb: 1 }}>
        <Typography
          sx={{
            fontSize: '0.75rem',
            color: '#757575',
            fontWeight: 400,
            mb: 0.5,
          }}
        >
          Candidate ID: {candidate.candidate_id}
        </Typography>
        <Typography
          sx={{
            fontSize: '1.25rem',
            fontWeight: 700,
            color: '#111827',
            letterSpacing: '-0.01em',
            mb: 0.5,
            lineHeight: 1.3,
          }}
        >
          {candidate.full_name}
        </Typography>
        <Typography
          sx={{
            fontSize: '0.85rem',
            color: '#374151',
            fontWeight: 400,
            mb: 0.25,
          }}
        >
          {candidate.mobile_number}
        </Typography>
        <Typography
          sx={{
            fontSize: '0.85rem',
            color: '#374151',
            fontWeight: 400,
          }}
        >
          {candidate.email || `${candidate.full_name.toLowerCase().replace(/\s+/g, '')}@gmail.com`}
        </Typography>

        {/* Divider line below candidate details matching Screenshot 2 */}
        {messages.length > 0 && !loadingHistory && (
          <Box sx={{ borderBottom: '1px solid #e0e0e0', mt: 3, mb: 1.5 }} />
        )}
      </Box>

      {/* ── Body: Messages Timeline or Empty State ────────────────────────── */}
      <Box sx={{ flex: 1, overflowY: 'auto', px: 3.5, py: 1 }}>
        {loadingHistory ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
            <CircularProgress size={28} sx={{ color: '#1976d2' }} />
          </Box>
        ) : messages.length === 0 ? (
          /* ── Empty State matching Screenshot 3 ─────────────────────────── */
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              py: 8,
              textAlign: 'center',
            }}
          >
            <EmptyHistoryIllustration />
            <Typography
              sx={{
                fontWeight: 600,
                fontSize: '0.95rem',
                color: '#1f2937',
                mt: 3,
                mb: 0.75,
              }}
            >
              No communication history
            </Typography>
            <Typography
              sx={{
                fontSize: '0.8125rem',
                color: '#6b7280',
                lineHeight: 1.5,
                maxWidth: 320,
              }}
            >
              You have not communicated with this candidate yet.
              <br />
              When you send them a message, it will appear here.
            </Typography>
          </Box>
        ) : (
          /* ── Messages List matching Screenshot 2 (Recent to Oldest) ─────── */
          <Box sx={{ display: 'flex', flexDirection: 'column' }}>
            {messages.map((msg) => (
              <Box key={msg.id} sx={{ mb: 2 }}>
                {/* Header row: Date | Time on left, Status Badge on right */}
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    mb: 0.75,
                  }}
                >
                  <Typography
                    sx={{
                      fontSize: '0.78rem',
                      color: '#757575',
                      fontWeight: 400,
                    }}
                  >
                    {msg.status === 'scheduled' && msg.scheduled_at
                      ? `Scheduled ${formatHistoryDateTime(msg.scheduled_at)}`
                      : formatHistoryDateTime(msg.sent_at)}
                  </Typography>
                  <Tooltip
                    title={`Provider: ${msg.provider || 'dummy-service'} | Channel: ${(msg.channel || 'sms').toUpperCase()} | Ref ID: ${msg.provider_message_id || `MSG-${msg.id}`}`}
                    arrow
                    placement="left"
                  >
                    <Box component="span" sx={{ cursor: 'pointer' }}>
                      {renderHistoryStatusBadge(msg.status)}
                    </Box>
                  </Tooltip>
                </Box>

                {/* Message Body Content */}
                <Typography
                  sx={{
                    fontSize: '0.8125rem',
                    color: '#1f2937',
                    lineHeight: 1.5,
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                  }}
                >
                  {msg.content}
                </Typography>
                {msg.status === 'failed' && msg.error_message && (
                  <Typography sx={{ fontSize: '0.75rem', color: '#d32f2f', mt: 0.75 }}>
                    {msg.error_message}
                    {!msg.is_retryable ? ' This failure is permanent and cannot be retried.' : ''}
                  </Typography>
                )}
                {msg.status === 'failed' && msg.is_retryable && (
                  <Button
                    size="small"
                    startIcon={retryingId === msg.id ? <CircularProgress size={12} /> : <ReplayIcon sx={{ fontSize: 14 }} />}
                    onClick={() => handleRetry(msg)}
                    disabled={retryingId === msg.id}
                    sx={{ mt: 0.75, textTransform: 'none', fontSize: '0.75rem' }}
                  >
                    Retry message
                  </Button>
                )}

                {/* Divider below each message item */}
                <Box sx={{ borderBottom: '1px solid #eeeeee', mt: 2 }} />
              </Box>
            ))}
          </Box>
        )}
      </Box>
    </Drawer>
  );
}
