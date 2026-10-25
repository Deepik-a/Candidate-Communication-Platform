'use client';

import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Checkbox,
  Typography,
  Box,
  TableSortLabel,
  Skeleton,
} from '@mui/material';
import { Candidate } from '@/types';
import { StatusBadge } from './StatusBadge';

type SortField = 'full_name' | 'mobile_number' | 'last_message_date' | 'status' | 'candidate_id';
type SortOrder = 'asc' | 'desc';

interface CandidateTableProps {
  candidates: Candidate[];
  loading: boolean;
  selected: number[];
  onSelect: (id: number) => void;
  onSelectAll: (checked: boolean) => void;
  onCandidateClick: (candidate: Candidate) => void;
  sortField: SortField;
  sortOrder: SortOrder;
  onSort: (field: SortField) => void;
}

const columns: { id: SortField; label: string; width?: string }[] = [
  { id: 'full_name', label: 'Full name', width: '25%' },
  { id: 'mobile_number', label: 'Mobile number', width: '20%' },
  { id: 'last_message_date', label: 'Last message', width: '18%' },
  { id: 'status', label: 'Status', width: '17%' },
  { id: 'candidate_id', label: 'Candidate ID', width: '20%' },
];

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'NA';
  // Format as DD-MM-YYYY to match screenshot
  const [year, month, day] = dateStr.split('-');
  return `${day}-${month}-${year}`;
}

export function CandidateTable({
  candidates,
  loading,
  selected,
  onSelect,
  onSelectAll,
  onCandidateClick,
  sortField,
  sortOrder,
  onSort,
}: CandidateTableProps) {
  const allSelected = candidates.length > 0 && selected.length === candidates.length;
  const someSelected = selected.length > 0 && !allSelected;

  const headerSx = {
    fontWeight: 600,
    fontSize: '0.8rem',
    color: '#424242',
    backgroundColor: '#fafafa',
    borderBottom: '1px solid #e0e0e0',
    py: 1.5,
    px: 2,
    userSelect: 'none' as const,
  };

  const cellSx = {
    fontSize: '0.875rem',
    color: '#212121',
    borderBottom: '1px solid #f0f0f0',
    py: 1.25,
    px: 2,
  };

  return (
    <TableContainer>
      <Table size="medium" aria-label="candidate table">
        <TableHead>
          <TableRow>
            <TableCell padding="checkbox" sx={{ ...headerSx, pl: 2 }}>
              <Checkbox
                id="select-all-checkbox"
                size="small"
                indeterminate={someSelected}
                checked={allSelected}
                onChange={(e) => onSelectAll(e.target.checked)}
                sx={{ color: '#bdbdbd' }}
              />
            </TableCell>
            {columns.map((col) => (
              <TableCell key={col.id} sx={{ ...headerSx, width: col.width }}>
                <TableSortLabel
                  active={sortField === col.id}
                  direction={sortField === col.id ? sortOrder : 'asc'}
                  onClick={() => onSort(col.id)}
                  sx={{
                    '& .MuiTableSortLabel-icon': { fontSize: '1rem', opacity: 0.4 },
                    '&.Mui-active': { color: '#424242' },
                    '&.Mui-active .MuiTableSortLabel-icon': { opacity: 1, color: '#757575' },
                  }}
                >
                  {col.label}
                </TableSortLabel>
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {loading
            ? Array.from({ length: 7 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell padding="checkbox" sx={{ pl: 2 }}>
                    <Skeleton variant="rectangular" width={16} height={16} sx={{ borderRadius: 0.5 }} />
                  </TableCell>
                  {columns.map((col) => (
                    <TableCell key={col.id} sx={{ py: 1.5, px: 2 }}>
                      <Skeleton variant="text" width={col.id === 'full_name' ? 140 : 100} />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            : candidates.length === 0
            ? (
              <TableRow>
                <TableCell colSpan={6} sx={{ textAlign: 'center', py: 6 }}>
                  <Typography color="text.secondary" variant="body2">
                    No candidates found. Add one using the button above.
                  </Typography>
                </TableCell>
              </TableRow>
            )
            : candidates.map((candidate) => {
                const isSelected = selected.includes(candidate.id);
                return (
                  <TableRow
                    key={candidate.id}
                    hover
                    selected={isSelected}
                    sx={{
                      '&:hover': { backgroundColor: '#f5f9ff' },
                      '&.Mui-selected': { backgroundColor: '#eff6ff' },
                      '&.Mui-selected:hover': { backgroundColor: '#e8f1ff' },
                      cursor: 'default',
                      transition: 'background-color 0.15s ease',
                    }}
                  >
                    <TableCell padding="checkbox" sx={{ pl: 2 }}>
                      <Checkbox
                        id={`select-candidate-${candidate.id}`}
                        size="small"
                        checked={isSelected}
                        onChange={() => onSelect(candidate.id)}
                        sx={{ color: '#bdbdbd' }}
                      />
                    </TableCell>
                    <TableCell sx={cellSx}>
                      <Typography
                        component="span"
                        sx={{
                          color: '#1565c0',
                          fontWeight: 500,
                          fontSize: '0.875rem',
                          cursor: 'pointer',
                          '&:hover': { textDecoration: 'underline' },
                        }}
                        onClick={() => onCandidateClick(candidate)}
                        id={`candidate-name-${candidate.id}`}
                      >
                        {candidate.full_name}
                      </Typography>
                    </TableCell>
                    <TableCell sx={cellSx}>{candidate.mobile_number}</TableCell>
                    <TableCell sx={{ ...cellSx, color: candidate.last_message_date ? '#212121' : '#9e9e9e' }}>
                      {formatDate(candidate.last_message_date)}
                    </TableCell>
                    <TableCell sx={cellSx}>
                      <StatusBadge status={candidate.status} />
                    </TableCell>
                    <TableCell sx={cellSx}>{candidate.candidate_id}</TableCell>
                  </TableRow>
                );
              })}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
