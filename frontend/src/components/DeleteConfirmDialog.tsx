'use client';

import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  IconButton,
  CircularProgress,
  Stack,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';

interface DeleteConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  loading?: boolean;
  candidateNames: string[];
}

export function DeleteConfirmDialog({
  open,
  onClose,
  onConfirm,
  loading = false,
  candidateNames = [],
}: DeleteConfirmDialogProps) {
  const isMultiple = candidateNames.length > 1;
  const candidateNamesStr = candidateNames.join(', ');

  return (
    <Dialog
      open={open}
      onClose={loading ? undefined : onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: '4px',
          boxShadow: '0 10px 25px rgba(0,0,0,0.1)',
          p: 0,
          width: 580,
          maxWidth: '94vw',
          minHeight: 290,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
        },
      }}
    >
      {/* Title & Close button matching Screenshot 1 */}
      <DialogTitle
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          pt: 3.5,
          px: 4,
          pb: 1,
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
          Delete Candidate
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

      {/* Body Copy matching Screenshot 1 with candidate name and generous spacing */}
      <DialogContent sx={{ px: 4, pt: 3.5, pb: 8, flex: 1 }}>
        <Stack spacing={1.5} sx={{ mt: 1 }}>
          <Typography
            sx={{
              fontWeight: 600,
              fontSize: '0.875rem',
              color: '#1f2937',
              lineHeight: 1.4,
            }}
          >
            {isMultiple
              ? `Are you sure you want to delete ${candidateNames.length} Candidates?`
              : 'Are you sure you want to delete this Candidate?'}
          </Typography>
          <Typography
            sx={{
              fontWeight: 400,
              fontSize: '0.8125rem',
              color: '#6b7280',
              lineHeight: 1.5,
            }}
          >
            {isMultiple
              ? "This action cannot be undone, and you'll lose all communication history with these candidates"
              : `This action cannot be undone, and you'll lose all communication history with ${candidateNames[0] || 'this candidate'}.`}
          </Typography>
        </Stack>
      </DialogContent>

      {/* Actions matching Screenshot 1 */}
      <DialogActions sx={{ px: 3.5, pb: 3, pt: 2.5, gap: 1.5, justifyContent: 'flex-end' }}>
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
          id="confirm-delete-btn"
          onClick={onConfirm}
          variant="contained"
          disabled={loading}
          sx={{
            backgroundColor: '#d32f2f',
            color: '#ffffff',
            textTransform: 'uppercase',
            fontWeight: 600,
            fontSize: '0.8125rem',
            height: 36,
            px: 2.25,
            borderRadius: '4px',
            boxShadow: 'none',
            '&:hover': {
              backgroundColor: '#b71c1c',
              boxShadow: 'none',
            },
            '&.Mui-disabled': {
              backgroundColor: '#ef9a9a',
              color: '#ffffff',
            },
          }}
        >
          {loading ? (
            <CircularProgress size={18} color="inherit" />
          ) : isMultiple ? (
            `DELETE ${candidateNames.length} CANDIDATES`
          ) : (
            'DELETE CANDIDATE'
          )}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
