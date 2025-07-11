'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Calendar, Clock, MapPin, User, Building2, AlertCircle, Trash2 } from 'lucide-react';
import { 
  calendarService, 
  CalendarEvent, 
  CalendarEventCreate, 
  CalendarEventUpdate,
  CalendarEventAttendee
} from '@/services/calendar';
import { AttendeeManagerEnhanced } from './AttendeeManagerEnhanced';

interface Contact {
  id: string;
  business_name: string;
  contact_name: string;
  contact_email?: string;
  phone?: string;
  city?: string;
  state?: string;
  status: string;
}

interface EventFormProps {
  event?: CalendarEvent | null;
  defaultDate?: Date | null;
  onEventCreated: (event: CalendarEvent) => void;
  onEventUpdated: (event: CalendarEvent) => void;
  onEventDeleted: () => void;
  onCancel: () => void;
}

export function EventForm({
  event,
  defaultDate,
  onEventCreated,
  onEventUpdated,
  onEventDeleted,
  onCancel
}: EventFormProps) {
  const [loading, setLoading] = useState(false);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [contactsLoading, setContactsLoading] = useState(false);
  const [contactSearch, setContactSearch] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  
  // Attendee management state
  const [currentEventId, setCurrentEventId] = useState<string | undefined>(event?.id);
  const [attendees, setAttendees] = useState<CalendarEventAttendee[]>([]);

  // Form data
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [startDate, setStartDate] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endDate, setEndDate] = useState('');
  const [endTime, setEndTime] = useState('');
  const [allDay, setAllDay] = useState(false);
  const [location, setLocation] = useState('');
  const [eventType, setEventType] = useState<'appointment' | 'service' | 'meeting' | 'call' | 'reminder' | 'other'>('appointment');
  const [status, setStatus] = useState<'confirmed' | 'tentative' | 'cancelled'>('confirmed');
  const [contactId, setContactId] = useState('');
  const [eventMetadata, setEventMetadata] = useState('');

  useEffect(() => {
    loadContacts();
    
    if (event) {
      // Edit mode - populate form with existing event data
      setTitle(event.title);
      setDescription(event.description || '');
      
      const startDateTime = new Date(event.start_time);
      const endDateTime = new Date(event.end_time);
      
      setStartDate(startDateTime.toISOString().split('T')[0]);
      setStartTime(startDateTime.toTimeString().slice(0, 5));
      setEndDate(endDateTime.toISOString().split('T')[0]);
      setEndTime(endDateTime.toTimeString().slice(0, 5));
      
      setAllDay(event.all_day);
      setLocation(event.location || '');
      setEventType(event.event_type);
      setStatus(event.status);
      setContactId(event.contact_id || '');
      setEventMetadata(JSON.stringify(event.event_metadata || {}, null, 2));
    } else if (defaultDate) {
      // Create mode with default date
      const date = defaultDate.toISOString().split('T')[0];
      const time = defaultDate.toTimeString().slice(0, 5);
      setStartDate(date);
      setStartTime(time);
      
      const endDateTime = new Date(defaultDate);
      endDateTime.setHours(endDateTime.getHours() + 1);
      setEndDate(endDateTime.toISOString().split('T')[0]);
      setEndTime(endDateTime.toTimeString().slice(0, 5));
    } else {
      // Create mode with current date/time
      const now = new Date();
      const date = now.toISOString().split('T')[0];
      const time = now.toTimeString().slice(0, 5);
      setStartDate(date);
      setStartTime(time);
      
      const endTime = new Date(now.getTime() + 60 * 60 * 1000);
      setEndDate(endTime.toISOString().split('T')[0]);
      setEndTime(endTime.toTimeString().slice(0, 5));
    }
  }, [event, defaultDate]);

  const loadContacts = async () => {
    try {
      setContactsLoading(true);
      
      // Get tokens from localStorage in the correct format
      const tokens = localStorage.getItem('tokens');
      let authHeader = '';
      if (tokens) {
        try {
          const parsedTokens = JSON.parse(tokens);
          if (parsedTokens.access_token) {
            authHeader = `Bearer ${parsedTokens.access_token}`;
          }
        } catch (error) {
          console.warn('Failed to parse tokens:', error);
        }
      }
      
      const response = await fetch('/api/crm/contacts?limit=1000', {
        headers: {
          'Authorization': authHeader,
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setContacts(data.contacts || []);
      }
    } catch (error) {
      console.error('Failed to load contacts:', error);
    } finally {
      setContactsLoading(false);
    }
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!title.trim()) {
      newErrors.title = 'Title is required';
    }

    if (!startDate) {
      newErrors.startDate = 'Start date is required';
    }

    if (!allDay && !startTime) {
      newErrors.startTime = 'Start time is required for non-all-day events';
    }

    if (!endDate) {
      newErrors.endDate = 'End date is required';
    }

    if (!allDay && !endTime) {
      newErrors.endTime = 'End time is required for non-all-day events';
    }

    // Validate end time is after start time
    if (startDate && endDate && startTime && endTime) {
      const startDateTime = new Date(`${startDate}T${startTime}`);
      const endDateTime = new Date(`${endDate}T${endTime}`);
      
      if (endDateTime <= startDateTime) {
        newErrors.endTime = 'End time must be after start time';
      }
    }

    // Validate metadata JSON if provided
    if (eventMetadata.trim()) {
      try {
        JSON.parse(eventMetadata);
      } catch {
        newErrors.eventMetadata = 'Invalid JSON format';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      return;
    }

    try {
      setLoading(true);

      // Prepare datetime strings
      const startDateTime = allDay 
        ? new Date(`${startDate}T00:00:00`).toISOString()
        : new Date(`${startDate}T${startTime}`).toISOString();
      
      const endDateTime = allDay 
        ? new Date(`${endDate}T23:59:59`).toISOString()
        : new Date(`${endDate}T${endTime}`).toISOString();

      // Prepare metadata
      let metadata = undefined;
      if (eventMetadata.trim()) {
        try {
          metadata = JSON.parse(eventMetadata);
        } catch {
          // Already validated above
        }
      }

      const eventData = {
        title: title.trim(),
        description: description.trim() || undefined,
        start_time: startDateTime,
        end_time: endDateTime,
        all_day: allDay,
        location: location.trim() || undefined,
        event_type: eventType,
        status,
        contact_id: contactId || undefined,
        event_metadata: metadata,
      };

      if (event) {
        // Update existing event
        const updatedEvent = await calendarService.updateEvent(event.id, eventData);
        onEventUpdated(updatedEvent);
      } else {
        // Create new event
        const newEvent = await calendarService.createEvent(eventData);
        setCurrentEventId(newEvent.id); // Set the event ID for attendee management
        onEventCreated(newEvent);
      }
    } catch (error) {
      console.error('Failed to save event:', error);
      setErrors({ general: 'Failed to save event. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!event || !confirm('Are you sure you want to delete this event?')) {
      return;
    }

    try {
      setLoading(true);
      await calendarService.deleteEvent(event.id);
      onEventDeleted();
    } catch (error) {
      console.error('Failed to delete event:', error);
      setErrors({ general: 'Failed to delete event. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  const filteredContacts = contacts.filter(contact => 
    contact.business_name.toLowerCase().includes(contactSearch.toLowerCase()) ||
    contact.contact_name.toLowerCase().includes(contactSearch.toLowerCase())
  );

  const selectedContact = contacts.find(c => c.id === contactId);

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 space-y-6 overflow-y-auto">
        {errors.general && (
          <div className="flex items-center gap-2 text-red-600 bg-red-50 p-3 rounded-lg">
            <AlertCircle className="h-4 w-4" />
            {errors.general}
          </div>
        )}

      {/* Basic Information */}
      <div className="space-y-4">
        <div>
          <Label htmlFor="title">Event Title *</Label>
          <Input
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Enter event title"
            className={errors.title ? 'border-red-500' : ''}
          />
          {errors.title && <p className="text-sm text-red-600 mt-1">{errors.title}</p>}
        </div>

        <div>
          <Label htmlFor="description">Description</Label>
          <Textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Enter event description"
            rows={3}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="eventType">Event Type</Label>
            <Select value={eventType} onValueChange={(value: any) => setEventType(value)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="appointment">Appointment</SelectItem>
                <SelectItem value="service">Service</SelectItem>
                <SelectItem value="meeting">Meeting</SelectItem>
                <SelectItem value="call">Call</SelectItem>
                <SelectItem value="reminder">Reminder</SelectItem>
                <SelectItem value="other">Other</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="status">Status</Label>
            <Select value={status} onValueChange={(value: any) => setStatus(value)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="confirmed">Confirmed</SelectItem>
                <SelectItem value="tentative">Tentative</SelectItem>
                <SelectItem value="cancelled">Cancelled</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      <Separator />

      {/* Date and Time */}
      <div className="space-y-4">
        <div className="flex items-center space-x-2">
          <Checkbox
            id="allDay"
            checked={allDay}
            onCheckedChange={(checked) => setAllDay(checked as boolean)}
          />
          <Label htmlFor="allDay">All day event</Label>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="startDate">Start Date *</Label>
            <Input
              id="startDate"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className={errors.startDate ? 'border-red-500' : ''}
            />
            {errors.startDate && <p className="text-sm text-red-600 mt-1">{errors.startDate}</p>}
          </div>

          <div>
            <Label htmlFor="endDate">End Date *</Label>
            <Input
              id="endDate"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className={errors.endDate ? 'border-red-500' : ''}
            />
            {errors.endDate && <p className="text-sm text-red-600 mt-1">{errors.endDate}</p>}
          </div>
        </div>

        {!allDay && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="startTime">Start Time *</Label>
              <Input
                id="startTime"
                type="time"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                className={errors.startTime ? 'border-red-500' : ''}
              />
              {errors.startTime && <p className="text-sm text-red-600 mt-1">{errors.startTime}</p>}
            </div>

            <div>
              <Label htmlFor="endTime">End Time *</Label>
              <Input
                id="endTime"
                type="time"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                className={errors.endTime ? 'border-red-500' : ''}
              />
              {errors.endTime && <p className="text-sm text-red-600 mt-1">{errors.endTime}</p>}
            </div>
          </div>
        )}
      </div>

      <Separator />

      {/* Location */}
      <div>
        <Label htmlFor="location">Location</Label>
        <Input
          id="location"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          placeholder="Enter event location"
        />
      </div>

      <Separator />

      {/* CRM Integration */}
      <div className="space-y-4">
        <Label>Link to Contact (Optional)</Label>
        
        {selectedContact ? (
          <div className="flex items-center justify-between p-3 border rounded-lg bg-gray-50">
            <div className="flex items-center gap-3">
              <Building2 className="h-4 w-4 text-gray-600" />
              <div>
                <p className="font-medium">{selectedContact.business_name}</p>
                <p className="text-sm text-gray-600">{selectedContact.contact_name}</p>
                {selectedContact.contact_email && (
                  <p className="text-sm text-gray-600">{selectedContact.contact_email}</p>
                )}
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setContactId('')}
            >
              Remove
            </Button>
          </div>
        ) : (
          <div className="space-y-2">
            <Input
              placeholder="Search contacts..."
              value={contactSearch}
              onChange={(e) => setContactSearch(e.target.value)}
            />
            
            {contactsLoading ? (
              <p className="text-sm text-gray-500">Loading contacts...</p>
            ) : filteredContacts.length > 0 ? (
              <div className="max-h-40 overflow-y-auto border rounded-lg">
                {filteredContacts.slice(0, 10).map((contact) => (
                  <div
                    key={contact.id}
                    className="p-2 hover:bg-gray-50 cursor-pointer border-b last:border-b-0"
                    onClick={() => {
                      setContactId(contact.id);
                      setContactSearch('');
                    }}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-sm">{contact.business_name}</p>
                        <p className="text-xs text-gray-600">{contact.contact_name}</p>
                      </div>
                      <Badge variant="outline" className="text-xs">
                        {contact.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : contactSearch ? (
              <p className="text-sm text-gray-500">No contacts found</p>
            ) : null}
          </div>
        )}
      </div>

      {/* Advanced Metadata */}
      <details className="space-y-2">
        <summary className="cursor-pointer text-sm font-medium">Advanced Options</summary>
        <div className="space-y-2 mt-2">
          <Label htmlFor="eventMetadata">Event Metadata (JSON)</Label>
          <Textarea
            id="eventMetadata"
            value={eventMetadata}
            onChange={(e) => setEventMetadata(e.target.value)}
            placeholder='{"notes": "Additional information", "priority": "high"}'
            rows={3}
            className={errors.eventMetadata ? 'border-red-500' : ''}
          />
          {errors.eventMetadata && <p className="text-sm text-red-600 mt-1">{errors.eventMetadata}</p>}
          <p className="text-xs text-gray-500">
            Optional JSON data for additional event information
          </p>
        </div>
      </details>

      <Separator />

      {/* Attendee Management */}
      <AttendeeManagerEnhanced 
        eventId={currentEventId}
        isEventCreated={!!currentEventId}
        onAttendeesChange={setAttendees}
      />
      </div>

      {/* Actions - Always visible at bottom */}
      <div className="flex-shrink-0 flex items-center justify-between pt-4 border-t bg-white">
        <div>
          {event && (
            <Button
              variant="destructive"
              size="sm"
              onClick={handleDelete}
              disabled={loading}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete Event
            </Button>
          )}
        </div>
        
        <div className="flex gap-2">
          <Button variant="outline" onClick={onCancel} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={loading}>
            {loading ? 'Saving...' : event ? 'Update Event' : 'Create Event'}
          </Button>
        </div>
      </div>
    </div>
  );
}