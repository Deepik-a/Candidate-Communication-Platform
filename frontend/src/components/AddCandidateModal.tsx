'use client';

import React, { useState, useEffect } from 'react';
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

/** Real-time error validation functions (Requirement #11) */
function validateFullName(val: string): string | undefined {
  const trimmed = val.trim();
  if (!val) {
    return 'Candidate Name is required';
  }
  if (!trimmed) {
    return 'Candidate Name cannot be only spaces';
  }
  // User Requirement: Name should not exceed more than 10 letters
  if (val.length > 10) {
    return `Name should not exceed more than 10 letters (${val.length}/10)`;
  }
  // Name must only contain letters and spaces (no digits, no special characters)
  if (!/^[a-zA-Z\s]+$/.test(val)) {
    return 'Name must contain only alphabetic letters without digits or symbols';
  }
  if (trimmed.length < 2) {
    return 'Name must be at least 2 letters';
  }
  return undefined;
}

function validateMobileNumber(val: string): string | undefined {
  if (!val) {
    return 'Mobile Number is required';
  }
  // Check for alphabets
  if (/[a-zA-Z]/.test(val)) {
    return 'Phone number cannot contain alphabets';
  }
  // User Requirement: Phone no must be 10 digits without special characters/alphabets
  // Allow optional leading "+91" prefix if pasted/typed, but remaining must be exactly 10 digits
  let digits = val;
  if (val.startsWith('+91')) {
    digits = val.slice(3).trim();
  } else if (val.startsWith('+')) {
    digits = val.slice(1).trim();
  }

  // Check for forbidden special characters inside the number
  if (/[^\d]/.test(digits)) {
    return 'Phone number must be 10 digits without special characters/alphabets';
  }

  if (digits.length < 10) {
    return `Phone number must be exactly 10 digits (${digits.length}/10 digits)`;
  }
  if (digits.length > 10) {
    return `Phone number cannot exceed 10 digits (${digits.length} digits entered)`;
  }
  if (!/^[6-9]\d{9}$/.test(digits) && !/^\d{10}$/.test(digits)) {
    return 'Please enter a valid 10-digit mobile number';
  }
  return undefined;
}

function validateEmail(val: string): string | undefined {
  if (!val) {
    return 'Email is required';
  }
  if (val.includes(' ')) {
    return 'Email cannot contain spaces';
  }
  if (val.length > 80) {
    return 'Email cannot exceed 80 characters';
  }
  // Standard strict email pattern
  const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  if (!emailRegex.test(val.trim())) {
    return 'Enter a valid email address (e.g. name@example.com)';
  }
  return undefined;
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
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (open) {
      setFormData({ full_name: '', mobile_number: '', email: '' });
      setErrors({});
      setTouched({});
    }
  }, [open]);

  // Real-time field change validation
  const handleChange = (field: keyof FormData) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setFormData(prev => ({ ...prev, [field]: value }));

    // Run real-time validation immediately as user types
    let err: string | undefined;
    if (field === 'full_name') err = validateFullName(value);
    if (field === 'mobile_number') err = validateMobileNumber(value);
    if (field === 'email') err = validateEmail(value);

    setErrors(prev => ({ ...prev, [field]: err }));
  };

  const handleBlur = (field: keyof FormData) => () => {
    setTouched(prev => ({ ...prev, [field]: true }));
    let err: string | undefined;
    if (field === 'full_name') err = validateFullName(formData.full_name);
    if (field === 'mobile_number') err = validateMobileNumber(formData.mobile_number);
    if (field === 'email') err = validateEmail(formData.email);
    setErrors(prev => ({ ...prev, [field]: err }));
  };

  const validateAll = (): boolean => {
    const errName = validateFullName(formData.full_name);
    const errPhone = validateMobileNumber(formData.mobile_number);
    const errEmail = validateEmail(formData.email);

    const newErrors: FormErrors = {
      full_name: errName,
      mobile_number: errPhone,
      email: errEmail,
    };

    setErrors(newErrors);
    setTouched({ full_name: true, mobile_number: true, email: true });

    return !errName && !errPhone && !errEmail;
  };

  const handleSubmit = async () => {
    if (!validateAll()) return;

    setLoading(true);

    // Format phone cleanly with standard +91 prefix
    let cleanPhone = formData.mobile_number.trim();
    if (!cleanPhone.startsWith('+91')) {
      cleanPhone = `+91 ${cleanPhone.replace(/^\+/, '')}`;
    } else {
      const core = cleanPhone.replace(/^\+91/, '').trim();
      cleanPhone = `+91 ${core}`;
    }

    try {
      await candidatesApi.create({
        full_name: formData.full_name.trim(),
        mobile_number: cleanPhone,
        email: formData.email.trim(),
      });
      showToast('Candidate added successfully', 'success');
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: Record<string, string[] | string> } };
      const data = axiosErr?.response?.data;
      if (data) {
        if (data.mobile_number) {
          const msg = Array.isArray(data.mobile_number) ? data.mobile_number[0] : String(data.mobile_number);
          setErrors(prev => ({ ...prev, mobile_number: msg }));
          showToast(msg, 'error');
          return;
        }
        if (data.email) {
          const msg = Array.isArray(data.email) ? data.email[0] : String(data.email);
          setErrors(prev => ({ ...prev, email: msg }));
          showToast(msg, 'error');
          return;
        }
        if (data.full_name) {
          const msg = Array.isArray(data.full_name) ? data.full_name[0] : String(data.full_name);
          setErrors(prev => ({ ...prev, full_name: msg }));
          showToast(msg, 'error');
          return;
        }
      }
      showToast('Failed to add candidate. Please check input values.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const isFormValid =
    !errors.full_name &&
    !errors.mobile_number &&
    !errors.email &&
    formData.full_name.trim().length > 0 &&
    formData.mobile_number.trim().length > 0 &&
    formData.email.trim().length > 0;

  return (
    <Dialog
      open={open}
      onClose={loading ? undefined : onClose}
      maxWidth="xs"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: '4px',
          boxShadow: '0 10px 25px rgba(0,0,0,0.1)',
          p: 0,
          width: 480,
          maxWidth: '92vw',
        },
      }}
    >
      {/* Exact Header matching Screenshot 3 */}
      <DialogTitle
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          pt: 3,
          px: 3.5,
          pb: 1.5,
        }}
      >
        <Typography
          variant="h6"
          sx={{
            fontWeight: 700,
            fontSize: '1.15rem',
            color: '#1a1a2e',
            letterSpacing: '-0.01em',
          }}
        >
          Add Candidate
        </Typography>
        <IconButton
          onClick={onClose}
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
      </DialogTitle>

      {/* Exact Fields matching Screenshot 3 */}
      <DialogContent sx={{ px: 3.5, py: 1.5 }}>
        <Stack spacing={2.5} sx={{ pt: 1 }}>
          {/* Candidate Name * */}
          <TextField
            id="add-candidate-name-input"
            label={
              <span>
                Candidate Name <span style={{ color: '#d32f2f' }}>*</span>
              </span>
            }
            value={formData.full_name}
            onChange={handleChange('full_name')}
            onBlur={handleBlur('full_name')}
            error={!!errors.full_name && touched.full_name}
            helperText={touched.full_name ? errors.full_name : ''}
            placeholder="e.g. Taylor"
            fullWidth
            size="medium"
            disabled={loading}
            inputProps={{ maxLength: 15 }}
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: '4px',
                fontSize: '0.875rem',
                '& fieldset': {
                  borderColor: !!errors.full_name && touched.full_name ? '#d32f2f' : '#cfd8dc',
                },
                '&:hover fieldset': {
                  borderColor: !!errors.full_name && touched.full_name ? '#d32f2f' : '#90a4ae',
                },
                '&.Mui-focused fieldset': {
                  borderColor: !!errors.full_name && touched.full_name ? '#d32f2f' : '#1976d2',
                },
              },
              '& .MuiInputLabel-root': {
                fontSize: '0.875rem',
                color: '#546e7a',
              },
              '& .MuiFormHelperText-root': {
                fontSize: '0.75rem',
                mx: 0.5,
              },
            }}
          />

          {/* Mobile Number * */}
          <TextField
            id="add-candidate-phone-input"
            label={
              <span>
                Mobile Number <span style={{ color: '#d32f2f' }}>*</span>
              </span>
            }
            value={formData.mobile_number}
            onChange={handleChange('mobile_number')}
            onBlur={handleBlur('mobile_number')}
            error={!!errors.mobile_number && touched.mobile_number}
            helperText={touched.mobile_number ? errors.mobile_number : ''}
            placeholder="+919876543210"
            fullWidth
            size="medium"
            disabled={loading}
            inputProps={{ maxLength: 14 }}
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: '4px',
                fontSize: '0.875rem',
                '& fieldset': {
                  borderColor: !!errors.mobile_number && touched.mobile_number ? '#d32f2f' : '#cfd8dc',
                },
                '&:hover fieldset': {
                  borderColor: !!errors.mobile_number && touched.mobile_number ? '#d32f2f' : '#90a4ae',
                },
                '&.Mui-focused fieldset': {
                  borderColor: !!errors.mobile_number && touched.mobile_number ? '#d32f2f' : '#1976d2',
                },
              },
              '& .MuiInputLabel-root': {
                fontSize: '0.875rem',
                color: '#546e7a',
              },
              '& .MuiFormHelperText-root': {
                fontSize: '0.75rem',
                mx: 0.5,
              },
            }}
          />

          {/* Email * */}
          <TextField
            id="add-candidate-email-input"
            label={
              <span>
                Email <span style={{ color: '#d32f2f' }}>*</span>
              </span>
            }
            value={formData.email}
            onChange={handleChange('email')}
            onBlur={handleBlur('email')}
            error={!!errors.email && touched.email}
            helperText={touched.email ? errors.email : ''}
            placeholder="taylor.swift@gmail.com"
            fullWidth
            size="medium"
            type="email"
            disabled={loading}
            inputProps={{ maxLength: 80 }}
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: '4px',
                fontSize: '0.875rem',
                '& fieldset': {
                  borderColor: !!errors.email && touched.email ? '#d32f2f' : '#cfd8dc',
                },
                '&:hover fieldset': {
                  borderColor: !!errors.email && touched.email ? '#d32f2f' : '#90a4ae',
                },
                '&.Mui-focused fieldset': {
                  borderColor: !!errors.email && touched.email ? '#d32f2f' : '#1976d2',
                },
              },
              '& .MuiInputLabel-root': {
                fontSize: '0.875rem',
                color: '#546e7a',
              },
              '& .MuiFormHelperText-root': {
                fontSize: '0.75rem',
                mx: 0.5,
              },
            }}
          />
        </Stack>
      </DialogContent>

      {/* Exact Actions matching Screenshot 3 */}
      <DialogActions sx={{ px: 3.5, pb: 3, pt: 2, gap: 1.5, justifyContent: 'flex-end' }}>
        <Button
          onClick={onClose}
          variant="outlined"
          disabled={loading}
          sx={{
            borderColor: '#90caf9',
            color: '#1976d2',
            textTransform: 'uppercase',
            fontWeight: 500,
            fontSize: '0.8125rem',
            height: 36,
            px: 2.25,
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
          id="add-candidate-submit-btn"
          onClick={handleSubmit}
          variant="contained"
          disabled={loading || !isFormValid}
          sx={{
            backgroundColor: '#1976d2',
            color: '#ffffff',
            textTransform: 'uppercase',
            fontWeight: 600,
            fontSize: '0.8125rem',
            height: 36,
            px: 2.25,
            borderRadius: '4px',
            boxShadow: 'none',
            '&:hover': {
              backgroundColor: '#1565c0',
              boxShadow: 'none',
            },
            '&.Mui-disabled': {
              backgroundColor: '#90caf9',
              color: '#ffffff',
              opacity: 0.7,
            },
          }}
        >
          {loading ? <CircularProgress size={18} color="inherit" /> : 'Add Candidate'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
