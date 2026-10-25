// API types matching backend models

export type MessageStatus = 'read' | 'sent' | 'failed' | 'NA';
export type MessageChannel = 'sms' | 'whatsapp' | 'email';

export interface Candidate {
  id: number;
  candidate_id: string;
  full_name: string;
  mobile_number: string;
  email: string | null;
  last_message_date: string | null; // ISO date string "YYYY-MM-DD"
  status: MessageStatus;
  created_at: string;
  updated_at: string;
}

export interface PaginatedCandidates {
  count: number;
  page: number;
  page_size: number;
  total_pages: number;
  results: Candidate[];
}

export interface CreateCandidatePayload {
  full_name: string;
  mobile_number: string;
  email?: string;
}

export interface UpdateCandidatePayload {
  full_name?: string;
  mobile_number?: string;
  email?: string;
}

export interface BulkDeletePayload {
  ids: number[];
}

export interface SendMessagePayload {
  candidate_id: number;
  channel: MessageChannel;
  content: string;
}

export interface Message {
  id: number;
  candidate: number;
  candidate_name: string;
  candidate_code: string;
  channel: MessageChannel;
  content: string;
  status: string;
  sent_at: string;
  updated_at: string;
}
