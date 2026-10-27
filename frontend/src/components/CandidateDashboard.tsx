'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Button,
  InputAdornment,
  Paper,
  Stack,
  TablePagination,
  TextField,
  Typography,
  Alert,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteForeverIcon from '@mui/icons-material/DeleteForever';
import SendIcon from '@mui/icons-material/Send';
import SearchIcon from '@mui/icons-material/Search';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';

import { candidatesApi, communicationsApi } from '@/lib/api';
import { Candidate, CommunicationHealth } from '@/types';
import { useToast } from '@/context/ToastContext';
import { CandidateTable } from '@/components/CandidateTable';
import { AddCandidateModal } from '@/components/AddCandidateModal';
import { SendMessageModal } from '@/components/SendMessageModal';
import { BulkMessageModal } from '@/components/BulkMessageModal';
import { CandidateDetailModal } from '@/components/CandidateDetailModal';
import { DeleteConfirmDialog } from '@/components/DeleteConfirmDialog';
import { ServiceHealthBar } from '@/components/ServiceHealthBar';
import { TemplatesDrawer } from '@/components/TemplatesDrawer';

type SortField = 'full_name' | 'mobile_number' | 'last_message_date' | 'status' | 'candidate_id';
type SortOrder = 'asc' | 'desc';

export default function CandidateDashboard() {
  const { showToast, toast, open: toastOpen, closeToast, setInlineHandled } = useToast();

  useEffect(() => {
    setInlineHandled(true);
    return () => setInlineHandled(false);
  }, [setInlineHandled]);

  // Data state
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);

  // Pagination
  const [page, setPage] = useState(0); // MUI is 0-indexed
  const [rowsPerPage, setRowsPerPage] = useState(10);

  // Search
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');

  // Sort: null by default preserves the backend's recently added top order (-created_at)
  const [sortField, setSortField] = useState<SortField | null>(null);
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');

  // Selection
  const [selected, setSelected] = useState<number[]>([]);

  // Modal state
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [sendModalOpen, setSendModalOpen] = useState(false);
  const [bulkModalOpen, setBulkModalOpen] = useState(false);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [activeCandidate, setActiveCandidate] = useState<Candidate | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [templatesOpen, setTemplatesOpen] = useState(false);
  const [health, setHealth] = useState<CommunicationHealth | null>(null);

  // Fetch candidates
  const fetchCandidates = useCallback(async () => {
    setLoading(true);
    try {
      const data = await candidatesApi.list({
        search: search || undefined,
        page: page + 1, // Backend is 1-indexed
        page_size: rowsPerPage,
      });
      setCandidates(data.results);
      setTotalCount(data.count);
      setFetchError(null);
    } catch {
      setFetchError('Unable to connect to the backend API server. Please verify that the Django server is running.');
      showToast('Failed to load candidates. Is the backend running?', 'error');
    } finally {
      setLoading(false);
    }
  }, [search, page, rowsPerPage, showToast]);

  useEffect(() => {
    fetchCandidates();
  }, [fetchCandidates]);

  const refreshHealth = useCallback(async () => {
    try {
      await communicationsApi.dispatchScheduled();
      setHealth(await communicationsApi.health());
    } catch {
      setHealth(null);
    }
  }, []);

  // Real-time status sync: silently polls candidate statuses (Sent -> Delivered -> Read) every 5s without UI flicker
  const silentFetchCandidates = useCallback(async () => {
    try {
      const data = await candidatesApi.list({
        search: search || undefined,
        page: page + 1,
        page_size: rowsPerPage,
      });
      setCandidates(data.results);
      setTotalCount(data.count);
    } catch {
      // Silently ignore transient blips during polling
    }
  }, [search, page, rowsPerPage]);

  useEffect(() => {
    refreshHealth();
    const timer = setInterval(refreshHealth, 15000);
    const pollTimer = setInterval(silentFetchCandidates, 5000);
    return () => {
      clearInterval(timer);
      clearInterval(pollTimer);
    };
  }, [refreshHealth, silentFetchCandidates]);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setPage(0);
    }, 350);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // Sort candidates client-side only when a column header has been clicked;
  // otherwise, preserve natural backend ordering (-created_at, recently added at top)
  const sortedCandidates = sortField
    ? [...candidates].sort((a, b) => {
        const aVal = a[sortField] ?? '';
        const bVal = b[sortField] ?? '';
        const cmp = String(aVal).localeCompare(String(bVal));
        return sortOrder === 'asc' ? cmp : -cmp;
      })
    : candidates;

  // Selection handlers
  const handleSelect = (id: number) => {
    setSelected(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const handleSelectAll = (checked: boolean) => {
    setSelected(checked ? candidates.map(c => c.id) : []);
  };

  // Delete handlers
  const handleDeleteClick = () => {
    if (selected.length === 0) {
      showToast('Select at least one candidate to delete.', 'warning');
      return;
    }
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    setDeleteLoading(true);
    try {
      const { deleted } = await candidatesApi.bulkDelete(selected);
      showToast(
        deleted === 1 ? 'Candidate deleted successfully' : `${deleted} candidates succesfully deleted`,
        'success'
      );
      setSelected([]);
      setDeleteDialogOpen(false);
      fetchCandidates();
    } catch {
      showToast('Failed to delete candidates.', 'error');
    } finally {
      setDeleteLoading(false);
    }
  };

  // Send message to single or multiple
  const handleSendClick = () => {
    if (selected.length === 0) {
      showToast('Select at least one candidate to send a message.', 'warning');
      return;
    }

    if (selected.length === 1) {
      const target = candidates.find(c => c.id === selected[0]) ?? null;
      setActiveCandidate(target);
      setSendModalOpen(true);
    } else {
      setActiveCandidate(null);
      setSendModalOpen(true);
    }
  };

  const handleOpenSingleSend = (candidate: Candidate) => {
    setActiveCandidate(candidate);
    setSendModalOpen(true);
  };

  const handleOpenDetail = (candidate: Candidate) => {
    setActiveCandidate(candidate);
    setDetailModalOpen(true);
  };

  // Sort
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      if (sortOrder === 'asc') {
        setSortOrder('desc');
      } else {
        // Reset to default recently added order
        setSortField(null);
        setSortOrder('asc');
      }
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  // Pagination
  const handleChangePage = (_: unknown, newPage: number) => {
    setPage(newPage);
    setSelected([]);
  };

  const handleChangeRowsPerPage = (e: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(e.target.value, 10));
    setPage(0);
    setSelected([]);
  };

  const selectedCandidatesList = candidates.filter(c => selected.includes(c.id));

  return (
    <Box sx={{ minHeight: '100vh', backgroundColor: '#ffffff' }}>
      <Paper
        elevation={0}
        sx={{
          width: '100%',
          backgroundColor: '#ffffff',
          borderRadius: 0,
        }}
      >
        {/* ── Top Header Toolbar matching Screenshots 1 & 2 ─────────────────── */}
        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
          sx={{ px: 3.5, py: 2.5 }}
        >
          {/* Title */}
          <Typography
            variant="h5"
            sx={{
              fontWeight: 700,
              color: '#1a1a2e',
              fontSize: '1.25rem',
              letterSpacing: '-0.02em',
            }}
          >
            Candidate communication
          </Typography>

          {/* Action Buttons matching Screenshots 1 & 2 */}
          <Stack direction="row" alignItems="center" spacing={1.5}>
            <Button
              variant="outlined"
              size="small"
              onClick={() => setTemplatesOpen(true)}
              sx={{
                borderColor: '#90caf9',
                color: '#0288d1',
                fontWeight: 600,
                fontSize: '0.78rem',
                textTransform: 'uppercase',
                height: 36,
                px: 2,
                borderRadius: '4px',
              }}
            >
              Templates
            </Button>

            {/* + ADD CANDIDATE */}
            <Button
              id="add-candidate-btn"
              variant="outlined"
              size="small"
              startIcon={<AddIcon sx={{ fontSize: 18 }} />}
              onClick={() => setAddModalOpen(true)}
              sx={{
                borderColor: '#4fc3f7',
                color: '#0288d1',
                backgroundColor: '#ffffff',
                fontWeight: 600,
                fontSize: '0.78rem',
                textTransform: 'uppercase',
                height: 36,
                px: 2,
                borderRadius: '4px',
                '&:hover': {
                  backgroundColor: '#e1f5fe',
                  borderColor: '#0288d1',
                },
              }}
            >
              + ADD CANDIDATE
            </Button>

            {/* DELETE CANDIDATE */}
            <Button
              id="delete-candidate-btn"
              variant="contained"
              size="small"
              startIcon={<DeleteForeverIcon sx={{ fontSize: 18 }} />}
              onClick={handleDeleteClick}
              disabled={selected.length === 0}
              sx={{
                backgroundColor: selected.length > 0 ? '#1976d2' : '#e0e0e0',
                color: selected.length > 0 ? '#ffffff' : '#757575',
                fontWeight: 600,
                fontSize: '0.78rem',
                textTransform: 'uppercase',
                height: 36,
                px: 2,
                borderRadius: '4px',
                boxShadow: 'none',
                '&:hover': {
                  backgroundColor: selected.length > 0 ? '#1565c0' : '#d5d5d5',
                  boxShadow: 'none',
                },
                '&.Mui-disabled': {
                  backgroundColor: '#e0e0e0',
                  color: '#9e9e9e',
                },
              }}
            >
              DELETE CANDIDATE
            </Button>

            {/* SEND MESSAGE */}
            <Button
              id="send-message-btn"
              variant="contained"
              size="small"
              startIcon={<SendIcon sx={{ fontSize: 16 }} />}
              onClick={handleSendClick}
              disabled={selected.length === 0}
              sx={{
                backgroundColor: selected.length > 0 ? '#1976d2' : '#e0e0e0',
                color: selected.length > 0 ? '#ffffff' : '#757575',
                fontWeight: 600,
                fontSize: '0.78rem',
                textTransform: 'uppercase',
                height: 36,
                px: 2,
                borderRadius: '4px',
                boxShadow: 'none',
                '&:hover': {
                  backgroundColor: selected.length > 0 ? '#1565c0' : '#d5d5d5',
                  boxShadow: 'none',
                },
                '&.Mui-disabled': {
                  backgroundColor: '#e0e0e0',
                  color: '#9e9e9e',
                },
              }}
            >
              SEND MESSAGE
            </Button>

            {/* Search Input Box */}
            <TextField
              id="candidate-search"
              size="small"
              placeholder="Search"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon sx={{ fontSize: 18, color: '#757575' }} />
                  </InputAdornment>
                ),
              }}
              sx={{
                width: 190,
                '& .MuiOutlinedInput-root': {
                  height: 36,
                  borderRadius: '4px',
                  backgroundColor: '#ffffff',
                  fontSize: '0.8125rem',
                  '& fieldset': { borderColor: '#e0e0e0' },
                  '&:hover fieldset': { borderColor: '#bdbdbd' },
                  '&.Mui-focused fieldset': { borderColor: '#1976d2' },
                },
              }}
            />
          </Stack>
        </Stack>

        <ServiceHealthBar health={health} />

        {/* Failed Request Banner */}
        {fetchError && (
          <Box sx={{ px: 3.5, pb: 2 }}>
            <Alert
              severity="error"
              action={
                <Button
                  color="inherit"
                  size="small"
                  onClick={fetchCandidates}
                  disabled={loading}
                  sx={{ textTransform: 'none', fontWeight: 600 }}
                >
                  Retry Connection
                </Button>
              }
              sx={{ borderRadius: '4px' }}
            >
              {fetchError}
            </Alert>
          </Box>
        )}

        {/* ── Table matching Screenshots 1 & 2 ─────────────────────────────── */}
        <CandidateTable
          candidates={sortedCandidates}
          loading={loading}
          selected={selected}
          onSelect={handleSelect}
          onSelectAll={handleSelectAll}
          onCandidateClick={handleOpenDetail}
          onSendMessageClick={handleOpenSingleSend}
          sortField={sortField}
          sortOrder={sortOrder}
          onSort={handleSort}
          searchQuery={search}
          onClearSearch={() => {
            setSearchInput('');
            setSearch('');
          }}
          onAddCandidateClick={() => setAddModalOpen(true)}
        />

        {/* ── Pagination & Toast on the Exact Same Line matching Screenshot 2 ───────── */}
        <Box
          id="pagination-toast-row"
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderTop: '1px solid #f0f0f0',
            pl: 2,
            pr: 3.5,
            minHeight: 52,
            backgroundColor: '#ffffff',
          }}
        >
          {/* Pagination at bottom leftmost */}
          <TablePagination
            component="div"
            count={totalCount}
            page={page}
            onPageChange={handleChangePage}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={handleChangeRowsPerPage}
            rowsPerPageOptions={[5, 10, 25, 50]}
            showFirstButton
            showLastButton
            labelRowsPerPage="Rows per page:"
            sx={{
              borderTop: 'none',
              color: '#424242',
              fontSize: '0.8125rem',
              '& .MuiToolbar-root': {
                justifyContent: 'flex-start',
                pl: 1.5,
                pr: 0,
                minHeight: 52,
              },
              '& .MuiTablePagination-spacer': {
                display: 'none',
              },
              '& .MuiTablePagination-selectLabel, & .MuiTablePagination-displayedRows': {
                fontSize: '0.8125rem',
                color: '#212121',
              },
              '& .MuiTablePagination-actions': {
                color: '#757575',
                ml: 1,
              },
            }}
          />

          {/* Toast Message at bottom rightmost on the same line matching Screenshot 2 */}
          {toastOpen && toast && (
            <Box
              id="dashboard-inline-toast"
              onClick={closeToast}
              sx={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 1.25,
                px: 2,
                py: 0.85,
                borderRadius: '4px',
                cursor: 'pointer',
                backgroundColor: toast.severity === 'error' ? '#ffebee' : '#e8f5e9',
                border: toast.severity === 'error' ? '1px solid #ffcdd2' : '1px solid #c8e6c9',
                color: toast.severity === 'error' ? '#b71c1c' : '#1e293b',
                boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                transition: 'all 0.2s ease',
              }}
            >
              {toast.severity === 'error' ? (
                <ErrorOutlineIcon sx={{ color: '#d32f2f', fontSize: 18 }} />
              ) : (
                <CheckCircleOutlineIcon sx={{ color: '#2e7d32', fontSize: 18 }} />
              )}
              <Typography
                sx={{
                  fontSize: '0.8125rem',
                  fontWeight: 500,
                  color: toast.severity === 'error' ? '#b71c1c' : '#1e293b',
                  lineHeight: 1.4,
                }}
              >
                {toast.message}
              </Typography>
            </Box>
          )}
        </Box>
      </Paper>

      {/* ── Modals ────────────────────────────────────────────────────────── */}
      <AddCandidateModal
        open={addModalOpen}
        onClose={() => setAddModalOpen(false)}
        onSuccess={fetchCandidates}
      />

      <SendMessageModal
        open={sendModalOpen}
        onClose={() => {
          setSendModalOpen(false);
          setActiveCandidate(null);
        }}
        onSuccess={() => {
          fetchCandidates();
          refreshHealth();
          setSelected([]);
        }}
        candidate={activeCandidate}
        recipients={selectedCandidatesList.length > 0 ? selectedCandidatesList : activeCandidate ? [activeCandidate] : []}
      />

      <BulkMessageModal
        open={bulkModalOpen}
        onClose={() => setBulkModalOpen(false)}
        onSuccess={fetchCandidates}
        selectedCandidates={selectedCandidatesList}
      />

      <CandidateDetailModal
        open={detailModalOpen}
        onClose={() => {
          setDetailModalOpen(false);
          setActiveCandidate(null);
        }}
        candidate={activeCandidate}
        onSendMessage={(c) => {
          setActiveCandidate(c);
          setSendModalOpen(true);
        }}
      />

      <TemplatesDrawer open={templatesOpen} onClose={() => setTemplatesOpen(false)} />

      <DeleteConfirmDialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        onConfirm={handleDeleteConfirm}
        candidateNames={selectedCandidatesList.map(c => c.full_name)}
        loading={deleteLoading}
      />
    </Box>
  );
}
