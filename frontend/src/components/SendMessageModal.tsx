'use client';

import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Stack,
  CircularProgress,
  Typography,
  IconButton,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  Box,
  Alert,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import SendIcon from '@mui/icons-material/Send';
import HubIcon from '@mui/icons-material/Hub';
import { communicationsApi } from '@/lib/api';
import { useToast } from '@/context/ToastContext';
import { Candidate, MessageChannel } from '@/types';

interface SendMessageModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  candidate: Candidate | null;
}

const channelOptions: { value: MessageChannel; label: string }[] = [
  { value: 'sms', label: 'SMS' },
  { value: 'whatsapp', label: 'WhatsApp' },
  { value: 'email', label: 'Email' },
];

const providerOptions: { value: string; label: string; description: string }[] = [
  {
    value: 'dummy',
    label: 'Dummy Communication Service (Port 9000)',
    description: 'Independent external service with reference IDs, status updates & simulation',
  },
  {
    value: 'whatsapp',
    label: 'Real WhatsApp API / Sandbox',
    description: 'Meta Graph API / WhatsApp Developer Sandbox (wamid.HB...)',
  },
];

export function SendMessageModal({ open, onClose, onSuccess, candidate }: SendMessageModalProps) {
  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [channel, setChannel] = useState<MessageChannel>('sms');
  const [provider, setProvider] = useState<string>('dummy');
  const [content, setContent] = useState('Your interview is scheduled for tomorrow.');
  const [contentError, setContentError] = useState('');

  const handleChannelChange = (e: SelectChangeEvent) => {
    const newChannel = e.target.value as MessageChannel;
    setChannel(newChannel);
    if (newChannel === 'whatsapp') {
      setProvider('whatsapp');
    }
  };

  const handleProviderChange = (e: SelectChangeEvent) => {
    setProvider(e.target.value);
  };

  const handleClose = () => {
    setContent('Your interview is scheduled for tomorrow.');
    setContentError('');
    onClose();
  };

  const handleSend = async () => {
    if (!content.trim()) {
      setContentError('Message content cannot be empty.');
      return;
    }
    if (!candidate) return;

    setLoading(true);
    try {
      const outcome = await communicationsApi.send({
        candidate_id: candidate.id,
        channel,
        content: content.trim(),
        provider,
      });

      if (outcome.success) {
        showToast(
          `Dispatched via ${outcome.provider}! Status: ${outcome.status.toUpperCase()} [ID: ${outcome.provider_message_id}]`,
          'success'
        );
      } else {
        showToast(
          `Delivery failed: ${outcome.error_message || 'Provider error'}`,
          'error'
        );
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
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle
        sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', pb: 1 }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <SendIcon sx={{ color: '#1976d2' }} />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>Send Message</Typography>
        </Box>
        <IconButton onClick={handleClose} size="small">
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent dividers>
        <Stack spacing={2.5} sx={{ pt: 1 }}>
          {candidate && (
            <Box sx={{ p: 1.5, backgroundColor: '#f8fafc', borderRadius: 1.5, border: '1px solid #e2e8f0' }}>
              <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', fontWeight: 600 }}>
                Recipient
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#1e293b' }}>
                  {candidate.full_name}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  ({channel === 'email' && candidate.email ? candidate.email : candidate.mobile_number})
                </Typography>
                <Typography variant="caption" sx={{ ml: 'auto', color: '#64748b', fontWeight: 600 }}>
                  ID: {candidate.candidate_id}
                </Typography>
              </Box>
            </Box>
          )}

          {/* Provider Selection */}
          <FormControl fullWidth size="small">
            <InputLabel id="provider-select-label">Communication Provider</InputLabel>
            <Select
              labelId="provider-select-label"
              id="send-message-provider"
              value={provider}
              label="Communication Provider"
              onChange={handleProviderChange}
            >
              {providerOptions.map(p => (
                <MenuItem key={p.value} value={p.value}>
                  <Box>
                    <Typography variant="body2" fontWeight={600}>{p.label}</Typography>
                    <Typography variant="caption" color="text.secondary">{p.description}</Typography>
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Channel Selection */}
          <FormControl fullWidth size="small">
            <InputLabel id="channel-label">Channel</InputLabel>
            <Select
              labelId="channel-label"
              id="send-message-channel"
              value={channel}
              label="Channel"
              onChange={handleChannelChange}
            >
              {channelOptions.map(opt => (
                <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            id="send-message-content"
            label="Message Content"
            value={content}
            onChange={(e) => {
              setContent(e.target.value);
              if (contentError) setContentError('');
            }}
            error={!!contentError}
            helperText={
              contentError ||
              `${content.length}/2000 characters. Tip: Add [fail] to test failure, [temp_fail] to test 503 outage.`
            }
            multiline
            rows={4}
            fullWidth
            size="small"
            placeholder="Type message to candidate..."
            inputProps={{ maxLength: 2000 }}
          />

          <Alert severity="info" sx={{ fontSize: '0.8rem', py: 0.5 }}>
            {provider === 'whatsapp'
              ? 'Using Real WhatsApp API / Sandbox with authentic wamid message IDs.'
              : 'Using Dummy Independent Communication Service on port 9000 with live status tracking.'}
          </Alert>
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button onClick={handleClose} variant="outlined" color="inherit" disabled={loading}>
          Cancel
        </Button>
        <Button
          id="send-message-submit"
          onClick={handleSend}
          variant="contained"
          disabled={loading}
          startIcon={loading ? <CircularProgress size={16} color="inherit" /> : <SendIcon />}
          sx={{
            backgroundColor: '#1976d2',
            '&:hover': { backgroundColor: '#1565c0' },
          }}
        >
          {loading ? 'Sending...' : 'Send Message'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
