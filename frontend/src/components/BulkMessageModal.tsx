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
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  LinearProgress,
  Tabs,
  Tab,
  Chip,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import SendIcon from '@mui/icons-material/Send';
import GroupIcon from '@mui/icons-material/Group';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import ReplayIcon from '@mui/icons-material/Replay';
import WhatsAppIcon from '@mui/icons-material/WhatsApp';
import SmsIcon from '@mui/icons-material/Sms';
import MailOutlineIcon from '@mui/icons-material/MailOutline';

import { communicationsApi } from '@/lib/api';
import { useToast } from '@/context/ToastContext';
import { Candidate, MessageChannel, CandidateMessageOutcome, MessageTemplate } from '@/types';
import { StatusBadge } from './StatusBadge';

interface BulkMessageModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  selectedCandidates: Candidate[];
}

const channelOptions: { value: MessageChannel; label: string; icon: React.ReactElement }[] = [
  { value: 'sms', label: 'SMS', icon: <SmsIcon sx={{ fontSize: 16, color: '#0284c7' }} /> },
  { value: 'whatsapp', label: 'WhatsApp', icon: <WhatsAppIcon sx={{ fontSize: 16, color: '#25D366' }} /> },
  { value: 'email', label: 'Email', icon: <MailOutlineIcon sx={{ fontSize: 16, color: '#7c3aed' }} /> },
];

const providerOptions: { value: string; label: string; description: string }[] = [
  {
    value: 'dummy',
    label: 'Dummy Communication Service (Port 9000)',
    description: 'Independent service with reference IDs, status updates & independent tracking',
  },
  {
    value: 'whatsapp',
    label: 'Real WhatsApp API / Sandbox',
    description: 'Meta Graph API / WhatsApp Developer Sandbox',
  },
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
  const [provider, setProvider] = useState<string>('dummy');
  const [content, setContent] = useState('Your interview is scheduled for tomorrow.');
  const [contentError, setContentError] = useState('');
  const [requestError, setRequestError] = useState<string | null>(null);
  const [templates, setTemplates] = useState<MessageTemplate[]>([]);
  const [templateId, setTemplateId] = useState<number | ''>('');
  const [scheduledAt, setScheduledAt] = useState('');

  // Track which candidates remain checked inside modal
  const [activeCandidateIds, setActiveCandidateIds] = useState<number[]>([]);

  // After send results
  const [outcomes, setOutcomes] = useState<CandidateMessageOutcome[] | null>(null);
  const [resultFilter, setResultFilter] = useState<'all' | 'success' | 'failed'>('all');

  // Sync active candidates when modal opens
  React.useEffect(() => {
    if (open) {
      setActiveCandidateIds(selectedCandidates.map(c => c.id));
      setOutcomes(null);
      setContent('Your interview is scheduled for tomorrow.');
      setContentError('');
      setRequestError(null);
      setResultFilter('all');
      setTemplateId('');
      setScheduledAt('');
      communicationsApi.listTemplates().then(setTemplates).catch(() => setTemplates([]));
    }
  }, [open, selectedCandidates]);

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

  const toggleCandidate = (id: number) => {
    setActiveCandidateIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const handleClose = () => {
    if (loading) return;
    setOutcomes(null);
    setRequestError(null);
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
    setRequestError(null);

    try {
      const scheduledIso = scheduledAt ? new Date(scheduledAt).toISOString() : null;
      const resp = await communicationsApi.bulkSend({
        candidate_ids: activeCandidateIds,
        channel,
        content: content.trim(),
        provider,
        scheduled_at: scheduledIso,
        template_id: templateId || null,
      });

      setOutcomes(resp.outcomes);

      if (resp.failed_count === 0) {
        showToast(
          `Successfully dispatched to all ${resp.successful_count} candidate(s) via ${provider.toUpperCase()}!`,
          'success'
        );
      } else if (resp.successful_count > 0) {
        showToast(
          `Dispatched to ${resp.successful_count} candidate(s); ${resp.failed_count} encountered delivery issues. Review results breakdown below.`,
          'warning'
        );
      } else {
        showToast(`All ${resp.failed_count} message dispatches failed. Review failure reasons below.`, 'error');
      }

      onSuccess();
    } catch {
      // Failed request handling (Requirement #11)
      setRequestError('Request failed: Unable to connect to the backend server or communication gateway. Please verify network status.');
      showToast('Error processing bulk message request.', 'error');
    } finally {
      setLoading(false);
    }
  };

  // Retry only failed candidates
  const handleRetryFailed = () => {
    if (!outcomes) return;
    const failedIds = outcomes.filter(o => !o.success).map(o => o.candidate_id);
    setActiveCandidateIds(failedIds);
    setOutcomes(null);
    setResultFilter('all');
  };

  const filteredOutcomes = outcomes
    ? outcomes.filter(o => {
        if (resultFilter === 'success') return o.success;
        if (resultFilter === 'failed') return !o.success;
        return true;
      })
    : [];

  const successfulCount = outcomes ? outcomes.filter(o => o.success).length : 0;
  const failedCount = outcomes ? outcomes.filter(o => !o.success).length : 0;

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth PaperProps={{ sx: { borderRadius: 2.5 } }}>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', pb: 1, pt: 2, px: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25 }}>
          <Box sx={{ width: 34, height: 34, borderRadius: '50%', backgroundColor: '#eff6ff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <GroupIcon sx={{ color: '#0284c7', fontSize: 20 }} />
          </Box>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 700, color: '#0f172a', lineHeight: 1.2 }}>
              {outcomes ? 'Bulk Messaging Results Breakdown' : `Bulk Messaging (${activeCandidateIds.length} Selected)`}
            </Typography>
            <Typography variant="caption" sx={{ color: '#64748b' }}>
              {outcomes ? 'Independent per-candidate delivery outcomes & status tracking' : 'Dispatch message independently to each selected candidate'}
            </Typography>
          </Box>
        </Box>
        <IconButton onClick={handleClose} size="small" disabled={loading}>
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      {/* Sending progress bar (Requirement #11) */}
      {loading && (
        <LinearProgress
          sx={{ height: 3, backgroundColor: '#e0f2fe', '& .MuiLinearProgress-bar': { backgroundColor: '#0284c7' } }}
        />
      )}

      <DialogContent dividers sx={{ p: 3 }}>
        <Stack spacing={2.5}>
          {/* Failed Request Alert Banner (Requirement #11) */}
          {requestError && (
            <Alert
              severity="error"
              action={
                <Button color="inherit" size="small" onClick={handleSend} disabled={loading} sx={{ textTransform: 'none', fontWeight: 600 }}>
                  Retry
                </Button>
              }
              sx={{ borderRadius: 2 }}
            >
              {requestError}
            </Alert>
          )}

          {!outcomes ? (
            /* ── DISPATCH FORM STEP ─────────────────────────────────────────── */
            <>
              {/* Candidates Selector List */}
              <Box>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#1e293b' }}>
                    Recipients ({activeCandidateIds.length}/{selectedCandidates.length} checked):
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#64748b' }}>
                    Uncheck any candidate you wish to exclude
                  </Typography>
                </Box>
                <Paper
                  variant="outlined"
                  sx={{
                    maxHeight: 160,
                    overflowY: 'auto',
                    p: 1.5,
                    backgroundColor: '#f8fafc',
                    borderRadius: 2,
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
                              disabled={loading}
                              sx={{ py: 0.5, color: '#94a3b8', '&.Mui-checked': { color: '#0284c7' } }}
                            />
                          }
                          label={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                              <Typography variant="body2" sx={{ fontWeight: isChecked ? 600 : 400, color: isChecked ? '#0f172a' : '#64748b' }}>
                                {c.full_name}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                ({channel === 'email' && c.email ? c.email : c.mobile_number})
                              </Typography>
                              <Typography variant="caption" sx={{ color: '#94a3b8' }}>
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

              {/* Provider Selector */}
              <FormControl fullWidth size="small" disabled={loading}>
                <InputLabel id="bulk-provider-label">Communication Provider</InputLabel>
                <Select
                  labelId="bulk-provider-label"
                  id="bulk-message-provider"
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

              {/* Channel Selector */}
              <FormControl fullWidth size="small" disabled={loading}>
                <InputLabel id="bulk-channel-label">Channel</InputLabel>
                <Select
                  labelId="bulk-channel-label"
                  id="bulk-message-channel"
                  value={channel}
                  label="Channel"
                  onChange={handleChannelChange}
                >
                  {channelOptions.map(opt => (
                    <MenuItem key={opt.value} value={opt.value}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {opt.icon}
                        <Typography variant="body2">{opt.label}</Typography>
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl fullWidth size="small" disabled={loading}>
                <InputLabel>Template</InputLabel>
                <Select
                  value={templateId}
                  label="Template"
                  onChange={(e) => {
                    const value = e.target.value as number | '';
                    setTemplateId(value);
                    const selected = templates.find((t) => t.id === value);
                    if (selected) setContent(selected.content);
                  }}
                >
                  <MenuItem value="">Write a custom message</MenuItem>
                  {templates.map((template) => (
                    <MenuItem key={template.id} value={template.id}>
                      {template.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {/* Message Content */}
              <TextField
                id="bulk-message-content"
                label="Message Content"
                value={content}
                onChange={(e) => {
                  setContent(e.target.value);
                  if (contentError) setContentError('');
                }}
                disabled={loading}
                error={!!contentError}
                helperText={
                  contentError ||
                  `${content.length}/2000 characters. Use {{full_name}} and other candidate fields. Each send is tracked independently.`
                }
                multiline
                rows={4}
                fullWidth
                size="small"
                placeholder="Type your bulk notification content here..."
                inputProps={{ maxLength: 2000 }}
              />

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
            </>
          ) : (
            /* ── RESULTS BREAKDOWN STEP (Requirement #11) ─────────────────────── */
            <Box>
              {/* Summary Metrics Cards */}
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2.5 }}>
                <Paper variant="outlined" sx={{ flex: 1, p: 2, textAlign: 'center', borderRadius: 2, backgroundColor: '#f8fafc' }}>
                  <Typography variant="caption" sx={{ color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>
                    Total Dispatched
                  </Typography>
                  <Typography variant="h5" sx={{ fontWeight: 800, color: '#0f172a', mt: 0.5 }}>
                    {outcomes.length}
                  </Typography>
                </Paper>

                <Paper variant="outlined" sx={{ flex: 1, p: 2, textAlign: 'center', borderRadius: 2, backgroundColor: '#f0fdf4', borderColor: '#bbf7d0' }}>
                  <Typography variant="caption" sx={{ color: '#166534', fontWeight: 600, textTransform: 'uppercase' }}>
                    Successfully Sent
                  </Typography>
                  <Typography variant="h5" sx={{ fontWeight: 800, color: '#16a34a', mt: 0.5 }}>
                    {successfulCount}
                  </Typography>
                </Paper>

                <Paper variant="outlined" sx={{ flex: 1, p: 2, textAlign: 'center', borderRadius: 2, backgroundColor: failedCount > 0 ? '#fef2f2' : '#f8fafc', borderColor: failedCount > 0 ? '#fecaca' : '#e2e8f0' }}>
                  <Typography variant="caption" sx={{ color: failedCount > 0 ? '#991b1b' : '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>
                    Failed Dispatches
                  </Typography>
                  <Typography variant="h5" sx={{ fontWeight: 800, color: failedCount > 0 ? '#dc2626' : '#64748b', mt: 0.5 }}>
                    {failedCount}
                  </Typography>
                </Paper>
              </Stack>

              {/* Filter Tabs */}
              <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
                <Tabs value={resultFilter} onChange={(_, val) => setResultFilter(val)}>
                  <Tab value="all" label={`All Results (${outcomes.length})`} sx={{ textTransform: 'none', fontWeight: 600, fontSize: '0.8rem' }} />
                  <Tab value="success" label={`Successful (${successfulCount})`} sx={{ textTransform: 'none', fontWeight: 600, fontSize: '0.8rem', color: '#16a34a' }} />
                  <Tab value="failed" label={`Failed (${failedCount})`} sx={{ textTransform: 'none', fontWeight: 600, fontSize: '0.8rem', color: '#dc2626' }} />
                </Tabs>
              </Box>

              {/* Individual Candidate Table */}
              <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 260, borderRadius: 2 }}>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 600, backgroundColor: '#f8fafc' }}>Candidate</TableCell>
                      <TableCell sx={{ fontWeight: 600, backgroundColor: '#f8fafc' }}>Result</TableCell>
                      <TableCell sx={{ fontWeight: 600, backgroundColor: '#f8fafc' }}>Status</TableCell>
                      <TableCell sx={{ fontWeight: 600, backgroundColor: '#f8fafc' }}>Delivery Detail / Failure Reason</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filteredOutcomes.map(out => {
                      return (
                        <TableRow key={out.candidate_id} hover>
                          <TableCell sx={{ fontWeight: 600, color: '#0f172a' }}>
                            {out.candidate_name}
                            <Typography variant="caption" sx={{ display: 'block', color: '#64748b' }}>
                              ID: {out.candidate_code}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            {out.success ? (
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, color: '#16a34a' }}>
                                <CheckCircleIcon sx={{ fontSize: 16 }} />
                                <Typography variant="caption" fontWeight={700}>Dispatched</Typography>
                              </Box>
                            ) : (
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, color: '#dc2626' }}>
                                <ErrorOutlineIcon sx={{ fontSize: 16 }} />
                                <Typography variant="caption" fontWeight={700}>Failed</Typography>
                              </Box>
                            )}
                          </TableCell>
                          <TableCell>
                            <StatusBadge status={out.status as any} />
                          </TableCell>
                          <TableCell sx={{ fontSize: '0.8rem', color: out.error_message ? '#b91c1c' : '#475569' }}>
                            {out.error_message ? (
                              <Box>
                                <Typography variant="caption" sx={{ color: '#dc2626', fontWeight: 600, display: 'block' }}>
                                  {out.error_message}
                                </Typography>
                                {out.failure_category && (
                                  <Chip
                                    label={out.failure_category.replace(/_/g, ' ')}
                                    size="small"
                                    sx={{ height: 18, fontSize: '0.65rem', backgroundColor: '#fee2e2', color: '#991b1b', mt: 0.5 }}
                                  />
                                )}
                              </Box>
                            ) : (
                              <Typography variant="caption" sx={{ color: '#64748b' }}>
                                Ref ID: {out.provider_message_id || 'Accepted'} via {out.provider}
                              </Typography>
                            )}
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
        <Button onClick={handleClose} variant="outlined" color="inherit" disabled={loading} sx={{ textTransform: 'none', fontWeight: 600 }}>
          {outcomes ? 'Close' : 'Cancel'}
        </Button>

        {/* Retry Failed button if there are failures (Requirement #11) */}
        {outcomes && failedCount > 0 && (
          <Button
            variant="outlined"
            color="error"
            startIcon={<ReplayIcon sx={{ fontSize: 16 }} />}
            onClick={handleRetryFailed}
            sx={{ textTransform: 'none', fontWeight: 600 }}
          >
            Retry {failedCount} Failed Candidate{failedCount > 1 ? 's' : ''}
          </Button>
        )}

        {!outcomes && (
          <Button
            id="bulk-send-submit-btn"
            onClick={handleSend}
            variant="contained"
            disabled={loading || activeCandidateIds.length === 0 || !content.trim()}
            startIcon={loading ? <CircularProgress size={16} color="inherit" /> : <SendIcon />}
            sx={{
              backgroundColor: '#0284c7',
              '&:hover': { backgroundColor: '#0369a1' },
              fontWeight: 600,
              textTransform: 'none',
              px: 2.5,
            }}
          >
            {loading ? `Transmitting to ${activeCandidateIds.length}...` : `Send to ${activeCandidateIds.length} Candidate${activeCandidateIds.length > 1 ? 's' : ''}`}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
