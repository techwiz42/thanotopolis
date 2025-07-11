'use client';

import React from 'react';
import { Clock, MapPin, User, Building2, Phone } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { CalendarEvent } from '@/services/calendar';

interface EventCardProps {
  event: CalendarEvent;
  compact?: boolean;
  onClick?: () => void;
}

const EVENT_TYPE_COLORS: Record<string, string> = {
  appointment: 'bg-blue-100 text-blue-800',
  service: 'bg-green-100 text-green-800',
  meeting: 'bg-purple-100 text-purple-800',
  call: 'bg-orange-100 text-orange-800',
  reminder: 'bg-yellow-100 text-yellow-800',
  other: 'bg-gray-100 text-gray-800',
};

const EVENT_STATUS_COLORS: Record<string, string> = {
  confirmed: 'bg-green-100 text-green-800',
  tentative: 'bg-yellow-100 text-yellow-800',
  cancelled: 'bg-red-100 text-red-800',
};

const EVENT_TYPE_ICONS: Record<string, React.ReactNode> = {
  appointment: <Clock className="h-4 w-4" />,
  service: <Building2 className="h-4 w-4" />,
  meeting: <User className="h-4 w-4" />,
  call: <Phone className="h-4 w-4" />,
  reminder: <Clock className="h-4 w-4" />,
  other: <Clock className="h-4 w-4" />,
};

export function EventCard({ event, compact = false, onClick }: EventCardProps) {
  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    });
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      weekday: 'short',
      month: 'short', 
      day: 'numeric' 
    });
  };

  const getTimeDisplay = () => {
    if (event.all_day) {
      return 'All day';
    }
    return `${formatTime(event.start_time)} - ${formatTime(event.end_time)}`;
  };

  if (compact) {
    return (
      <div
        className="p-3 border border-gray-200 rounded-lg hover:shadow-md transition-shadow cursor-pointer"
        onClick={onClick}
      >
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              {EVENT_TYPE_ICONS[event.event_type]}
              <h3 className="font-medium text-sm truncate">{event.title}</h3>
            </div>
            
            <div className="text-xs text-gray-600 flex items-center gap-1 mb-1">
              <Clock className="h-3 w-3" />
              {getTimeDisplay()}
            </div>
            
            {event.location && (
              <div className="text-xs text-gray-600 flex items-center gap-1 mb-1">
                <MapPin className="h-3 w-3" />
                <span className="truncate">{event.location}</span>
              </div>
            )}
            
            {(event.contact_name || event.contact_business) && (
              <div className="text-xs text-gray-600 flex items-center gap-1">
                <User className="h-3 w-3" />
                <span className="truncate">
                  {event.contact_name} {event.contact_business && `(${event.contact_business})`}
                </span>
              </div>
            )}
          </div>
          
          <div className="flex flex-col gap-1 ml-2">
            <Badge className={`text-xs ${EVENT_TYPE_COLORS[event.event_type]}`}>
              {event.event_type}
            </Badge>
            {event.status !== 'confirmed' && (
              <Badge className={`text-xs ${EVENT_STATUS_COLORS[event.status]}`}>
                {event.status}
              </Badge>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="p-4 border border-gray-200 rounded-lg hover:shadow-md transition-shadow cursor-pointer"
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          {EVENT_TYPE_ICONS[event.event_type]}
          <h3 className="font-semibold text-lg">{event.title}</h3>
        </div>
        
        <div className="flex gap-2">
          <Badge className={EVENT_TYPE_COLORS[event.event_type]}>
            {event.event_type}
          </Badge>
          {event.status !== 'confirmed' && (
            <Badge className={EVENT_STATUS_COLORS[event.status]}>
              {event.status}
            </Badge>
          )}
        </div>
      </div>

      {event.description && (
        <p className="text-gray-600 mb-3 text-sm">{event.description}</p>
      )}

      <div className="space-y-2 text-sm">
        <div className="flex items-center gap-2 text-gray-600">
          <Clock className="h-4 w-4" />
          <span>{formatDate(event.start_time)} • {getTimeDisplay()}</span>
        </div>
        
        {event.location && (
          <div className="flex items-center gap-2 text-gray-600">
            <MapPin className="h-4 w-4" />
            <span>{event.location}</span>
          </div>
        )}
        
        {(event.contact_name || event.contact_business) && (
          <div className="flex items-center gap-2 text-gray-600">
            <User className="h-4 w-4" />
            <span>
              {event.contact_name} 
              {event.contact_business && ` (${event.contact_business})`}
            </span>
          </div>
        )}
      </div>

      {event.event_metadata && Object.keys(event.event_metadata).length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <div className="text-xs text-gray-500">
            Additional info available
          </div>
        </div>
      )}
    </div>
  );
}