'use client';

import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { Snackbar, Box, Typography } from '@mui/material';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';

type ToastSeverity = 'success' | 'error' | 'warning' | 'info';

interface ToastMessage {
  message: string;
  severity: ToastSeverity;
}

interface ToastContextValue {
  showToast: (message: string, severity?: ToastSeverity) => void;
  toast: ToastMessage | null;
  open: boolean;
  closeToast: () => void;
  setInlineHandled: (handled: boolean) => void;
}

const ToastContext = createContext<ToastContextValue>({
  showToast: () => {},
  toast: null,
  open: false,
  closeToast: () => {},
  setInlineHandled: () => {},
});

export const useToast = () => useContext(ToastContext);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const [open, setOpen] = useState(false);
  const [inlineHandled, setInlineHandled] = useState(false);

  const showToast = useCallback((message: string, severity: ToastSeverity = 'success') => {
    setToast({ message, severity });
    setOpen(true);
  }, []);

  const handleClose = useCallback(() => setOpen(false), []);

  const severity: ToastSeverity = toast?.severity || 'success';

  return (
    <ToastContext.Provider
      value={{
        showToast,
        toast,
        open,
        closeToast: handleClose,
        setInlineHandled,
      }}
    >
      {children}

      {/* Floating Snackbar fallback when not handled inline */}
      {!inlineHandled && (
        <Snackbar
          open={open}
          autoHideDuration={4000}
          onClose={handleClose}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
          sx={{ mb: 2, mr: 2 }}
        >
          <Box
            onClick={handleClose}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1.25,
              px: 2,
              py: 1.25,
              borderRadius: '4px',
              cursor: 'pointer',
              boxShadow: '0 2px 10px rgba(0,0,0,0.08)',
              ...(severity === 'success' && {
                backgroundColor: '#e8f5e9',
                border: '1px solid #c8e6c9',
                color: '#1e293b',
              }),
              ...(severity === 'error' && {
                backgroundColor: '#ffebee',
                border: '1px solid #ffcdd2',
                color: '#b71c1c',
              }),
              ...(severity === 'warning' && {
                backgroundColor: '#fff8e1',
                border: '1px solid #ffe082',
                color: '#b45309',
              }),
              ...(severity === 'info' && {
                backgroundColor: '#e0f2fe',
                border: '1px solid #bae6fd',
                color: '#0369a1',
              }),
            }}
          >
            {severity === 'success' && (
              <CheckCircleOutlineIcon sx={{ color: '#2e7d32', fontSize: 18 }} />
            )}
            {severity === 'error' && (
              <ErrorOutlineIcon sx={{ color: '#d32f2f', fontSize: 18 }} />
            )}
            {severity === 'warning' && (
              <WarningAmberIcon sx={{ color: '#ed6c02', fontSize: 18 }} />
            )}
            {severity === 'info' && (
              <InfoOutlinedIcon sx={{ color: '#0284c7', fontSize: 18 }} />
            )}

            <Typography
              sx={{
                fontSize: '0.8125rem',
                fontWeight: 500,
                color: severity === 'success' ? '#1e293b' : 'inherit',
                lineHeight: 1.4,
              }}
            >
              {toast?.message}
            </Typography>
          </Box>
        </Snackbar>
      )}
    </ToastContext.Provider>
  );
}
