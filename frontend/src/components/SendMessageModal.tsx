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
  const [content, setContent] = useState('');
  const [contentError, setContentError] = useState('');

  const handleChannelChange = (e: SelectChangeEvent) => {
    setChannel(e.target.value as MessageChannel);
  };

  const handleClose = () => {
    setChannel('sms');
    setContent('');
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
      await communicationsApi.send({
        candidate_id: candidate.id,
        channel,
        content: content.trim(),
      });
      showToast(`Message sent to ${candidate.full_name} via ${channel.toUpperCase()}!`, 'success');
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
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="body2" color="text.secondary">To:</Typography>
              <Typography variant="body2" sx={{ fontWeight: 600 }}>{candidate.full_name}</Typography>
              <Typography variant="body2" color="text.secondary">({candidate.mobile_number})</Typography>
            </Box>
          )}
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
            label="Message"
            value={content}
            onChange={(e) => {
              setContent(e.target.value);
              if (contentError) setContentError('');
            }}
            error={!!contentError}
            helperText={contentError || `${content.length}/2000 characters`}
            multiline
            rows={5}
            fullWidth
            size="small"
            placeholder="Type your message here..."
            inputProps={{ maxLength: 2000 }}
          />
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
        >
          {loading ? 'Sending...' : 'Send Message'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
