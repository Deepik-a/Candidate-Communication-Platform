'use client';

import React, { useEffect, useState } from 'react';
import {
  Drawer,
  Box,
  Typography,
  IconButton,
  Button,
  TextField,
  Stack,
  CircularProgress,
  Paper,
  Chip,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import LockIcon from '@mui/icons-material/Lock';
import AddIcon from '@mui/icons-material/Add';
import { communicationsApi } from '@/lib/api';
import { MessageTemplate } from '@/types';
import { useToast } from '@/context/ToastContext';

interface TemplatesDrawerProps {
  open: boolean;
  onClose: () => void;
}

const FIXED_FIELDS = [
  { key: '{{full_name}}', label: 'Full Name', desc: "Candidate's full name" },
  { key: '{{mobile_number}}', label: 'Mobile Number', desc: "Candidate's phone" },
  { key: '{{email}}', label: 'Email', desc: "Candidate's email" },
  { key: '{{candidate_id}}', label: 'Candidate ID', desc: 'Unique candidate code' },
];

export function TemplatesDrawer({ open, onClose }: TemplatesDrawerProps) {
  const { showToast } = useToast();
  const [templates, setTemplates] = useState<MessageTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [name, setName] = useState('');
  const [content, setContent] = useState('Hello {{full_name}}, we will contact you at {{mobile_number}}.');
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      setTemplates(await communicationsApi.listTemplates());
    } catch {
      showToast('Could not load templates.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const insertFixedField = (token: string) => {
    if (content.includes(token)) {
      showToast(`${token} is already included in this template.`, 'info');
      return;
    }
    setContent((prev) => (prev ? `${prev} ${token}` : token));
  };

  const handleCreate = async () => {
    if (!name.trim() || !content.trim()) return;
    setSaving(true);
    try {
      await communicationsApi.createTemplate({ name: name.trim(), content: content.trim(), channel: 'sms' });
      setName('');
      setContent('Hello {{full_name}}, your interview is scheduled.');
      showToast('Template saved successfully.', 'success');
      await load();
    } catch {
      showToast('Could not save template.', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await communicationsApi.deleteTemplate(id);
      setTemplates((prev) => prev.filter((t) => t.id !== id));
      showToast('Template deleted.', 'success');
    } catch {
      showToast('Could not delete template.', 'error');
    }
  };

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{ sx: { width: { xs: '100%', sm: 500 }, p: 0 } }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', px: 3.5, pt: 3.5, pb: 2 }}>
        <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1.2rem', color: '#1a1a2e' }}>
          Message Templates
        </Typography>
        <IconButton onClick={onClose} size="small">
          <CloseIcon sx={{ fontSize: 20 }} />
        </IconButton>
      </Box>

      <Box sx={{ px: 3.5, pb: 3, overflowY: 'auto' }}>
        <Typography sx={{ fontSize: '0.8125rem', color: '#6b7280', mb: 2, lineHeight: 1.5 }}>
          Create reusable templates with <strong>fixed candidate fields</strong>. Recruiters can customize the message text, but fixed candidate fields are automatically populated at dispatch time.
        </Typography>

        {/* ── Fixed Fields Selector ────────────────────────────────────────── */}
        <Box sx={{ mb: 2, p: 2, backgroundColor: '#f8fafc', borderRadius: 2, border: '1px solid #e2e8f0' }}>
          <Typography sx={{ fontSize: '0.75rem', fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.04em', mb: 1, display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <LockIcon sx={{ fontSize: 13, color: '#0284c7' }} /> Select Fixed Fields to Include:
          </Typography>
          <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
            {FIXED_FIELDS.map((f) => {
              const isIncluded = content.includes(f.key);
              return (
                <Chip
                  key={f.key}
                  icon={isIncluded ? <LockIcon sx={{ fontSize: '14px !important' }} /> : <AddIcon sx={{ fontSize: '14px !important' }} />}
                  label={f.label}
                  clickable
                  onClick={() => insertFixedField(f.key)}
                  color={isIncluded ? 'primary' : 'default'}
                  variant={isIncluded ? 'filled' : 'outlined'}
                  size="small"
                  sx={{
                    fontWeight: 600,
                    fontSize: '0.75rem',
                    cursor: 'pointer',
                    '&:hover': { backgroundColor: isIncluded ? '#1565c0' : '#e0f2fe' },
                  }}
                />
              );
            })}
          </Stack>
        </Box>

        <Stack spacing={2} sx={{ mb: 3 }}>
          <TextField
            size="small"
            label="Template Name"
            placeholder="e.g., Interview Confirmation"
            value={name}
            onChange={(e) => setName(e.target.value)}
            fullWidth
          />
          <TextField
            size="small"
            label="Template Content (Edit text freely)"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            multiline
            minRows={4}
            fullWidth
            helperText="Fixed fields like {{full_name}} or {{mobile_number}} will be locked and dynamically replaced for each candidate."
          />
          <Button
            variant="contained"
            onClick={handleCreate}
            disabled={saving || !name.trim() || !content.trim()}
            sx={{ textTransform: 'none', fontWeight: 600, py: 1 }}
          >
            {saving ? <CircularProgress size={16} color="inherit" /> : 'Save Template'}
          </Button>
        </Stack>

        <Typography sx={{ fontSize: '0.875rem', fontWeight: 700, color: '#1f2937', mb: 1.5 }}>
          Saved Templates ({templates.length})
        </Typography>

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress size={24} />
          </Box>
        ) : templates.length === 0 ? (
          <Typography sx={{ fontSize: '0.8125rem', color: '#94a3b8', fontStyle: 'italic' }}>
            No saved templates yet. Create your first template above.
          </Typography>
        ) : (
          <Stack spacing={1.5}>
            {templates.map((template) => (
              <Paper key={template.id} variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 1 }}>
                  <Box sx={{ flex: 1 }}>
                    <Typography sx={{ fontWeight: 600, fontSize: '0.875rem', color: '#111827' }}>
                      {template.name}
                    </Typography>
                    <Typography sx={{ fontSize: '0.8125rem', color: '#4b5563', whiteSpace: 'pre-wrap', mt: 0.75, lineHeight: 1.5 }}>
                      {template.content}
                    </Typography>
                    {/* Active fixed fields badges */}
                    <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap', mt: 1.25 }}>
                      {FIXED_FIELDS.filter((f) => template.content.includes(f.key)).map((f) => (
                        <Chip
                          key={f.key}
                          icon={<LockIcon sx={{ fontSize: '11px !important', color: '#0284c7' }} />}
                          label={f.label}
                          size="small"
                          sx={{ fontSize: '0.68rem', height: 20, backgroundColor: '#eff6ff', color: '#0369a1', fontWeight: 600 }}
                        />
                      ))}
                    </Box>
                  </Box>
                  <IconButton size="small" onClick={() => handleDelete(template.id)} sx={{ color: '#ef4444' }}>
                    <DeleteOutlineIcon fontSize="small" />
                  </IconButton>
                </Box>
              </Paper>
            ))}
          </Stack>
        )}
      </Box>
    </Drawer>
  );
}
