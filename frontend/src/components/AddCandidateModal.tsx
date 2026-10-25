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
  Box,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import PersonAddAltIcon from '@mui/icons-material/PersonAddAlt';
import { candidatesApi } from '@/lib/api';
import { useToast } from '@/context/ToastContext';

interface AddCandidateModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

interface FormData {
  full_name: string;
  mobile_number: string;
  email: string;
}

interface FormErrors {
  full_name?: string;
  mobile_number?: string;
  email?: string;
}

export function AddCandidateModal({ open, onClose, onSuccess }: AddCandidateModalProps) {
  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState<FormData>({
    full_name: '',
    mobile_number: '',
    email: '',
  });
  const [errors, setErrors] = useState<FormErrors>({});

  const validate = (): boolean => {
    const newErrors: FormErrors = {};
    if (!formData.full_name.trim()) newErrors.full_name = 'Full name is required';
    if (!formData.mobile_number.trim()) {
      newErrors.mobile_number = 'Mobile number is required';
    } else if (!/^\+?[\d\s\-()]{7,20}$/.test(formData.mobile_number.trim())) {
      newErrors.mobile_number = 'Enter a valid mobile number';
    }
    if (formData.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Enter a valid email address';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (field: keyof FormData) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({ ...prev, [field]: e.target.value }));
    if (errors[field]) setErrors(prev => ({ ...prev, [field]: undefined }));
  };

  const handleSubmit = async () => {
    if (!validate()) return;
    setLoading(true);
    try {
      await candidatesApi.create({
        full_name: formData.full_name.trim(),
        mobile_number: formData.mobile_number.trim(),
        email: formData.email.trim() || undefined,
      });
      showToast('Candidate added successfully!', 'success');
      handleReset();
      onSuccess();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: Record<string, string[]> } };
      const msg =
        axiosErr?.response?.data?.mobile_number?.[0] ||
        axiosErr?.response?.data?.full_name?.[0] ||
        'Failed to add candidate. Please try again.';
      showToast(msg, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setFormData({ full_name: '', mobile_number: '', email: '' });
    setErrors({});
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleReset} maxWidth="sm" fullWidth>
      <DialogTitle
        sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', pb: 1 }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <PersonAddAltIcon sx={{ color: '#1976d2' }} />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>Add New Candidate</Typography>
        </Box>
        <IconButton onClick={handleReset} size="small">
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent dividers>
        <Stack spacing={2.5} sx={{ pt: 1 }}>
          <TextField
            id="add-candidate-full-name"
            label="Full Name"
            value={formData.full_name}
            onChange={handleChange('full_name')}
            error={!!errors.full_name}
            helperText={errors.full_name}
            placeholder="e.g. Krishna Khandelwal"
            fullWidth
            size="small"
            required
          />
          <TextField
            id="add-candidate-mobile"
            label="Mobile Number"
            value={formData.mobile_number}
            onChange={handleChange('mobile_number')}
            error={!!errors.mobile_number}
            helperText={errors.mobile_number}
            placeholder="+91 9876543210"
            fullWidth
            size="small"
            required
          />
          <TextField
            id="add-candidate-email"
            label="Email (Optional)"
            value={formData.email}
            onChange={handleChange('email')}
            error={!!errors.email}
            helperText={errors.email}
            placeholder="candidate@example.com"
            fullWidth
            size="small"
            type="email"
          />
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button onClick={handleReset} variant="outlined" color="inherit" disabled={loading}>
          Cancel
        </Button>
        <Button
          id="add-candidate-submit"
          onClick={handleSubmit}
          variant="contained"
          disabled={loading}
          startIcon={loading ? <CircularProgress size={16} color="inherit" /> : null}
        >
          {loading ? 'Adding...' : 'Add Candidate'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
