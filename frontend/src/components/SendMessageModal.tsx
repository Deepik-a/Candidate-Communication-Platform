'use client';

import React, { useState } from 'react';
import {
  Drawer,
  Box,
  Typography,
  IconButton,
  Button,
  Stack,
  CircularProgress,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';

import { communicationsApi } from '@/lib/api';
import { useToast } from '@/context/ToastContext';
import { Candidate } from '@/types';

interface SendMessageModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  candidate: Candidate | null;
  recipients?: Candidate[];
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

  // Determine recipient list
  const recipientList: Candidate[] =
    recipients.length > 0 ? recipients : candidate ? [candidate] : [];

  const handleClose = () => {
    if (loading) return;
    setContent('');
    setContentError('');
    onClose();
  };

  const handleSend = async () => {
    if (!content.trim()) {
      setContentError('Message content cannot be empty.');
      return;
    }
    if (recipientList.length === 0) return;

    setLoading(true);
    setContentError('');

    try {
      if (recipientList.length === 1) {
        const target = recipientList[0];
        await communicationsApi.send({
          candidate_id: target.id,
          channel: 'sms',
          content: content.trim(),
        });
        showToast('Message sent to 1 candidate', 'success');
      } else {
        await communicationsApi.bulkSend({
          candidate_ids: recipientList.map((r) => r.id),
          channel: 'sms',
          content: content.trim(),
        });
        showToast(`Message sent to ${recipientList.length} candidates`, 'success');
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
      {/* ── Top Header matching Screenshot ───────────────────────────────── */}
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

      {/* ── Body matching Screenshot ───────────────────────────────────────── */}
      <Box
        sx={{
          px: 3.5,
          py: 1,
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          gap: 3.5,
        }}
      >
        {/* Recipient Section */}
        <Box>
          <Typography
            sx={{
              fontWeight: 600,
              fontSize: '0.875rem',
              color: '#1f2937',
              mb: 1,
            }}
          >
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

        {/* Message Field Section */}
        <Box>
          <Typography
            sx={{
              fontWeight: 600,
              fontSize: '0.875rem',
              color: '#1f2937',
            }}
          >
            Message{' '}
            <Box component="span" sx={{ color: '#d32f2f' }}>
              *
            </Box>
          </Typography>
          <Typography
            sx={{
              fontSize: '0.78rem',
              color: '#6b7280',
              mt: 0.5,
              mb: 1.5,
            }}
          >
            Type, or paste the message you want to send.
          </Typography>

          {/* Dev note: Use the text area component here, so the box can be resized. */}
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
              minHeight: 160,
              border: contentError ? '1px solid #d32f2f' : '1px solid #cfd8dc',
              borderRadius: '4px',
              p: 1.5,
              fontSize: '0.875rem',
              fontFamily: 'inherit',
              color: '#1f2937',
              resize: 'both', // Resizable component strictly following dev note
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
      </Box>

      {/* ── Footer Actions matching Screenshot ─────────────────────────────── */}
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
          {loading ? <CircularProgress size={18} color="inherit" /> : 'Send Message'}
        </Button>
      </Box>
    </Drawer>
  );
}
