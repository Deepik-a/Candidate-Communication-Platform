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
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';

import { communicationsApi } from '@/lib/api';
import { useToast } from '@/context/ToastContext';
import { Candidate, MessageChannel, MessageTemplate } from '@/types';

interface SendMessageModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  candidate: Candidate | null;
  recipients?: Candidate[];
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
  const [channel, setChannel] = useState<MessageChannel>('sms');
  const [provider, setProvider] = useState('dummy');
  const [templates, setTemplates] = useState<MessageTemplate[]>([]);
  const [templateId, setTemplateId] = useState<number | ''>('');
  const [scheduledAt, setScheduledAt] = useState('');
  const [preview, setPreview] = useState('');

  const recipientList: Candidate[] =
    recipients.length > 0 ? recipients : candidate ? [candidate] : [];
  const previewCandidateId = recipientList[0]?.id;

  useEffect(() => {
    if (!open) return;
    communicationsApi.listTemplates().then(setTemplates).catch(() => setTemplates([]));
  }, [open]);

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

  const handleClose = () => {
    if (loading) return;
    setContent('');
    setContentError('');
    setTemplateId('');
    setScheduledAt('');
    setPreview('');
    setChannel('sms');
    setProvider('dummy');
    onClose();
  };

  const handleTemplateChange = (id: number | '') => {
    setTemplateId(id);
    if (id === '') return;
    const selected = templates.find((t) => t.id === id);
    if (selected) {
      setContent(selected.content);
      if (selected.channel === 'sms' || selected.channel === 'whatsapp' || selected.channel === 'email') {
        setChannel(selected.channel);
      }
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

    const payloadExtras = {
      channel,
      content: content.trim(),
      provider,
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
        if (!outcome.success) {
          showToast(outcome.error_message || 'Message failed to send.', 'error');
        } else if (outcome.status === 'scheduled') {
          showToast('Message scheduled for 1 candidate', 'success');
        } else {
          showToast('Message sent to 1 candidate', 'success');
        }
      } else {
        const resp = await communicationsApi.bulkSend({
          candidate_ids: recipientList.map((r) => r.id),
          ...payloadExtras,
        });
        if (resp.failed_count === 0) {
          showToast(
            scheduledAt
              ? `Message scheduled for ${resp.successful_count} candidates`
              : `Message sent to ${resp.successful_count} candidates`,
            'success',
          );
        } else {
          showToast(
            `Sent to ${resp.successful_count}; ${resp.failed_count} failed. Check history for details.`,
            'warning',
          );
        }
      }

      handleClose();
      onSuccess();
    } catch {
      showToast('Failed to send message. Please try again.', 'error');
    } finally {
      setLoading(false);
    }
  };

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
          Send Message
        </Typography>
        <IconButton
          onClick={handleClose}
          size="small"
          disabled={loading}
          sx={{
            color: '#757575',
            p: 0.5,
            '&:hover': { backgroundColor: '#f5f5f5' },
          }}
        >
          <CloseIcon sx={{ fontSize: 20 }} />
        </IconButton>
      </Box>

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
                  display: 'inline-block',
                }}
              >
                {c.full_name}
              </Box>
            ))}
          </Stack>
        </Box>

        <Stack direction="row" spacing={1.5}>
          <FormControl fullWidth size="small">
            <InputLabel>Channel</InputLabel>
            <Select
              value={channel}
              label="Channel"
              onChange={(e) => setChannel(e.target.value as MessageChannel)}
              disabled={loading}
            >
              <MenuItem value="sms">SMS</MenuItem>
              <MenuItem value="whatsapp">WhatsApp</MenuItem>
              <MenuItem value="email">Email</MenuItem>
            </Select>
          </FormControl>
          <FormControl fullWidth size="small">
            <InputLabel>Provider</InputLabel>
            <Select
              value={provider}
              label="Provider"
              onChange={(e) => setProvider(e.target.value)}
              disabled={loading}
            >
              <MenuItem value="dummy">Dummy Service</MenuItem>
              <MenuItem value="whatsapp">WhatsApp Cloud / Sandbox</MenuItem>
              <MenuItem value="mock">Mock Gateway</MenuItem>
            </Select>
          </FormControl>
        </Stack>

        <FormControl fullWidth size="small">
          <InputLabel>Template</InputLabel>
          <Select
            value={templateId}
            label="Template"
            onChange={(e) => handleTemplateChange(e.target.value as number | '')}
            disabled={loading}
          >
            <MenuItem value="">Write a custom message</MenuItem>
            {templates.map((template) => (
              <MenuItem key={template.id} value={template.id}>
                {template.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <Box>
          <Typography sx={{ fontWeight: 600, fontSize: '0.875rem', color: '#1f2937' }}>
            Message{' '}
            <Box component="span" sx={{ color: '#d32f2f' }}>
              *
            </Box>
          </Typography>
          <Typography sx={{ fontSize: '0.78rem', color: '#6b7280', mt: 0.5, mb: 1.5 }}>
            Type a message or pick a template. Candidate fields like {'{{full_name}}'} are filled in at send time.
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
              '&::placeholder': {
                color: '#9e9e9e',
                fontStyle: 'normal',
              },
            }}
          />
          {contentError && (
            <Typography sx={{ color: '#d32f2f', fontSize: '0.75rem', mt: 0.5 }}>
              {contentError}
            </Typography>
          )}
        </Box>

        {preview && recipientList.length === 1 && preview !== content && (
          <Box sx={{ backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '4px', p: 1.5 }}>
            <Typography sx={{ fontSize: '0.75rem', fontWeight: 600, color: '#64748b', mb: 0.5 }}>
              Preview for {recipientList[0].full_name}
            </Typography>
            <Typography sx={{ fontSize: '0.8125rem', color: '#1f2937', whiteSpace: 'pre-wrap' }}>
              {preview}
            </Typography>
          </Box>
        )}

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

      <Box
        sx={{
          px: 3.5,
          pb: 3.5,
          pt: 2,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
          gap: 1.5,
        }}
      >
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
            '&:hover': {
              borderColor: '#42a5f5',
              backgroundColor: '#f4f9ff',
            },
          }}
        >
          Cancel
        </Button>
        <Button
          id="submit-send-message-btn"
          onClick={handleSend}
          variant="contained"
          disabled={loading || !content.trim()}
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
            '&:hover': {
              backgroundColor: content.trim() ? '#1565c0' : '#e0e0e0',
              boxShadow: 'none',
            },
            '&.Mui-disabled': {
              backgroundColor: '#e0e0e0',
              color: '#9e9e9e',
            },
          }}
        >
          {loading ? (
            <CircularProgress size={18} color="inherit" />
          ) : scheduledAt ? (
            'Schedule Message'
          ) : (
            'Send Message'
          )}
        </Button>
      </Box>
    </Drawer>
  );
}
