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

export function SendMessageModal({ open, onClose, onSuccess, candidate }: SendMessageModalProps) {
  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [channel, setChannel] = useState<MessageChannel>('sms');
  const [content, setContent] = useState('Your interview is scheduled for tomorrow.');
  const [contentError, setContentError] = useState('');

  const handleChannelChange = (e: SelectChangeEvent) => {
    setChannel(e.target.value as MessageChannel);
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
      });

      if (outcome.success) {
        showToast(
          `Message dispatched to ${candidate.full_name} via ${channel.toUpperCase()}! Status: ${outcome.status.toUpperCase()}`,
          'success'
        );
      } else {
        showToast(
          `Message delivery to ${candidate.full_name} failed: ${outcome.error_message || 'Provider error'}`,
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

          <FormControl fullWidth size="small">
            <InputLabel id="channel-label">Communication Provider / Channel</InputLabel>
            <Select
              labelId="channel-label"
              id="send-message-channel"
              value={channel}
              label="Communication Provider / Channel"
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
            helperText={contentError || `${content.length}/2000 characters`}
            multiline
            rows={4}
            fullWidth
            size="small"
            placeholder="Type message to candidate..."
            inputProps={{ maxLength: 2000 }}
          />

          <Alert severity="info" sx={{ fontSize: '0.8rem', py: 0.5 }}>
            Messages are tracked via gateway with real-time status updates (Sent, Delivered, Read, Failed).
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
