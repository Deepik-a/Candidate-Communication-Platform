import axios from 'axios';
import {
  BulkDeletePayload,
  BulkSendMessagePayload,
  BulkSendMessageResponse,
  Candidate,
  CandidateMessageOutcome,
  CommunicationHealth,
  CreateCandidatePayload,
  Message,
  MessageTemplate,
  PaginatedCandidates,
  ProviderCatalogItem,
  SendMessagePayload,
  UpdateCandidatePayload,
} from '@/types';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
  headers: { 'Content-Type': 'application/json' },
});

export const candidatesApi = {
  list: async (params?: { search?: string; page?: number; page_size?: number }): Promise<PaginatedCandidates> => {
    const { data } = await api.get('/candidates/', { params });
    return data;
  },
  create: async (payload: CreateCandidatePayload): Promise<Candidate> => {
    const { data } = await api.post('/candidates/', payload);
    return data;
  },
  update: async (id: number, payload: UpdateCandidatePayload): Promise<Candidate> => {
    const { data } = await api.patch(`/candidates/${id}/`, payload);
    return data;
  },
  remove: async (id: number): Promise<void> => {
    await api.delete(`/candidates/${id}/`);
  },
  bulkDelete: async (ids: number[]): Promise<{ deleted: number }> => {
    const payload: BulkDeletePayload = { ids };
    const { data } = await api.post('/candidates/bulk-delete/', payload);
    return data;
  },
};

export const communicationsApi = {
  send: async (payload: SendMessagePayload): Promise<CandidateMessageOutcome> => {
    const { data } = await api.post('/communications/send/', payload);
    return data;
  },
  bulkSend: async (payload: BulkSendMessagePayload): Promise<BulkSendMessageResponse> => {
    const { data } = await api.post('/communications/bulk-send/', payload);
    return data;
  },
  getHistory: async (candidateId: number): Promise<Message[]> => {
    const { data } = await api.get(`/communications/candidate/${candidateId}/`);
    return data;
  },
  retry: async (messageId: number): Promise<CandidateMessageOutcome> => {
    const { data } = await api.post(`/communications/messages/${messageId}/retry/`);
    return data;
  },
  health: async (): Promise<CommunicationHealth> => {
    const { data } = await api.get('/communications/health/');
    return data;
  },
  providers: async (): Promise<ProviderCatalogItem[]> => {
    const { data } = await api.get('/communications/providers/');
    return data.results;
  },
  dispatchScheduled: async (): Promise<{ dispatched: number }> => {
    const { data } = await api.post('/communications/dispatch-scheduled/');
    return data;
  },
  listTemplates: async (): Promise<MessageTemplate[]> => {
    const { data } = await api.get('/communications/templates/');
    return data;
  },
  createTemplate: async (payload: { name: string; content: string; channel?: string }): Promise<MessageTemplate> => {
    const { data } = await api.post('/communications/templates/', payload);
    return data;
  },
  updateTemplate: async (
    id: number,
    payload: { name?: string; content?: string; channel?: string },
  ): Promise<MessageTemplate> => {
    const { data } = await api.patch(`/communications/templates/${id}/`, payload);
    return data;
  },
  deleteTemplate: async (id: number): Promise<void> => {
    await api.delete(`/communications/templates/${id}/`);
  },
  previewTemplate: async (payload: {
    candidate_id: number;
    content?: string;
    template_id?: number;
  }): Promise<{ preview: string }> => {
    const { data } = await api.post('/communications/templates/preview/', payload);
    return data;
  },
};
