// Status: real

import { apiGet, apiPost } from '@/lib/api';

export type MessageScope = 'course' | 'class' | 'individual';
export type DeliveryState = 'unread' | 'read' | 'recalled';

export type MessageRecord = {
  id: string;
  sender_user_id: string;
  scope_type: MessageScope;
  course_id: string;
  teaching_class_id?: string | null;
  target_user_id?: string | null;
  subject: string;
  body: string;
  safety_state: 'accepted' | 'rejected';
  status: 'draft' | 'sent' | 'partially_delivered' | 'recalled' | 'expired';
  sent_at?: string | null;
  recall_deadline_at?: string | null;
  recalled_at?: string | null;
  delivery_counts: Record<string, number>;
  created_at: string;
  updated_at: string;
};

export type InboxMessage = MessageRecord & {
  delivery_state: DeliveryState;
  delivered_at: string;
  read_at?: string | null;
};

export type SendMessagePayload = {
  scope_type: MessageScope;
  course_id: string;
  teaching_class_id?: string;
  target_user_id?: string;
  subject: string;
  body: string;
  idempotency_key: string;
};

export function fetchInbox(): Promise<{ items: InboxMessage[] }> {
  return apiGet<{ items: InboxMessage[] }>('/api/v1/messages/inbox');
}

export function fetchOutbox(): Promise<MessageRecord[]> {
  return apiGet<MessageRecord[]>('/api/v1/messages/outbox');
}

export function sendMessage(payload: SendMessagePayload): Promise<MessageRecord> {
  return apiPost<MessageRecord, SendMessagePayload>('/api/v1/messages', payload);
}

export function markMessageRead(messageId: string): Promise<{ message_id: string; delivery_state: DeliveryState }> {
  return apiPost<{ message_id: string; delivery_state: DeliveryState }>(
    `/api/v1/messages/${encodeURIComponent(messageId)}/read`,
    {},
  );
}

export function recallMessage(messageId: string, reason: string): Promise<MessageRecord> {
  return apiPost<MessageRecord>(`/api/v1/messages/${encodeURIComponent(messageId)}/recall`, { reason });
}
