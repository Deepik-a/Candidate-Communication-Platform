// API types matching backend models

export type MessageStatus = 'read' | 'delivered' | 'sent' | 'failed' | 'scheduled' | 'pending' | 'NA';
export type MessageChannel = 'sms' | 'whatsapp' | 'email';
export type ProviderHealthStatus = 'operational' | 'degraded' | 'unavailable';

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
  provider?: string;
  scheduled_at?: string | null;
  template_id?: number | null;
}

export interface BulkSendMessagePayload {
  candidate_ids: number[];
  channel: MessageChannel;
  content: string;
  provider?: string;
  scheduled_at?: string | null;
  template_id?: number | null;
}

export interface CandidateMessageOutcome {
  candidate_id: number;
  candidate_name: string;
  candidate_code: string;
  success: boolean;
  status: string;
  message_id: number | null;
  provider: string;
  provider_message_id: string;
  failure_category?: string | null;
  error_message: string | null;
  is_retryable?: boolean;
}

export interface BulkSendMessageResponse {
  total_requested: number;
  successful_count: number;
  failed_count: number;
  outcomes: CandidateMessageOutcome[];
}

export interface Message {
  id: number;
  candidate: number;
  candidate_name: string;
  candidate_code: string;
  candidate_phone?: string;
  candidate_email?: string;
  channel: MessageChannel;
  content: string;
  status: string;
  provider?: string;
  provider_message_id?: string;
  failure_category?: string;
  error_message?: string;
  scheduled_at?: string | null;
  template?: number | null;
  template_name?: string | null;
  retry_count?: number;
  is_retryable?: boolean;
  sent_at: string;
  updated_at: string;
}

export interface MessageTemplate {
  id: number;
  name: string;
  content: string;
  channel: string;
  placeholders?: { token: string; description: string }[];
  created_at: string;
  updated_at: string;
}

export interface ProviderCatalogItem {
  id: string;
  name: string;
  description: string;
  channels: string[];
  health: {
    id: string;
    name: string;
    status: ProviderHealthStatus | string;
    detail: string;
  };
}

export interface CommunicationHealth {
  status: ProviderHealthStatus | string;
  label: string;
  recruiter_notice: string;
  messages_sent: number;
  messages_delivered: number;
  messages_failed: number;
  messages_scheduled: number;
  messages_read: number;
  providers: ProviderCatalogItem[];
}
