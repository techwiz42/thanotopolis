// frontend/src/services/telephony.ts
import { api } from './api';

export interface TelephonyConfig {
  id: string;
  tenant_id: string;
  organization_phone_number: string;
  formatted_phone_number?: string;
  platform_phone_number?: string;
  country_code: string;
  verification_status: 'pending' | 'verified' | 'failed' | 'expired';
  call_forwarding_enabled: boolean;
  welcome_message?: string;
  is_enabled: boolean;
  business_hours?: BusinessHours;
  timezone: string;
  max_concurrent_calls: number;
  call_timeout_seconds: number;
  record_calls: boolean;
  transcript_calls: boolean;
  forwarding_instructions?: string;
  integration_method: string;
  created_at: string;
  updated_at?: string;
}

export interface BusinessHours {
  [day: string]: {
    start: string;
    end: string;
  } | { start: 'closed'; end: 'closed' };
}

export interface PhoneCall {
  id: string;
  call_sid: string;
  customer_phone_number: string;
  organization_phone_number: string;
  platform_phone_number: string;
  direction: 'inbound' | 'outbound';
  status: 'incoming' | 'ringing' | 'answered' | 'in_progress' | 'completed' | 'failed' | 'no_answer' | 'busy';
  start_time?: string;
  answer_time?: string;
  end_time?: string;
  duration_seconds?: number;
  cost_cents: number;
  cost_currency: string;
  recording_url?: string;
  call_metadata?: Record<string, any>;
  created_at: string;
  messages?: CallMessage[];
  summary?: string;
}

export interface CallMessage {
  id: string;
  call_id: string;
  content: string;
  sender: CallMessageSender;
  timestamp: string;
  message_type: 'transcript' | 'system' | 'summary' | 'note';
  metadata?: CallMessageMetadata;
  created_at: string;
}

export interface CallMessageSender {
  identifier: string;
  name?: string;
  type: 'customer' | 'agent' | 'system' | 'operator';
  phone_number?: string;
}

export interface CallMessageMetadata {
  audio_start_time?: number;
  audio_end_time?: number;
  confidence_score?: number;
  language?: string;
  recording_segment_url?: string;
  is_automated?: boolean;
  system_event_type?: string;
  [key: string]: unknown;
}

export interface CallsListResponse {
  calls: PhoneCall[];
  total: number;
  page: number;
  per_page: number;
}

export interface TelephonySetupRequest {
  organization_phone_number: string;
  welcome_message?: string;
  business_hours?: BusinessHours;
  voice_id?: string;
  max_concurrent_calls?: number;
  record_calls?: boolean;
  transcript_calls?: boolean;
}

export interface TelephonyUpdateRequest {
  welcome_message?: string;
  business_hours?: BusinessHours;
  is_enabled?: boolean;
  max_concurrent_calls?: number;
  voice_id?: string;
  record_calls?: boolean;
  transcript_calls?: boolean;
}

export interface PhoneVerificationResponse {
  success: boolean;
  message: string;
  verification_id?: string;
}

export const telephonyService = {
  // Setup telephony configuration
  async setupTelephony(data: TelephonySetupRequest, token: string): Promise<TelephonyConfig> {
    try {
      // Always enforce transcript_calls and record_calls to be true
      const setupData = {
        ...data,
        record_calls: true,
        transcript_calls: true
      };
      
      const response = await api.post('/telephony/setup', setupData, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      return response.data as TelephonyConfig;
    } catch (error) {
      console.error('Error setting up telephony:', error);
      throw error;
    }
  },

  // Get telephony configuration
  async getTelephonyConfig(token: string): Promise<TelephonyConfig> {
    try {
      const response = await api.get('/telephony/config', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      return response.data as TelephonyConfig;
    } catch (error) {
      console.error('Error fetching telephony config:', error);
      throw error;
    }
  },

  // Update telephony configuration
  async updateTelephonyConfig(data: TelephonyUpdateRequest, token: string): Promise<TelephonyConfig> {
    try {
      // Always enforce transcript_calls and record_calls to be true
      const updateData = {
        ...data,
        record_calls: true,
        transcript_calls: true
      };
      
      const response = await api.patch('/telephony/config', updateData, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      return response.data as TelephonyConfig;
    } catch (error) {
      console.error('Error updating telephony config:', error);
      throw error;
    }
  },

  // Initiate phone verification
  async initiateVerification(token: string): Promise<PhoneVerificationResponse> {
    try {
      const response = await api.post('/telephony/verify/initiate', {}, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      return response.data as PhoneVerificationResponse;
    } catch (error) {
      console.error('Error initiating verification:', error);
      throw error;
    }
  },

  // Confirm phone verification
  async confirmVerification(verificationCode: string, token: string): Promise<PhoneVerificationResponse> {
    try {
      const response = await api.post('/telephony/verify/confirm', 
        { verification_code: verificationCode },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );
      
      return response.data as PhoneVerificationResponse;
    } catch (error) {
      console.error('Error confirming verification:', error);
      throw error;
    }
  },

  // Get call history
  async getCalls(
    token: string,
    page: number = 1,
    perPage: number = 20,
    status?: string
  ): Promise<CallsListResponse> {
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: perPage.toString()
      });
      
      if (status) {
        params.append('status', status);
      }

      const response = await api.get(`/telephony/calls?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      return response.data as CallsListResponse;
    } catch (error) {
      console.error('Error fetching calls:', error);
      throw error;
    }
  },

  // Get call forwarding instructions
  async getForwardingInstructions(token: string): Promise<{ instructions: string }> {
    try {
      const response = await api.get('/telephony/forwarding-instructions', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      return response.data as { instructions: string };
    } catch (error) {
      console.error('Error fetching forwarding instructions:', error);
      throw error;
    }
  },

  // Get specific call
  async getCall(callId: string, token: string): Promise<PhoneCall> {
    try {
      console.log('Fetching call with ID:', callId);
      console.log('Using token:', token ? 'Present' : 'Missing');
      
      const response = await api.get(`/telephony/calls/${callId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      console.log('Call fetch response:', response);
      return response.data as PhoneCall;
    } catch (error) {
      console.error('Error fetching call:', error);
      throw error;
    }
  },

  // Get call messages
  async getCallMessages(callId: string, token: string): Promise<CallMessage[]> {
    try {
      const response = await api.get(`/telephony/calls/${callId}/messages`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      // Backend returns {messages: [], total: number, call_id: string}
      // Frontend expects just the messages array
      if (response.data && typeof response.data === 'object' && 'messages' in response.data) {
        const data = response.data as { messages: unknown };
        console.log(`📞 Loaded ${Array.isArray(data.messages) ? data.messages.length : 0} call messages`);
        return data.messages as CallMessage[];
      }
      
      // Fallback for direct array response (legacy)
      return response.data as CallMessage[];
    } catch (error) {
      console.error('Error fetching call messages:', error);
      throw error;
    }
  },

  // Add message to call
  async addCallMessage(
    callId: string, 
    message: Omit<CallMessage, 'id' | 'call_id' | 'created_at'>, 
    token: string
  ): Promise<CallMessage> {
    try {
      const response = await api.post(`/telephony/calls/${callId}/messages`, message, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      return response.data as CallMessage;
    } catch (error) {
      console.error('Error adding call message:', error);
      throw error;
    }
  },

  // Update call message
  async updateCallMessage(
    callId: string,
    messageId: string,
    updates: Partial<Pick<CallMessage, 'content' | 'metadata'>>,
    token: string
  ): Promise<CallMessage> {
    try {
      const response = await api.patch(`/telephony/calls/${callId}/messages/${messageId}`, updates, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      return response.data as CallMessage;
    } catch (error) {
      console.error('Error updating call message:', error);
      throw error;
    }
  },

  // Delete call message
  async deleteCallMessage(callId: string, messageId: string, token: string): Promise<void> {
    try {
      await api.delete(`/telephony/calls/${callId}/messages/${messageId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
    } catch (error) {
      console.error('Error deleting call message:', error);
      throw error;
    }
  },

  // Utility functions
  formatPhoneNumber(phoneNumber: string): string {
    // Remove all non-digit characters
    const digits = phoneNumber.replace(/\D/g, '');
    
    // Format US numbers
    if (digits.length === 10) {
      return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
    } else if (digits.length === 11 && digits.startsWith('1')) {
      return `(${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7)}`;  
    }
    
    return phoneNumber;
  },

  validatePhoneNumber(phoneNumber: string): boolean {
    // Remove all non-digit characters
    const digits = phoneNumber.replace(/\D/g, '');
    
    // Check if it's a valid US phone number (10 digits or 11 with country code)
    return digits.length === 10 || (digits.length === 11 && digits.startsWith('1'));
  },

  formatCallDuration(durationSeconds: number): string {
    const minutes = Math.floor(durationSeconds / 60);
    const seconds = durationSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  },

  formatCallCost(costCents: number, currency: string = 'USD'): string {
    const dollars = costCents / 100;
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency
    }).format(dollars);
  },

  getCallStatusColor(status: string): string {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'in_progress':
      case 'answered':
        return 'bg-blue-100 text-blue-800';
      case 'incoming':
      case 'ringing':
        return 'bg-yellow-100 text-yellow-800';
      case 'failed':
      case 'no_answer':
        return 'bg-red-100 text-red-800';
      case 'busy':
        return 'bg-orange-100 text-orange-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  },

  getVerificationStatusColor(status: string): string {
    switch (status) {
      case 'verified':
        return 'bg-green-100 text-green-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'failed':
      case 'expired':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  },

  getDefaultBusinessHours(): BusinessHours {
    return {
      monday: { start: '09:00', end: '17:00' },
      tuesday: { start: '09:00', end: '17:00' },
      wednesday: { start: '09:00', end: '17:00' },
      thursday: { start: '09:00', end: '17:00' },
      friday: { start: '09:00', end: '17:00' },
      saturday: { start: '10:00', end: '14:00' },
      sunday: { start: 'closed', end: 'closed' }
    };
  },

  // New utility methods for the updated model
  getDisplayPhoneNumber(config: TelephonyConfig): string {
    return config.formatted_phone_number || this.formatPhoneNumber(config.organization_phone_number);
  },

  getPlatformPhoneNumber(config: TelephonyConfig): string {
    return config.platform_phone_number ? 
      this.formatPhoneNumber(config.platform_phone_number) : 
      'Not assigned';
  },

  isSetupComplete(config: TelephonyConfig): boolean {
    return config.verification_status === 'verified' && config.call_forwarding_enabled;
  },

  getSetupStatus(config: TelephonyConfig): string {
    if (!config.platform_phone_number) return 'Platform number not assigned';
    if (config.verification_status !== 'verified') return 'Phone verification required';
    if (!config.call_forwarding_enabled) return 'Call forwarding setup required';
    return 'Setup complete';
  },

  // Call message utilities
  getMessageSenderName(sender: CallMessageSender): string {
    switch (sender.type) {
      case 'customer':
        return sender.phone_number ? this.formatPhoneNumber(sender.phone_number) : 'Customer';
      case 'agent':
        return sender.name || 'AI Agent';
      case 'system':
        return 'System';
      case 'operator':
        return 'Operator';
      default:
        return sender.name || sender.identifier;
    }
  },

  getMessageTypeColor(messageType: CallMessage['message_type']): string {
    switch (messageType) {
      case 'transcript':
        return 'bg-blue-100 text-blue-800';
      case 'system':
        return 'bg-gray-100 text-gray-800';
      case 'summary':
        return 'bg-green-100 text-green-800';
      case 'note':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  },

  getSenderTypeColor(senderType: CallMessageSender['type']): string {
    switch (senderType) {
      case 'customer':
        return 'bg-purple-100 text-purple-800';
      case 'agent':
        return 'bg-blue-100 text-blue-800';
      case 'system':
        return 'bg-gray-100 text-gray-800';
      case 'operator':
        return 'bg-orange-100 text-orange-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  },

  sortMessagesByTimestamp(messages: CallMessage[]): CallMessage[] {
    if (!Array.isArray(messages)) {
      return [];
    }
    return [...messages].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  },

  groupMessagesByType(messages: CallMessage[]): Record<CallMessage['message_type'], CallMessage[]> {
    if (!Array.isArray(messages)) {
      return {} as Record<CallMessage['message_type'], CallMessage[]>;
    }
    return messages.reduce((groups, message) => {
      const type = message.message_type;
      if (!groups[type]) {
        groups[type] = [];
      }
      groups[type].push(message);
      return groups;
    }, {} as Record<CallMessage['message_type'], CallMessage[]>);
  },

  groupConsecutiveMessagesBySender(messages: CallMessage[]): CallMessage[][] {
    if (!Array.isArray(messages) || messages.length === 0) {
      return [];
    }

    const sortedMessages = this.sortMessagesByTimestamp(messages);
    const grouped: CallMessage[][] = [];
    let currentGroup: CallMessage[] = [sortedMessages[0]];

    for (let i = 1; i < sortedMessages.length; i++) {
      const currentMessage = sortedMessages[i];
      const previousMessage = sortedMessages[i - 1];

      const isSameSender = 
        currentMessage.sender.type === previousMessage.sender.type &&
        currentMessage.sender.identifier === previousMessage.sender.identifier;

      const areBothTranscripts = 
        currentMessage.message_type === 'transcript' && 
        previousMessage.message_type === 'transcript';

      if (isSameSender && areBothTranscripts && (currentMessage.sender.type === 'customer' || currentMessage.sender.type === 'agent')) {
        currentGroup.push(currentMessage);
      } else {
        grouped.push(currentGroup);
        currentGroup = [currentMessage];
      }
    }

    grouped.push(currentGroup);
    return grouped;
  },

  getCallTranscript(messages: CallMessage[]): string {
    if (!Array.isArray(messages)) {
      return '';
    }
    return messages
      .filter(msg => msg.message_type === 'transcript')
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
      .map(msg => {
        const senderName = this.getMessageSenderName(msg.sender);
        return `${senderName}: ${msg.content}`;
      })
      .join('\n');
  },

  getCallSummary(messages: CallMessage[]): string | null {
    if (!Array.isArray(messages)) {
      return null;
    }
    const summaryMessage = messages.find(msg => msg.message_type === 'summary');
    return summaryMessage?.content || null;
  },

  hasAudioSegment(message: CallMessage): boolean {
    return !!(message.metadata?.recording_segment_url || message.metadata?.audio_start_time !== undefined);
  },

  // Generate summary for a call
  async generateCallSummary(callId: string, token: string): Promise<{
    success: boolean;
    call_id: string;
    summary: string;
    message_id: string;
    created_at: string;
  }> {
    try {
      const response = await api.post<{
        success: boolean;
        call_id: string;
        summary: string;
        message_id: string;
        created_at: string;
      }>(`/telephony/calls/${callId}/generate-summary`, {}, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      return response.data;
    } catch (error) {
      console.error('Error generating call summary:', error);
      throw error;
    }
  },

  // Create test call for telephony testing
  async createTestCall(customerNumber: string, token: string): Promise<{
    success: boolean;
    call_id: string;
    call_sid: string;
    customer_number: string;
    organization_number: string;
    platform_number: string;
    websocket_url: string;
    message: string;
  }> {
    try {
      const params = new URLSearchParams({ customer_number: customerNumber });
      const response = await api.post(`/telephony/test/simulate-call?${params}`, {}, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      return response.data as {
        success: boolean;
        call_id: string;
        call_sid: string;
        customer_number: string;
        organization_number: string;
        platform_number: string;
        websocket_url: string;
        message: string;
      };
    } catch (error) {
      console.error('Error creating test call:', error);
      throw error;
    }
  }
};
