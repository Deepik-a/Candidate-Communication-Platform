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
  Divider,
  Tooltip,
  Badge,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteForeverIcon from '@mui/icons-material/DeleteForever';
import SendIcon from '@mui/icons-material/Send';
import GroupIcon from '@mui/icons-material/Group';
import SearchIcon from '@mui/icons-material/Search';

import { candidatesApi } from '@/lib/api';
import { Candidate } from '@/types';
import { useToast } from '@/context/ToastContext';
import { CandidateTable } from '@/components/CandidateTable';
import { AddCandidateModal } from '@/components/AddCandidateModal';
import { SendMessageModal } from '@/components/SendMessageModal';
import { BulkMessageModal } from '@/components/BulkMessageModal';
import { CandidateDetailModal } from '@/components/CandidateDetailModal';
import { DeleteConfirmDialog } from '@/components/DeleteConfirmDialog';

type SortField = 'full_name' | 'mobile_number' | 'last_message_date' | 'status' | 'candidate_id';
type SortOrder = 'asc' | 'desc';

export default function CandidateDashboard() {
  const { showToast } = useToast();

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

  // Sort
  const [sortField, setSortField] = useState<SortField>('full_name');
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
    } catch {
      showToast('Failed to load candidates. Is the backend running?', 'error');
    } finally {
      setLoading(false);
    }
  }, [search, page, rowsPerPage, showToast]);

  useEffect(() => {
    fetchCandidates();
  }, [fetchCandidates]);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setPage(0);
    }, 350);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // Sort candidates client-side
  const sortedCandidates = [...candidates].sort((a, b) => {
    const aVal = a[sortField] ?? '';
    const bVal = b[sortField] ?? '';
    const cmp = String(aVal).localeCompare(String(bVal));
    return sortOrder === 'asc' ? cmp : -cmp;
  });

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
      showToast(`${deleted} candidate${deleted > 1 ? 's' : ''} deleted.`, 'success');
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
      // Bulk messaging flow
      setBulkModalOpen(true);
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
      setSortOrder(prev => (prev === 'asc' ? 'desc' : 'asc'));
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
    <Box sx={{ minHeight: '100vh', backgroundColor: '#f8f9fa' }}>
      <Paper
        elevation={0}
        sx={{
          mx: 'auto',
          my: 3,
          maxWidth: 1280,
          borderRadius: 2,
          border: '1px solid #e0e0e0',
          backgroundColor: '#ffffff',
          overflow: 'hidden',
        }}
      >
        {/* ── Toolbar ─────────────────────────────────────────────────────── */}
        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
          sx={{ px: 3, py: 2 }}
        >
          {/* Title */}
          <Typography
            variant="h6"
            fontWeight={700}
            sx={{ color: '#1a1a2e', letterSpacing: '-0.02em', fontSize: '1.15rem' }}
          >
            Candidate communication
          </Typography>

          {/* Actions */}
          <Stack direction="row" alignItems="center" spacing={1.5}>
            <Tooltip title="Add a new candidate">
              <Button
                id="add-candidate-btn"
                variant="outlined"
                size="small"
                startIcon={<AddIcon />}
                onClick={() => setAddModalOpen(true)}
                sx={{
                  borderColor: '#1976d2',
                  color: '#1976d2',
                  fontWeight: 500,
                  fontSize: '0.8rem',
                  textTransform: 'uppercase',
                  px: 1.5,
                  py: 0.6,
                  '&:hover': { backgroundColor: '#e3f2fd', borderColor: '#1565c0' },
                }}
              >
                Add Candidate
              </Button>
            </Tooltip>

            <Tooltip title={selected.length === 0 ? 'Select candidates first' : 'Delete selected'}>
              <span>
                <Button
                  id="delete-candidate-btn"
                  variant="outlined"
                  size="small"
                  startIcon={<DeleteForeverIcon />}
                  onClick={handleDeleteClick}
                  disabled={selected.length === 0}
                  sx={{
                    borderColor: '#9e9e9e',
                    color: '#616161',
                    fontWeight: 500,
                    fontSize: '0.8rem',
                    textTransform: 'uppercase',
                    px: 1.5,
                    py: 0.6,
                    '&:hover': { backgroundColor: '#fce4ec', borderColor: '#e53935', color: '#e53935' },
                    '&.Mui-disabled': { opacity: 0.5 },
                  }}
                >
                  Delete Candidate
                </Button>
              </span>
            </Tooltip>

            <Tooltip
              title={
                selected.length === 0
                  ? 'Select one or more candidates'
                  : selected.length === 1
                  ? 'Send message to 1 candidate'
                  : `Bulk send to ${selected.length} candidates`
              }
            >
              <span>
                <Button
                  id="send-message-btn"
                  variant={selected.length > 1 ? 'contained' : 'outlined'}
                  size="small"
                  startIcon={selected.length > 1 ? <GroupIcon sx={{ fontSize: '1rem' }} /> : <SendIcon sx={{ fontSize: '0.9rem' }} />}
                  onClick={handleSendClick}
                  disabled={selected.length === 0}
                  sx={{
                    fontWeight: 600,
                    fontSize: '0.8rem',
                    textTransform: 'uppercase',
                    px: 1.5,
                    py: 0.6,
                    ...(selected.length > 1
                      ? {
                          backgroundColor: '#1976d2',
                          color: '#fff',
                          '&:hover': { backgroundColor: '#1565c0' },
                        }
                      : {
                          borderColor: '#9e9e9e',
                          color: '#616161',
                          '&:hover': { backgroundColor: '#e8f5e9', borderColor: '#43a047', color: '#43a047' },
                        }),
                    '&.Mui-disabled': { opacity: 0.5 },
                  }}
                >
                  {selected.length > 1 ? `Send to ${selected.length} Candidates` : 'Send Message'}
                </Button>
              </span>
            </Tooltip>

            {/* Search */}
            <TextField
              id="candidate-search"
              size="small"
              placeholder="Search by name, phone, email, ID"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon sx={{ fontSize: '1.1rem', color: '#9e9e9e' }} />
                  </InputAdornment>
                ),
              }}
              sx={{
                width: 240,
                '& .MuiOutlinedInput-root': {
                  borderRadius: '6px',
                  backgroundColor: '#fafafa',
                  fontSize: '0.875rem',
                  '&:hover fieldset': { borderColor: '#bdbdbd' },
                },
              }}
            />
          </Stack>
        </Stack>

        <Divider />

        {/* ── Table ──────────────────────────────────────────────────────── */}
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
        />

        <Divider />

        {/* ── Pagination ─────────────────────────────────────────────────── */}
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
          sx={{
            borderTop: 'none',
            '& .MuiTablePagination-toolbar': { px: 2, minHeight: 52 },
            '& .MuiTablePagination-displayedRows': { fontSize: '0.8rem', color: '#616161' },
            '& .MuiTablePagination-selectLabel': { fontSize: '0.8rem', color: '#616161' },
          }}
        />
      </Paper>

      {/* ── Modals ─────────────────────────────────────────────────────────── */}
      <AddCandidateModal
        open={addModalOpen}
        onClose={() => setAddModalOpen(false)}
        onSuccess={() => {
          fetchCandidates();
          setAddModalOpen(false);
        }}
      />

      <SendMessageModal
        open={sendModalOpen}
        onClose={() => setSendModalOpen(false)}
        onSuccess={() => {
          fetchCandidates();
          setSendModalOpen(false);
          setSelected([]);
        }}
        candidate={activeCandidate}
      />

      <BulkMessageModal
        open={bulkModalOpen}
        onClose={() => setBulkModalOpen(false)}
        onSuccess={() => {
          fetchCandidates();
          setSelected([]);
        }}
        selectedCandidates={selectedCandidatesList}
      />

      <CandidateDetailModal
        open={detailModalOpen}
        onClose={() => setDetailModalOpen(false)}
        candidate={activeCandidate}
        onSendMessage={handleOpenSingleSend}
      />

      <DeleteConfirmDialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        onConfirm={handleDeleteConfirm}
        loading={deleteLoading}
        count={selected.length}
      />
    </Box>
  );
}
