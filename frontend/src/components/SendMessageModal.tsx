'use client';

import React, { useEffect, useState } from 'react';
import {
  Drawer,
  Box,
  Typography,
  IconButton,
  Button,
  Stack,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Divider,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import ScheduleSendIcon from '@mui/icons-material/ScheduleSend';

import { communicationsApi } from '@/lib/api';
import { useToast } from '@/context/ToastContext';
import { Candidate, CandidateMessageOutcome, MessageTemplate } from '@/types';

interface SendMessageModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  candidate: Candidate | null;
  recipients?: Candidate[];
}

interface BulkOutcomeRow {
  name: string;
  success: boolean;
  status: string;
  error: string | null;
}

function toIsoOrNull(localValue: string): string | null {
  if (!localValue) return null;
  const date = new Date(localValue);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

export function SendMessageModal({
  open,
  onClose,
  onSuccess,
  candidate,
  recipients = [],
}: SendMessageModalProps) {
  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [content, setContent] = useState('');
  const [contentError, setContentError] = useState('');
  const [templates, setTemplates] = useState<MessageTemplate[]>([]);
  const [templateId, setTemplateId] = useState<number | ''>('');
  const [scheduledAt, setScheduledAt] = useState('');
  const [preview, setPreview] = useState('');
  // Per-candidate results shown after bulk send
  const [outcomeRows, setOutcomeRows] = useState<BulkOutcomeRow[] | null>(null);

  const recipientList: Candidate[] =
    recipients.length > 0 ? recipients : candidate ? [candidate] : [];
  const previewCandidateId = recipientList[0]?.id;
  const isBulk = recipientList.length > 1;

  // Load templates when drawer opens
  useEffect(() => {
    if (!open) return;
    communicationsApi.listTemplates().then(setTemplates).catch(() => setTemplates([]));
  }, [open]);

  // Live preview (debounced 250ms) — always show when content is present
  useEffect(() => {
    if (!open || !previewCandidateId || !content.trim()) {
      setPreview('');
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const result = await communicationsApi.previewTemplate({
          candidate_id: previewCandidateId,
          content,
          template_id: templateId || undefined,
        });
        setPreview(result.preview);
      } catch {
        setPreview('');
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [open, content, templateId, previewCandidateId]);

  const resetForm = () => {
    setContent('');
    setContentError('');
    setTemplateId('');
    setScheduledAt('');
    setPreview('');
    setOutcomeRows(null);
  };

  const handleClose = () => {
    if (loading) return;
    resetForm();
    onClose();
  };

  const handleTemplateChange = (id: number | '') => {
    setTemplateId(id);
    if (id === '') {
      setContent('');
      return;
    }
    const selected = templates.find((t) => t.id === id);
    if (selected) {
      setContent(selected.content);
    }
  };

  const handleSend = async () => {
    if (!content.trim() && !templateId) {
      setContentError('Message content cannot be empty.');
      return;
    }
    if (recipientList.length === 0) return;

    setLoading(true);
    setContentError('');
    setOutcomeRows(null);

    // Always use dummy provider — channel not exposed to UI
    const payloadExtras = {
      channel: 'sms' as const,
      content: content.trim(),
      provider: 'dummy',
      scheduled_at: toIsoOrNull(scheduledAt),
      template_id: templateId || null,
    };

    try {
      if (recipientList.length === 1) {
        const target = recipientList[0];
        const outcome = await communicationsApi.send({
          candidate_id: target.id,
          ...payloadExtras,
        });

        resetForm();
        onSuccess();
        handleClose();

        if (!outcome.success) {
          showToast(outcome.error_message || 'Message failed to send.', 'error');
        } else if (outcome.status === 'scheduled') {
          showToast('Message scheduled successfully', 'success');
        } else {
          showToast('Message sent successfully', 'success');
        }
      } else {
        // Bulk send — show per-candidate results instead of just a toast
        const resp = await communicationsApi.bulkSend({
          candidate_ids: recipientList.map((r) => r.id),
          ...payloadExtras,
        });

        // Build per-candidate outcome rows
        const rows: BulkOutcomeRow[] = resp.outcomes.map(
          (o: CandidateMessageOutcome) => ({
            name: o.candidate_name || `Candidate #${o.candidate_id}`,
            success: o.success,
            status: o.status,
            error: o.error_message || null,
          }),
        );
        setOutcomeRows(rows);
        onSuccess();

        if (resp.failed_count === 0) {
          showToast(
            scheduledAt
              ? `Scheduled for ${resp.successful_count} candidate${resp.successful_count > 1 ? 's' : ''}`
              : `Sent to ${resp.successful_count} candidate${resp.successful_count > 1 ? 's' : ''}`,
            'success',
          );
        } else {
          showToast(
            `${resp.successful_count} sent, ${resp.failed_count} failed`,
            resp.successful_count > 0 ? 'warning' : 'error',
          );
        }
      }
    } catch {
      showToast('Failed to send message. Please try again.', 'error');
    } finally {
      setLoading(false);
    }
  };

  // ── Result panel shown after bulk send ──────────────────────────────────────
  const ResultPanel = () => (
    <Box sx={{ px: 3.5, py: 1, flex: 1, overflowY: 'auto' }}>
      <Typography sx={{ fontWeight: 600, fontSize: '0.9rem', color: '#1f2937', mb: 2 }}>
        Send Results — {outcomeRows!.length} candidates
      </Typography>
      <Stack spacing={1}>
        {outcomeRows!.map((row, i) => (
          <Box
            key={i}
            sx={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: 1.5,
              p: 1.25,
              borderRadius: '4px',
              backgroundColor: row.success ? '#f0fdf4' : '#fef2f2',
              border: `1px solid ${row.success ? '#bbf7d0' : '#fecaca'}`,
            }}
          >
            {row.success ? (
              <CheckCircleOutlineIcon sx={{ color: '#16a34a', fontSize: 20, mt: 0.1, flexShrink: 0 }} />
            ) : (
              <ErrorOutlineIcon sx={{ color: '#dc2626', fontSize: 20, mt: 0.1, flexShrink: 0 }} />
            )}
            <Box sx={{ minWidth: 0 }}>
              <Typography sx={{ fontSize: '0.8125rem', fontWeight: 600, color: '#1f2937' }}>
                {row.name}
              </Typography>
              <Typography
                sx={{
                  fontSize: '0.75rem',
                  color: row.success ? '#16a34a' : '#dc2626',
                  textTransform: 'capitalize',
                }}
              >
                {row.success
                  ? row.status === 'scheduled'
                    ? '⏱ Scheduled'
                    : '✓ Sent'
                  : row.error || `Failed (${row.status})`}
              </Typography>
            </Box>
          </Box>
        ))}
      </Stack>
    </Box>
  );

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={loading ? undefined : handleClose}
      PaperProps={{
        sx: {
          width: { xs: '100%', sm: 480, md: 520 },
          backgroundColor: '#ffffff',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          boxShadow: '-4px 0 24px rgba(0,0,0,0.08)',
          p: 0,
        },
      }}
    >
      {/* ── Header ───────────────────────────────────────────────────────────── */}
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
          sx={{ fontWeight: 700, fontSize: '1.2rem', color: '#1a1a2e', letterSpacing: '-0.01em' }}
        >
          {outcomeRows ? 'Send Results' : isBulk ? `Send to ${recipientList.length} Candidates` : 'Send Message'}
        </Typography>
        <IconButton
          onClick={handleClose}
          size="small"
          disabled={loading}
          sx={{ color: '#757575', p: 0.5, '&:hover': { backgroundColor: '#f5f5f5' } }}
        >
          <CloseIcon sx={{ fontSize: 20 }} />
        </IconButton>
      </Box>

      {/* ── Body ─────────────────────────────────────────────────────────────── */}
      {outcomeRows ? (
        <ResultPanel />
      ) : (
        <Box
          sx={{
            px: 3.5,
            py: 1,
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            gap: 2.5,
            overflowY: 'auto',
          }}
        >
          {/* Recipients */}
          <Box>
            <Typography sx={{ fontWeight: 600, fontSize: '0.875rem', color: '#1f2937', mb: 1 }}>
              {recipientList.length === 1 ? '1 Recipient' : `${recipientList.length} Recipients`}
            </Typography>
            <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
              {recipientList.map((c) => (
                <Box
                  key={c.id}
                  sx={{
                    backgroundColor: '#e8eaed',
                    color: '#374151',
                    borderRadius: '16px',
                    px: 1.75,
                    py: 0.5,
                    fontSize: '0.8125rem',
                    fontWeight: 500,
                  }}
                >
                  {c.full_name}
                </Box>
              ))}
            </Stack>
          </Box>

          {/* Template picker */}
          <FormControl fullWidth size="small">
            <InputLabel>Template (optional)</InputLabel>
            <Select
              value={templateId}
              label="Template (optional)"
              onChange={(e) => handleTemplateChange(e.target.value as number | '')}
              disabled={loading}
            >
              <MenuItem value="">Write a custom message</MenuItem>
              {templates.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  {t.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Message textarea */}
          <Box>
            <Typography sx={{ fontWeight: 600, fontSize: '0.875rem', color: '#1f2937' }}>
              Message{' '}
              <Box component="span" sx={{ color: '#d32f2f' }}>
                *
              </Box>
            </Typography>
            <Typography sx={{ fontSize: '0.78rem', color: '#6b7280', mt: 0.5, mb: 1.5 }}>
              Type a message or pick a template. Fields like {'{{full_name}}'} are filled in at
              send time.
            </Typography>

            <Box
              component="textarea"
              id="message-send-textarea"
              rows={7}
              placeholder="Type or paste here..."
              value={content}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => {
                setContent(e.target.value);
                if (contentError) setContentError('');
              }}
              disabled={loading}
              sx={{
                width: '100%',
                minHeight: 140,
                border: contentError ? '1px solid #d32f2f' : '1px solid #cfd8dc',
                borderRadius: '4px',
                p: 1.5,
                fontSize: '0.875rem',
                fontFamily: 'inherit',
                color: '#1f2937',
                resize: 'both',
                outline: 'none',
                boxSizing: 'border-box',
                lineHeight: 1.5,
                '&:focus': {
                  borderColor: contentError ? '#d32f2f' : '#1976d2',
                  boxShadow: contentError ? '0 0 0 1px #d32f2f' : '0 0 0 1px #1976d2',
                },
                '&::placeholder': { color: '#9e9e9e' },
              }}
            />
            {contentError && (
              <Typography sx={{ color: '#d32f2f', fontSize: '0.75rem', mt: 0.5 }}>
                {contentError}
              </Typography>
            )}
          </Box>

          {/* Preview box — shown whenever content is non-empty for a single recipient */}
          {preview && recipientList.length === 1 && (
            <Box
              sx={{
                backgroundColor: '#f8fafc',
                border: '1px solid #e2e8f0',
                borderRadius: '4px',
                p: 1.5,
              }}
            >
              <Typography sx={{ fontSize: '0.72rem', fontWeight: 700, color: '#64748b', mb: 0.5, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Preview for {recipientList[0].full_name}
              </Typography>
              <Divider sx={{ mb: 1 }} />
              <Typography sx={{ fontSize: '0.8125rem', color: '#1f2937', whiteSpace: 'pre-wrap' }}>
                {preview}
              </Typography>
            </Box>
          )}

          {/* Schedule */}
          <TextField
            size="small"
            label="Schedule send (optional)"
            type="datetime-local"
            value={scheduledAt}
            onChange={(e) => setScheduledAt(e.target.value)}
            disabled={loading}
            InputLabelProps={{ shrink: true }}
            helperText="Leave empty to send immediately."
          />
        </Box>
      )}

      {/* ── Footer ───────────────────────────────────────────────────────────── */}
      <Box
        sx={{
          px: 3.5,
          pb: 3.5,
          pt: 2,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
          gap: 1.5,
          borderTop: '1px solid #f0f0f0',
        }}
      >
        {outcomeRows ? (
          <Button
            variant="contained"
            onClick={handleClose}
            sx={{
              backgroundColor: '#1976d2',
              color: '#fff',
              textTransform: 'uppercase',
              fontWeight: 500,
              fontSize: '0.8125rem',
              height: 36,
              px: 2.5,
              borderRadius: '4px',
              boxShadow: 'none',
              '&:hover': { backgroundColor: '#1565c0', boxShadow: 'none' },
            }}
          >
            Done
          </Button>
        ) : (
          <>
            <Button
              onClick={handleClose}
              variant="outlined"
              disabled={loading}
              sx={{
                borderColor: '#90caf9',
                color: '#1976d2',
                textTransform: 'uppercase',
                fontWeight: 500,
                fontSize: '0.8125rem',
                height: 36,
                px: 2.5,
                borderRadius: '4px',
                '&:hover': { borderColor: '#42a5f5', backgroundColor: '#f4f9ff' },
              }}
            >
              Cancel
            </Button>
            <Button
              id="submit-send-message-btn"
              onClick={handleSend}
              variant="contained"
              disabled={loading || !content.trim()}
              startIcon={
                loading ? undefined : scheduledAt ? (
                  <ScheduleSendIcon sx={{ fontSize: 17 }} />
                ) : undefined
              }
              sx={{
                backgroundColor: content.trim() ? '#1976d2' : '#e0e0e0',
                color: content.trim() ? '#ffffff' : '#9e9e9e',
                textTransform: 'uppercase',
                fontWeight: 500,
                fontSize: '0.8125rem',
                height: 36,
                px: 2.5,
                borderRadius: '4px',
                boxShadow: 'none',
                '&:hover': { backgroundColor: content.trim() ? '#1565c0' : '#e0e0e0', boxShadow: 'none' },
                '&.Mui-disabled': { backgroundColor: '#e0e0e0', color: '#9e9e9e' },
              }}
            >
              {loading ? (
                <CircularProgress size={18} color="inherit" />
              ) : scheduledAt ? (
                'Schedule'
              ) : isBulk ? (
                `Send to ${recipientList.length}`
              ) : (
                'Send Message'
              )}
            </Button>
          </>
        )}
      </Box>
    </Drawer>
  );
}
