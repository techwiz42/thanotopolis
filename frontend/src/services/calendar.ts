// src/services/calendar.ts
import { api } from './api';

export interface CalendarEvent {
  id: string;
  tenant_id: string;
  user_id: string;
  contact_id?: string;
  title: string;
  description?: string;
  start_time: string;
  end_time: string;
  all_day: boolean;
  location?: string;
  event_type: 'appointment' | 'service' | 'meeting' | 'call' | 'reminder' | 'other';
  status: 'confirmed' | 'tentative' | 'cancelled';
  event_metadata?: Record<string, any>;
  created_at: string;
  updated_at?: string;
  created_by_user_id?: string;
  contact_name?: string;
  contact_business?: string;
}

export interface CalendarEventCreate {
  title: string;
  description?: string;
  start_time: string;
  end_time: string;
  all_day?: boolean;
  location?: string;
  event_type?: 'appointment' | 'service' | 'meeting' | 'call' | 'reminder' | 'other';
  status?: 'confirmed' | 'tentative' | 'cancelled';
  event_metadata?: Record<string, any>;
  contact_id?: string;
  user_id?: string;
}

export interface CalendarEventUpdate {
  title?: string;
  description?: string;
  start_time?: string;
  end_time?: string;
  all_day?: boolean;
  location?: string;
  event_type?: 'appointment' | 'service' | 'meeting' | 'call' | 'reminder' | 'other';
  status?: 'confirmed' | 'tentative' | 'cancelled';
  event_metadata?: Record<string, any>;
  contact_id?: string;
}

export interface CalendarEventList {
  events: CalendarEvent[];
  total: number;
  skip: number;
  limit: number;
}

export interface CalendarStats {
  month: number;
  year: number;
  total_events: number;
  events_by_type: Record<string, number>;
  events_by_status: Record<string, number>;
  date_range: {
    start: string;
    end: string;
  };
}

export interface CalendarEventAttendee {
  id: string;
  event_id: string;
  attendee_type: 'user' | 'contact' | 'external';
  user_id?: string;
  contact_id?: string;
  external_email?: string;
  external_name?: string;
  invitation_status: 'pending' | 'sent' | 'delivered' | 'failed';
  response_status: 'no_response' | 'accepted' | 'declined' | 'tentative';
  invitation_token: string;
  invited_at?: string;
  responded_at?: string;
  created_at: string;
  updated_at?: string;
  attendee_email?: string;
  attendee_name?: string;
}

export interface CalendarEventAttendeeCreate {
  attendee_type: 'user' | 'contact' | 'external';
  user_id?: string;
  contact_id?: string;
  external_email?: string;
  external_name?: string;
}

export interface CalendarEventAttendeeList {
  attendees: CalendarEventAttendee[];
  total: number;
}

export interface AttendeeInvitationRequest {
  attendee_ids: string[];
  send_invitations?: boolean;
  custom_message?: string;
}

export interface RSVPResponse {
  response_status: 'accepted' | 'declined' | 'tentative';
  attendee_name?: string;
}

export interface CalendarEventFilters {
  start_date?: string;
  end_date?: string;
  user_id?: string;
  contact_id?: string;
  event_type?: string;
  status?: string;
  skip?: number;
  limit?: number;
}

class CalendarService {
  
  /**
   * List calendar events with optional filters
   */
  async listEvents(filters: CalendarEventFilters = {}): Promise<CalendarEventList> {
    const { data } = await api.get<CalendarEventList>('/calendar/events', {
      params: filters as Record<string, string | number>
    });
    return data;
  }

  /**
   * Get events within a specific date range
   */
  async getEventsInRange(
    start: string, 
    end: string, 
    userId?: string
  ): Promise<CalendarEvent[]> {
    const params: Record<string, string> = { start, end };
    if (userId) params.user_id = userId;
    
    const { data } = await api.get<CalendarEvent[]>('/calendar/events/range', {
      params
    });
    return data;
  }

  /**
   * Get a single calendar event
   */
  async getEvent(eventId: string): Promise<CalendarEvent> {
    const { data } = await api.get<CalendarEvent>(`/calendar/events/${eventId}`);
    return data;
  }

  /**
   * Create a new calendar event
   */
  async createEvent(eventData: CalendarEventCreate): Promise<CalendarEvent> {
    const { data } = await api.post<CalendarEvent>('/calendar/events', eventData);
    return data;
  }

  /**
   * Update an existing calendar event
   */
  async updateEvent(
    eventId: string, 
    eventData: CalendarEventUpdate
  ): Promise<CalendarEvent> {
    const { data } = await api.put<CalendarEvent>(`/calendar/events/${eventId}`, eventData);
    return data;
  }

  /**
   * Delete a calendar event
   */
  async deleteEvent(eventId: string): Promise<void> {
    await api.delete(`/calendar/events/${eventId}`);
  }

  /**
   * Get calendar statistics
   */
  async getStats(month?: number, year?: number): Promise<CalendarStats> {
    const params: Record<string, number> = {};
    if (month) params.month = month;
    if (year) params.year = year;

    const { data } = await api.get<CalendarStats>('/calendar/events/stats/summary', {
      params
    });
    return data;
  }

  /**
   * Get today's events
   */
  async getTodayEvents(): Promise<CalendarEvent[]> {
    const today = new Date();
    const startOfDay = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    const endOfDay = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 1);
    
    return this.getEventsInRange(
      startOfDay.toISOString(),
      endOfDay.toISOString()
    );
  }

  /**
   * Get this week's events
   */
  async getWeekEvents(weekStart?: Date): Promise<CalendarEvent[]> {
    const start = weekStart || this.getStartOfWeek(new Date());
    const end = new Date(start);
    end.setDate(start.getDate() + 7);
    
    return this.getEventsInRange(start.toISOString(), end.toISOString());
  }

  /**
   * Get this month's events
   */
  async getMonthEvents(year?: number, month?: number): Promise<CalendarEvent[]> {
    const now = new Date();
    const targetYear = year ?? now.getFullYear();
    const targetMonth = month ?? now.getMonth();
    
    const start = new Date(targetYear, targetMonth, 1);
    const end = new Date(targetYear, targetMonth + 1, 1);
    
    return this.getEventsInRange(start.toISOString(), end.toISOString());
  }

  /**
   * Get events for a specific contact
   */
  async getContactEvents(contactId: string): Promise<CalendarEvent[]> {
    const { data } = await api.get<CalendarEventList>('/calendar/events', {
      params: { contact_id: contactId, limit: 1000 }
    });
    return data.events;
  }

  /**
   * Utility: Get start of week (Monday)
   */
  private getStartOfWeek(date: Date): Date {
    const start = new Date(date);
    const day = start.getDay();
    const diff = start.getDate() - day + (day === 0 ? -6 : 1); // Monday
    start.setDate(diff);
    start.setHours(0, 0, 0, 0);
    return start;
  }

  /**
   * Utility: Format date for API
   */
  formatDateForAPI(date: Date): string {
    return date.toISOString();
  }

  /**
   * Utility: Parse API date
   */
  parseAPIDate(dateString: string): Date {
    return new Date(dateString);
  }

  // Attendee Management Methods

  /**
   * List attendees for an event
   */
  async listEventAttendees(eventId: string): Promise<CalendarEventAttendeeList> {
    const { data } = await api.get<CalendarEventAttendeeList>(`/calendar/events/${eventId}/attendees`);
    return data;
  }

  /**
   * Add an attendee to an event
   */
  async addEventAttendee(
    eventId: string, 
    attendeeData: CalendarEventAttendeeCreate
  ): Promise<CalendarEventAttendee> {
    const { data } = await api.post<CalendarEventAttendee>(
      `/calendar/events/${eventId}/attendees`, 
      attendeeData
    );
    return data;
  }

  /**
   * Remove an attendee from an event
   */
  async removeEventAttendee(eventId: string, attendeeId: string): Promise<void> {
    await api.delete(`/calendar/events/${eventId}/attendees/${attendeeId}`);
  }

  /**
   * Send invitations to attendees
   */
  async sendEventInvitations(
    eventId: string, 
    invitationRequest: AttendeeInvitationRequest
  ): Promise<{
    detail: string;
    sent_count: number;
    failed_count: number;
  }> {
    const { data } = await api.post<{
      detail: string;
      sent_count: number;
      failed_count: number;
    }>(`/calendar/events/${eventId}/send-invitations`, invitationRequest);
    return data;
  }

  /**
   * Get RSVP details (public endpoint)
   */
  async getRSVPDetails(invitationToken: string): Promise<{
    attendee: CalendarEventAttendee;
    event: {
      id: string;
      title: string;
      description?: string;
      start_time: string;
      end_time: string;
      location?: string;
      all_day: boolean;
    };
  }> {
    const { data } = await api.get<{
      attendee: CalendarEventAttendee;
      event: {
        id: string;
        title: string;
        description?: string;
        start_time: string;
        end_time: string;
        location?: string;
        all_day: boolean;
      };
    }>(`/calendar/rsvp/${invitationToken}`);
    return data;
  }

  /**
   * Respond to RSVP (public endpoint)
   */
  async respondToRSVP(
    invitationToken: string, 
    response: RSVPResponse
  ): Promise<{
    detail: string;
    response_status: string;
    responded_at: string;
  }> {
    const { data } = await api.post<{
      detail: string;
      response_status: string;
      responded_at: string;
    }>(`/calendar/rsvp/${invitationToken}/respond`, response);
    return data;
  }

  /**
   * Download event as ICS file
   */
  downloadEventICS(eventId: string): string {
    return `${api.defaults.baseURL}/calendar/events/${eventId}/ics`;
  }

  /**
   * Add multiple attendees at once
   */
  async addMultipleAttendees(
    eventId: string, 
    attendees: CalendarEventAttendeeCreate[]
  ): Promise<CalendarEventAttendee[]> {
    const results: CalendarEventAttendee[] = [];
    
    for (const attendee of attendees) {
      try {
        const result = await this.addEventAttendee(eventId, attendee);
        results.push(result);
      } catch (error) {
        console.error('Failed to add attendee:', attendee, error);
        // Continue with other attendees even if one fails
      }
    }
    
    return results;
  }

  /**
   * Get attendee statistics for an event
   */
  async getEventAttendeeStats(eventId: string): Promise<{
    total: number;
    by_type: Record<string, number>;
    by_status: Record<string, number>;
    by_response: Record<string, number>;
  }> {
    const attendees = await this.listEventAttendees(eventId);
    
    const stats = {
      total: attendees.total,
      by_type: {} as Record<string, number>,
      by_status: {} as Record<string, number>,
      by_response: {} as Record<string, number>
    };
    
    // Calculate statistics
    attendees.attendees.forEach(attendee => {
      // By type
      stats.by_type[attendee.attendee_type] = (stats.by_type[attendee.attendee_type] || 0) + 1;
      
      // By invitation status
      stats.by_status[attendee.invitation_status] = (stats.by_status[attendee.invitation_status] || 0) + 1;
      
      // By response status
      stats.by_response[attendee.response_status] = (stats.by_response[attendee.response_status] || 0) + 1;
    });
    
    return stats;
  }
}

// Export singleton instance
export const calendarService = new CalendarService();