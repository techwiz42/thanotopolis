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
  transcript?: string;
  summary?: string;
  call_metadata?: Record<string, any>;
  created_at: string;
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
      const response = await api.post('/telephony/setup', data, {
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
      const response = await api.patch('/telephony/config', data, {
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
      const response = await api.get(`/telephony/calls/${callId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      return response.data as PhoneCall;
    } catch (error) {
      console.error('Error fetching call:', error);
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
  }
};
