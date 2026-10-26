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
  Skeleton,
} from '@mui/material';
import FilterListIcon from '@mui/icons-material/FilterList';
import { Candidate } from '@/types';
import { StatusBadge } from './StatusBadge';
import { EmptyCandidatesIllustration } from './EmptyCandidatesIllustration';

type SortField = 'full_name' | 'mobile_number' | 'last_message_date' | 'status' | 'candidate_id';
type SortOrder = 'asc' | 'desc';

interface CandidateTableProps {
  candidates: Candidate[];
  loading: boolean;
  selected: number[];
  onSelect: (id: number) => void;
  onSelectAll: (checked: boolean) => void;
  onCandidateClick: (candidate: Candidate) => void;
  onSendMessageClick?: (candidate: Candidate) => void;
  sortField: SortField | null;
  sortOrder: SortOrder;
  onSort: (field: SortField) => void;
  searchQuery?: string;
  onClearSearch?: () => void;
  onAddCandidateClick?: () => void;
}

const columns: { id: SortField; label: string; width?: string }[] = [
  { id: 'full_name', label: 'Full name', width: '22%' },
  { id: 'mobile_number', label: 'Mobile number', width: '20%' },
  { id: 'last_message_date', label: 'Last message', width: '20%' },
  { id: 'status', label: 'Status', width: '18%' },
  { id: 'candidate_id', label: 'Candidate ID', width: '16%' },
];

function formatDate(dateStr: string | null): string {
  if (!dateStr || dateStr.toLowerCase() === 'na') return 'NA';
  const parts = dateStr.split('-');
  if (parts.length === 3) {
    const [year, month, day] = parts;
    return `${day}-${month}-${year}`;
  }
  return dateStr;
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
  searchQuery = '',
  onClearSearch,
  onAddCandidateClick,
}: CandidateTableProps) {
  const allSelected = candidates.length > 0 && selected.length === candidates.length;
  const someSelected = selected.length > 0 && !allSelected;

  const headerSx = {
    fontWeight: 600,
    fontSize: '0.8125rem',
    color: '#212121',
    backgroundColor: '#ffffff',
    borderBottom: '1px solid #e0e0e0',
    py: 1.5,
    px: 2,
    userSelect: 'none' as const,
  };

  const cellSx = {
    fontSize: '0.8125rem',
    color: '#212121',
    borderBottom: '1px solid #f0f0f0',
    py: 1.5,
    px: 2,
  };

  return (
    <TableContainer sx={{ minHeight: candidates.length === 0 ? 440 : 'auto' }}>
      <Table size="medium" aria-label="candidate communication table">
        <TableHead>
          <TableRow sx={{ borderTop: '1px solid #e0e0e0' }}>
            <TableCell padding="checkbox" sx={{ ...headerSx, pl: 2, width: '4%' }}>
              <Checkbox
                id="select-all-checkbox"
                size="small"
                indeterminate={someSelected}
                checked={allSelected}
                onChange={(e) => onSelectAll(e.target.checked)}
                sx={{ color: '#bdbdbd', p: 0.5 }}
                disabled={loading || candidates.length === 0}
              />
            </TableCell>
            {columns.map((col) => (
              <TableCell
                key={col.id}
                sx={{ ...headerSx, width: col.width, cursor: 'pointer' }}
                onClick={() => onSort(col.id)}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span>{col.label}</span>
                  <FilterListIcon
                    sx={{
                      fontSize: '1.05rem',
                      color: sortField === col.id ? '#1976d2' : '#9e9e9e',
                      transform: sortField === col.id && sortOrder === 'desc' ? 'rotate(180deg)' : 'none',
                      transition: 'transform 0.2s, color 0.2s',
                    }}
                  />
                </Box>
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {loading ? (
            /* Loading Shimmer State */
            Array.from({ length: 6 }).map((_, i) => (
              <TableRow key={i}>
                <TableCell padding="checkbox" sx={{ pl: 2 }}>
                  <Skeleton variant="rectangular" width={16} height={16} sx={{ borderRadius: 0.5 }} />
                </TableCell>
                <TableCell sx={{ py: 1.75, px: 2 }}>
                  <Skeleton variant="text" width="70%" height={22} />
                </TableCell>
                <TableCell sx={{ py: 1.75, px: 2 }}>
                  <Skeleton variant="text" width="65%" height={20} />
                </TableCell>
                <TableCell sx={{ py: 1.75, px: 2 }}>
                  <Skeleton variant="text" width="55%" height={20} />
                </TableCell>
                <TableCell sx={{ py: 1.75, px: 2 }}>
                  <Skeleton variant="rounded" width={65} height={22} sx={{ borderRadius: '16px' }} />
                </TableCell>
                <TableCell sx={{ py: 1.75, px: 2 }}>
                  <Skeleton variant="text" width="60%" height={20} />
                </TableCell>
              </TableRow>
            ))
          ) : candidates.length === 0 ? (
            /* Exact Empty State matching Screenshot 1 */
            <TableRow>
              <TableCell colSpan={6} sx={{ textAlign: 'center', py: 10, borderBottom: 'none' }}>
                <Box
                  sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 1.25,
                  }}
                >
                  {/* Isometric Vector Illustration matching Screenshot 1 */}
                  <EmptyCandidatesIllustration width={190} height={140} />

                  {/* Title */}
                  <Typography
                    variant="h6"
                    sx={{
                      fontWeight: 700,
                      fontSize: '1.05rem',
                      color: '#262626',
                      letterSpacing: '-0.01em',
                      mt: 1,
                    }}
                  >
                    No candidates added
                  </Typography>

                  {/* Subtitle */}
                  <Typography
                    variant="body2"
                    sx={{
                      color: '#757575',
                      fontSize: '0.875rem',
                      fontWeight: 400,
                    }}
                  >
                    When you add a candidate, they will appear here.
                  </Typography>
                </Box>
              </TableCell>
            </TableRow>
          ) : (
            /* Exact Table Rows matching Screenshot 2 */
            candidates.map((candidate) => {
              const isSelected = selected.includes(candidate.id);
              return (
                <TableRow
                  key={candidate.id}
                  hover
                  selected={isSelected}
                  sx={{
                    '&:hover': { backgroundColor: '#fcfcfc' },
                    '&.Mui-selected': { backgroundColor: '#f5f9ff' },
                    '&.Mui-selected:hover': { backgroundColor: '#edf4fe' },
                    cursor: 'default',
                    transition: 'background-color 0.1s ease',
                  }}
                >
                  <TableCell padding="checkbox" sx={{ pl: 2 }}>
                    <Checkbox
                      id={`select-candidate-${candidate.id}`}
                      size="small"
                      checked={isSelected}
                      onChange={() => onSelect(candidate.id)}
                      sx={{ color: '#bdbdbd', p: 0.5 }}
                    />
                  </TableCell>

                  {/* Full Name: Blue clickable link */}
                  <TableCell sx={cellSx}>
                    <Typography
                      component="span"
                      sx={{
                        color: '#1976d2',
                        fontWeight: 400,
                        fontSize: '0.8125rem',
                        cursor: 'pointer',
                        '&:hover': { textDecoration: 'underline' },
                      }}
                      onClick={() => onCandidateClick(candidate)}
                      id={`candidate-name-${candidate.id}`}
                    >
                      {candidate.full_name}
                    </Typography>
                  </TableCell>

                  {/* Mobile Number */}
                  <TableCell sx={cellSx}>
                    <Typography component="span" sx={{ fontSize: '0.8125rem', color: '#212121' }}>
                      {candidate.mobile_number}
                    </Typography>
                  </TableCell>

                  {/* Last Message Date */}
                  <TableCell sx={cellSx}>
                    <Typography
                      component="span"
                      sx={{
                        fontSize: '0.8125rem',
                        color: candidate.last_message_date ? '#212121' : '#757575',
                      }}
                    >
                      {formatDate(candidate.last_message_date)}
                    </Typography>
                  </TableCell>

                  {/* Status Pill */}
                  <TableCell sx={cellSx}>
                    <StatusBadge status={candidate.status} />
                  </TableCell>

                  {/* Candidate ID */}
                  <TableCell sx={cellSx}>
                    <Typography component="span" sx={{ fontSize: '0.8125rem', color: '#212121' }}>
                      {candidate.candidate_id}
                    </Typography>
                  </TableCell>
                </TableRow>
              );
            })
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
