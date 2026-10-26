'use client';

import React, { useEffect, useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Stack,
  Typography,
  IconButton,
  Box,
  Divider,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
  MenuItem,
  Select,
  FormControl,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import PersonIcon from '@mui/icons-material/Person';
import SendIcon from '@mui/icons-material/Send';
import HistoryIcon from '@mui/icons-material/History';
import PhoneIcon from '@mui/icons-material/Phone';
import EmailIcon from '@mui/icons-material/Email';
import BadgeIcon from '@mui/icons-material/Badge';
import { Candidate, Message } from '@/types';
import { communicationsApi } from '@/lib/api';
import { StatusBadge } from './StatusBadge';
import { useToast } from '@/context/ToastContext';

interface CandidateDetailModalProps {
  open: boolean;
  onClose: () => void;
  candidate: Candidate | null;
  onSendMessage: (candidate: Candidate) => void;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'NA';
  return new Date(dateStr).toLocaleString();
}

export function CandidateDetailModal({
  open,
  onClose,
  candidate,
  onSendMessage,
}: CandidateDetailModalProps) {
  const { showToast } = useToast();
  const [messages, setMessages] = useState<Message[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const fetchHistory = React.useCallback(async () => {
    if (!candidate) return;
    setLoadingHistory(true);
    try {
      const history = await communicationsApi.getHistory(candidate.id);
      setMessages(history);
    } catch {
      showToast('Failed to load message history.', 'error');
    } finally {
      setLoadingHistory(false);
    }
  }, [candidate, showToast]);

  useEffect(() => {
    if (open && candidate) {
      fetchHistory();
    } else {
      setMessages([]);
    }
  }, [open, candidate, fetchHistory]);

  const handleStatusChange = async (messageId: number, newStatus: string) => {
    try {
      await communicationsApi.updateStatus(messageId, newStatus);
      showToast(`Status updated to ${newStatus.toUpperCase()}`, 'success');
      fetchHistory();
    } catch {
      showToast('Failed to update message status.', 'error');
    }
  };

  if (!candidate) return null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', pb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <PersonIcon sx={{ color: '#1976d2' }} />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Candidate Profile & Communication History
          </Typography>
        </Box>
        <IconButton onClick={onClose} size="small">
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers>
        <Stack spacing={3}>
          {/* Candidate Basic Information */}
          <Paper
            variant="outlined"
            sx={{
              p: 2.5,
              backgroundColor: '#f8fafc',
              borderRadius: 2,
              border: '1px solid #e2e8f0',
            }}
          >
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={3} alignItems={{ sm: 'center' }} justifyContent="space-between">
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 700, color: '#0f172a' }}>
                  {candidate.full_name}
                </Typography>
                <Stack direction="row" spacing={2} sx={{ mt: 1, flexWrap: 'wrap' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, color: '#475569' }}>
                    <BadgeIcon sx={{ fontSize: 18, color: '#64748b' }} />
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      ID: {candidate.candidate_id}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, color: '#475569' }}>
                    <PhoneIcon sx={{ fontSize: 18, color: '#64748b' }} />
                    <Typography variant="body2">{candidate.mobile_number}</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, color: '#475569' }}>
                    <EmailIcon sx={{ fontSize: 18, color: '#64748b' }} />
                    <Typography variant="body2">{candidate.email || 'No email provided'}</Typography>
                  </Box>
                </Stack>
              </Box>

              <Box sx={{ textAlign: { sm: 'right' } }}>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                  Current Status
                </Typography>
                <Box sx={{ mt: 0.5 }}>
                  <StatusBadge status={candidate.status} />
                </Box>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                  Last Contact: {candidate.last_message_date || 'Never'}
                </Typography>
              </Box>
            </Stack>
          </Paper>

          {/* Communication Journey History */}
          <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <HistoryIcon sx={{ color: '#64748b' }} />
                <Typography variant="subtitle1" sx={{ fontWeight: 600, color: '#1e293b' }}>
                  Communication Journey ({messages.length} message{messages.length !== 1 ? 's' : ''})
                </Typography>
              </Box>
              <Button
                variant="outlined"
                size="small"
                startIcon={<SendIcon sx={{ fontSize: 14 }} />}
                onClick={() => {
                  onClose();
                  onSendMessage(candidate);
                }}
                sx={{
                  borderColor: '#1976d2',
                  color: '#1976d2',
                  textTransform: 'none',
                  fontWeight: 600,
                  fontSize: '0.8rem',
                }}
              >
                Send Message
              </Button>
            </Box>

            {loadingHistory ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                <CircularProgress size={24} />
              </Box>
            ) : messages.length === 0 ? (
              <Paper variant="outlined" sx={{ p: 4, textAlign: 'center', color: '#64748b', borderRadius: 2 }}>
                <Typography variant="body2">No messages sent to this candidate yet.</Typography>
              </Paper>
            ) : (
              <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2, maxHeight: 300 }}>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 600, backgroundColor: '#f8fafc' }}>Channel</TableCell>
                      <TableCell sx={{ fontWeight: 600, backgroundColor: '#f8fafc' }}>Message</TableCell>
                      <TableCell sx={{ fontWeight: 600, backgroundColor: '#f8fafc' }}>Status (Provider)</TableCell>
                      <TableCell sx={{ fontWeight: 600, backgroundColor: '#f8fafc' }}>Sent At</TableCell>
                      <TableCell sx={{ fontWeight: 600, backgroundColor: '#f8fafc' }}>Simulate Status Update</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {messages.map((msg) => (
                      <TableRow key={msg.id} hover>
                        <TableCell sx={{ textTransform: 'uppercase', fontWeight: 600, fontSize: '0.75rem', color: '#475569' }}>
                          {msg.channel}
                        </TableCell>
                        <TableCell sx={{ maxWidth: 220, fontSize: '0.85rem' }}>
                          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                            {msg.content}
                          </Typography>
                          {msg.error_message && (
                            <Typography variant="caption" sx={{ color: '#dc2626', display: 'block', mt: 0.5 }}>
                              {msg.error_message}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={msg.status as any} />
                          {msg.provider && (
                            <Typography variant="caption" sx={{ display: 'block', color: '#94a3b8', fontSize: '0.7rem' }}>
                              {msg.provider}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell sx={{ fontSize: '0.75rem', color: '#64748b' }}>
                          {formatDate(msg.sent_at)}
                        </TableCell>
                        <TableCell>
                          <FormControl size="small" sx={{ minWidth: 110 }}>
                            <Select
                              value={msg.status}
                              onChange={(e) => handleStatusChange(msg.id, e.target.value)}
                              sx={{ fontSize: '0.75rem', height: 28 }}
                            >
                              <MenuItem value="sent" sx={{ fontSize: '0.75rem' }}>Sent</MenuItem>
                              <MenuItem value="delivered" sx={{ fontSize: '0.75rem' }}>Delivered</MenuItem>
                              <MenuItem value="read" sx={{ fontSize: '0.75rem' }}>Read</MenuItem>
                              <MenuItem value="failed" sx={{ fontSize: '0.75rem' }}>Failed</MenuItem>
                            </Select>
                          </FormControl>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Box>
        </Stack>
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button onClick={onClose} variant="outlined" color="inherit">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
}
