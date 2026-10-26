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
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import { communicationsApi } from '@/lib/api';
import { MessageTemplate } from '@/types';
import { useToast } from '@/context/ToastContext';

interface TemplatesDrawerProps {
  open: boolean;
  onClose: () => void;
}

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

  const handleCreate = async () => {
    if (!name.trim() || !content.trim()) return;
    setSaving(true);
    try {
      await communicationsApi.createTemplate({ name: name.trim(), content: content.trim(), channel: 'sms' });
      setName('');
      showToast('Template saved.', 'success');
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
    } catch {
      showToast('Could not delete template.', 'error');
    }
  };

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{ sx: { width: { xs: '100%', sm: 480 }, p: 0 } }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', px: 3.5, pt: 3.5, pb: 2 }}>
        <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1.2rem' }}>
          Message templates
        </Typography>
        <IconButton onClick={onClose} size="small">
          <CloseIcon sx={{ fontSize: 20 }} />
        </IconButton>
      </Box>
      <Box sx={{ px: 3.5, pb: 3, overflowY: 'auto' }}>
        <Typography sx={{ fontSize: '0.8rem', color: '#6b7280', mb: 2 }}>
          Use {'{{full_name}}'}, {'{{candidate_id}}'}, {'{{mobile_number}}'}, and {'{{email}}'}. These are filled in for each candidate when you send.
        </Typography>
        <Stack spacing={1.5} sx={{ mb: 3 }}>
          <TextField size="small" label="Template name" value={name} onChange={(e) => setName(e.target.value)} />
          <TextField
            size="small"
            label="Template content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            multiline
            minRows={3}
          />
          <Button variant="contained" onClick={handleCreate} disabled={saving || !name.trim() || !content.trim()}>
            {saving ? <CircularProgress size={16} color="inherit" /> : 'Save template'}
          </Button>
        </Stack>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress size={24} />
          </Box>
        ) : (
          <Stack spacing={1.5}>
            {templates.map((template) => (
              <Paper key={template.id} variant="outlined" sx={{ p: 1.5, borderRadius: 1.5 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 1 }}>
                  <Box>
                    <Typography sx={{ fontWeight: 600, fontSize: '0.875rem' }}>{template.name}</Typography>
                    <Typography sx={{ fontSize: '0.78rem', color: '#4b5563', whiteSpace: 'pre-wrap', mt: 0.5 }}>
                      {template.content}
                    </Typography>
                  </Box>
                  <IconButton size="small" onClick={() => handleDelete(template.id)}>
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
