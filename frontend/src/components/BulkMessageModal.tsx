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
  Checkbox,
  FormGroup,
  FormControlLabel,
  Paper,
  Divider,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import SendIcon from '@mui/icons-material/Send';
import GroupIcon from '@mui/icons-material/Group';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import { communicationsApi } from '@/lib/api';
import { useToast } from '@/context/ToastContext';
import { Candidate, MessageChannel, CandidateMessageOutcome } from '@/types';
import { StatusBadge } from './StatusBadge';

interface BulkMessageModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  selectedCandidates: Candidate[];
}

const channelOptions: { value: MessageChannel; label: string }[] = [
  { value: 'sms', label: 'SMS' },
  { value: 'whatsapp', label: 'WhatsApp' },
  { value: 'email', label: 'Email' },
];

export function BulkMessageModal({
  open,
  onClose,
  onSuccess,
  selectedCandidates,
}: BulkMessageModalProps) {
  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [channel, setChannel] = useState<MessageChannel>('sms');
  const [content, setContent] = useState('Your interview is scheduled for tomorrow.');
  const [contentError, setContentError] = useState('');
  
  // Track which candidates remain checked inside modal
  const [activeCandidateIds, setActiveCandidateIds] = useState<number[]>([]);
  
  // After send results
  const [outcomes, setOutcomes] = useState<CandidateMessageOutcome[] | null>(null);

  // Sync active candidates when modal opens
  React.useEffect(() => {
    if (open) {
      setActiveCandidateIds(selectedCandidates.map(c => c.id));
      setOutcomes(null);
      setContent('Your interview is scheduled for tomorrow.');
      setContentError('');
    }
  }, [open, selectedCandidates]);

  const handleChannelChange = (e: SelectChangeEvent) => {
    setChannel(e.target.value as MessageChannel);
  };

  const toggleCandidate = (id: number) => {
    setActiveCandidateIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const handleClose = () => {
    setOutcomes(null);
    onClose();
  };

  const handleSend = async () => {
    if (!content.trim()) {
      setContentError('Message content cannot be empty.');
      return;
    }
    if (activeCandidateIds.length === 0) {
      setContentError('Select at least one candidate.');
      return;
    }

    setLoading(true);
    try {
      const resp = await communicationsApi.bulkSend({
        candidate_ids: activeCandidateIds,
        channel,
        content: content.trim(),
      });

      setOutcomes(resp.outcomes);

      if (resp.failed_count === 0) {
        showToast(
          `Successfully sent message to all ${resp.successful_count} candidate(s)!`,
          'success'
        );
      } else if (resp.successful_count > 0) {
        showToast(
          `Sent to ${resp.successful_count} candidate(s), ${resp.failed_count} failed. Check individual statuses.`,
          'warning'
        );
      } else {
        showToast(`Failed to send message to candidates.`, 'error');
      }

      onSuccess();
    } catch {
      showToast('Error processing bulk message request.', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', pb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <GroupIcon sx={{ color: '#1976d2' }} />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Bulk Messaging ({activeCandidateIds.length} Candidates Selected)
          </Typography>
        </Box>
        <IconButton onClick={handleClose} size="small">
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers>
        <Stack spacing={2.5}>
          {/* Candidates Selector List */}
          <Box>
            <Typography variant="subtitle2" sx={{ fontWeight: 600, color: '#334155', mb: 1 }}>
              Candidates ({activeCandidateIds.length}/{selectedCandidates.length} checked):
            </Typography>
            <Paper
              variant="outlined"
              sx={{
                maxHeight: 160,
                overflowY: 'auto',
                p: 1.5,
                backgroundColor: '#f8fafc',
                borderRadius: 1.5,
              }}
            >
              <FormGroup>
                {selectedCandidates.map(c => {
                  const isChecked = activeCandidateIds.includes(c.id);
                  return (
                    <FormControlLabel
                      key={c.id}
                      control={
                        <Checkbox
                          size="small"
                          checked={isChecked}
                          onChange={() => toggleCandidate(c.id)}
                          sx={{ py: 0.5 }}
                        />
                      }
                      label={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                          <Typography variant="body2" sx={{ fontWeight: isChecked ? 600 : 400 }}>
                            {c.full_name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            ({channel === 'email' && c.email ? c.email : c.mobile_number})
                          </Typography>
                          <Typography variant="caption" sx={{ color: '#64748b' }}>
                            • ID: {c.candidate_id}
                          </Typography>
                        </Box>
                      }
                    />
                  );
                })}
              </FormGroup>
            </Paper>
          </Box>

          {/* Channel Selector */}
          <FormControl fullWidth size="small">
            <InputLabel id="bulk-channel-label">Communication Provider / Channel</InputLabel>
            <Select
              labelId="bulk-channel-label"
              id="bulk-message-channel"
              value={channel}
              label="Communication Provider / Channel"
              onChange={handleChannelChange}
            >
              {channelOptions.map(opt => (
                <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Message Content */}
          <TextField
            id="bulk-message-content"
            label="Message"
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
            placeholder="Your interview is scheduled for tomorrow."
            inputProps={{ maxLength: 2000 }}
          />

          {/* Individual Tracking Results Display */}
          {outcomes && (
            <Box sx={{ mt: 2 }}>
              <Divider sx={{ mb: 2 }} />
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                <span>Individual Candidate Results</span>
                <Typography variant="caption" sx={{ color: '#64748b', fontWeight: 500 }}>
                  (Each message is tracked independently)
                </Typography>
              </Typography>
              <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 220, borderRadius: 1.5 }}>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 600, backgroundColor: '#f1f5f9' }}>Candidate</TableCell>
                      <TableCell sx={{ fontWeight: 600, backgroundColor: '#f1f5f9' }}>Contact</TableCell>
                      <TableCell sx={{ fontWeight: 600, backgroundColor: '#f1f5f9' }}>Result</TableCell>
                      <TableCell sx={{ fontWeight: 600, backgroundColor: '#f1f5f9' }}>Status</TableCell>
                      <TableCell sx={{ fontWeight: 600, backgroundColor: '#f1f5f9' }}>Provider Details</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {outcomes.map(out => {
                      const cand = selectedCandidates.find(c => c.id === out.candidate_id);
                      return (
                        <TableRow key={out.candidate_id}>
                          <TableCell sx={{ fontWeight: 500 }}>{out.candidate_name}</TableCell>
                          <TableCell sx={{ color: '#64748b', fontSize: '0.8rem' }}>
                            {cand?.mobile_number || '—'}
                          </TableCell>
                          <TableCell>
                            {out.success ? (
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, color: '#16a34a' }}>
                                <CheckCircleIcon sx={{ fontSize: 16 }} />
                                <Typography variant="caption" fontWeight={600}>Success</Typography>
                              </Box>
                            ) : (
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, color: '#dc2626' }}>
                                <ErrorIcon sx={{ fontSize: 16 }} />
                                <Typography variant="caption" fontWeight={600}>Failed</Typography>
                              </Box>
                            )}
                          </TableCell>
                          <TableCell>
                            <StatusBadge status={out.status as any} />
                          </TableCell>
                          <TableCell sx={{ fontSize: '0.75rem', color: out.error_message ? '#dc2626' : '#64748b' }}>
                            {out.error_message ? out.error_message : `${out.provider} (${out.provider_message_id})`}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          )}
        </Stack>
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button onClick={handleClose} variant="outlined" color="inherit" disabled={loading}>
          {outcomes ? 'Close' : 'Cancel'}
        </Button>
        {!outcomes && (
          <Button
            id="bulk-send-submit-btn"
            onClick={handleSend}
            variant="contained"
            disabled={loading || activeCandidateIds.length === 0}
            startIcon={loading ? <CircularProgress size={16} color="inherit" /> : <SendIcon />}
            sx={{
              backgroundColor: '#1976d2',
              '&:hover': { backgroundColor: '#1565c0' },
              fontWeight: 600,
            }}
          >
            {loading ? 'Sending...' : `Send to ${activeCandidateIds.length} Candidate${activeCandidateIds.length > 1 ? 's' : ''}`}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
