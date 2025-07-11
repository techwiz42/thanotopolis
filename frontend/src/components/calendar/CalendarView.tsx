'use client';

import React from 'react';
import { CalendarEvent } from '@/services/calendar';

interface CalendarViewProps {
  currentDate: Date;
  events: CalendarEvent[];
  view: 'month' | 'week' | 'day';
  onDateClick: (date: Date) => void;
  onEventClick: (event: CalendarEvent) => void;
  onCreateEvent: (date: Date) => void;
}

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export function CalendarView({
  currentDate,
  events,
  view,
  onDateClick,
  onEventClick,
  onCreateEvent
}: CalendarViewProps) {
  
  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    });
  };

  const getEventColor = (eventType: string) => {
    const colors: Record<string, string> = {
      appointment: 'bg-blue-100 border-blue-300 text-blue-800',
      service: 'bg-green-100 border-green-300 text-green-800',
      meeting: 'bg-purple-100 border-purple-300 text-purple-800',
      call: 'bg-orange-100 border-orange-300 text-orange-800',
      reminder: 'bg-yellow-100 border-yellow-300 text-yellow-800',
      other: 'bg-gray-100 border-gray-300 text-gray-800',
    };
    return colors[eventType] || colors.other;
  };

  const getEventsForDate = (date: Date) => {
    return events.filter(event => {
      const eventDate = new Date(event.start_time);
      return eventDate.toDateString() === date.toDateString();
    });
  };

  const renderMonthView = () => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    
    // Get first day of month and calculate starting day
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startDate = new Date(firstDay);
    const dayOfWeek = (firstDay.getDay() + 6) % 7; // Convert Sunday=0 to Monday=0
    startDate.setDate(startDate.getDate() - dayOfWeek);
    
    const days = [];
    const endDate = new Date(lastDay);
    endDate.setDate(endDate.getDate() + (6 - ((endDate.getDay() + 6) % 7)));
    
    const current = new Date(startDate);
    while (current <= endDate) {
      days.push(new Date(current));
      current.setDate(current.getDate() + 1);
    }

    return (
      <div className="space-y-2">
        {/* Days header */}
        <div className="grid grid-cols-7 gap-1 mb-2">
          {DAYS.map(day => (
            <div key={day} className="p-2 text-center text-sm font-medium text-gray-600">
              {day}
            </div>
          ))}
        </div>
        
        {/* Calendar grid */}
        <div className="grid grid-cols-7 gap-1">
          {days.map((date, index) => {
            const isCurrentMonth = date.getMonth() === month;
            const isToday = date.toDateString() === new Date().toDateString();
            const dayEvents = getEventsForDate(date);
            
            return (
              <div
                key={index}
                className={`
                  min-h-[100px] p-1 border border-gray-200 cursor-pointer hover:bg-gray-50
                  ${!isCurrentMonth ? 'bg-gray-50 text-gray-400' : 'bg-white'}
                  ${isToday ? 'ring-2 ring-blue-500' : ''}
                `}
                onClick={() => onDateClick(date)}
                onDoubleClick={() => onCreateEvent(date)}
              >
                <div className={`
                  text-sm font-medium p-1
                  ${isToday ? 'text-blue-600' : isCurrentMonth ? 'text-gray-900' : 'text-gray-400'}
                `}>
                  {date.getDate()}
                </div>
                
                <div className="space-y-1 max-h-[70px] overflow-hidden">
                  {dayEvents.slice(0, 3).map((event) => (
                    <div
                      key={event.id}
                      className={`
                        text-xs p-1 rounded border cursor-pointer hover:opacity-80
                        ${getEventColor(event.event_type)}
                      `}
                      onClick={(e) => {
                        e.stopPropagation();
                        onEventClick(event);
                      }}
                    >
                      <div className="truncate font-medium">{event.title}</div>
                      {!event.all_day && (
                        <div className="truncate opacity-75">
                          {formatTime(event.start_time)}
                        </div>
                      )}
                    </div>
                  ))}
                  {dayEvents.length > 3 && (
                    <div className="text-xs text-gray-500 px-1">
                      +{dayEvents.length - 3} more
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderWeekView = () => {
    const startOfWeek = new Date(currentDate);
    const day = startOfWeek.getDay();
    const diff = startOfWeek.getDate() - day + (day === 0 ? -6 : 1); // Monday
    startOfWeek.setDate(diff);
    startOfWeek.setHours(0, 0, 0, 0);

    const weekDays: Date[] = [];
    for (let i = 0; i < 7; i++) {
      const date = new Date(startOfWeek);
      date.setDate(startOfWeek.getDate() + i);
      weekDays.push(date);
    }

    const hours = Array.from({ length: 24 }, (_, i) => i);

    return (
      <div className="space-y-2">
        {/* Week header */}
        <div className="grid grid-cols-8 gap-1 mb-2">
          <div className="p-2"></div> {/* Time column header */}
          {weekDays.map((date, index) => {
            const isToday = date.toDateString() === new Date().toDateString();
            return (
              <div key={index} className={`p-2 text-center text-sm font-medium ${isToday ? 'text-blue-600' : 'text-gray-600'}`}>
                <div>{DAYS[index]}</div>
                <div className={`text-lg ${isToday ? 'bg-blue-600 text-white rounded-full w-8 h-8 flex items-center justify-center mx-auto' : ''}`}>
                  {date.getDate()}
                </div>
              </div>
            );
          })}
        </div>

        {/* Week grid */}
        <div className="grid grid-cols-8 gap-1 max-h-[600px] overflow-y-auto">
          {hours.map(hour => (
            <React.Fragment key={hour}>
              {/* Time label */}
              <div className="p-2 text-xs text-gray-500 text-right border-r">
                {hour === 0 ? '12 AM' : hour < 12 ? `${hour} AM` : hour === 12 ? '12 PM' : `${hour - 12} PM`}
              </div>
              
              {/* Hour slots for each day */}
              {weekDays.map((date, dayIndex) => {
                const hourDate = new Date(date);
                hourDate.setHours(hour, 0, 0, 0);
                const hourEvents = events.filter(event => {
                  const eventStart = new Date(event.start_time);
                  return eventStart.getDate() === date.getDate() &&
                         eventStart.getMonth() === date.getMonth() &&
                         eventStart.getHours() === hour;
                });

                return (
                  <div
                    key={`${hour}-${dayIndex}`}
                    className="min-h-[60px] p-1 border border-gray-100 cursor-pointer hover:bg-gray-50"
                    onClick={() => onCreateEvent(hourDate)}
                  >
                    {hourEvents.map(event => (
                      <div
                        key={event.id}
                        className={`
                          text-xs p-1 mb-1 rounded border cursor-pointer hover:opacity-80
                          ${getEventColor(event.event_type)}
                        `}
                        onClick={(e) => {
                          e.stopPropagation();
                          onEventClick(event);
                        }}
                      >
                        <div className="font-medium truncate">{event.title}</div>
                        <div className="truncate opacity-75">
                          {formatTime(event.start_time)} - {formatTime(event.end_time)}
                        </div>
                      </div>
                    ))}
                  </div>
                );
              })}
            </React.Fragment>
          ))}
        </div>
      </div>
    );
  };

  const renderDayView = () => {
    const dayEvents = getEventsForDate(currentDate);
    const hours = Array.from({ length: 24 }, (_, i) => i);

    return (
      <div className="space-y-2">
        {/* Day header */}
        <div className="text-center p-4 border-b">
          <div className="text-sm text-gray-600">
            {currentDate.toLocaleDateString('en-US', { weekday: 'long' })}
          </div>
          <div className="text-2xl font-bold">
            {currentDate.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
          </div>
        </div>

        {/* Day grid */}
        <div className="max-h-[600px] overflow-y-auto">
          {hours.map(hour => {
            const hourDate = new Date(currentDate);
            hourDate.setHours(hour, 0, 0, 0);
            const hourEvents = dayEvents.filter(event => {
              const eventStart = new Date(event.start_time);
              return eventStart.getHours() === hour;
            });

            return (
              <div key={hour} className="flex border-b border-gray-100">
                {/* Time label */}
                <div className="w-20 p-2 text-xs text-gray-500 text-right border-r">
                  {hour === 0 ? '12 AM' : hour < 12 ? `${hour} AM` : hour === 12 ? '12 PM' : `${hour - 12} PM`}
                </div>
                
                {/* Hour content */}
                <div
                  className="flex-1 min-h-[60px] p-2 cursor-pointer hover:bg-gray-50"
                  onClick={() => onCreateEvent(hourDate)}
                >
                  {hourEvents.map(event => (
                    <div
                      key={event.id}
                      className={`
                        p-2 mb-2 rounded border cursor-pointer hover:opacity-80
                        ${getEventColor(event.event_type)}
                      `}
                      onClick={(e) => {
                        e.stopPropagation();
                        onEventClick(event);
                      }}
                    >
                      <div className="font-medium">{event.title}</div>
                      <div className="text-sm opacity-75">
                        {formatTime(event.start_time)} - {formatTime(event.end_time)}
                      </div>
                      {event.location && (
                        <div className="text-sm opacity-75">📍 {event.location}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  switch (view) {
    case 'week':
      return renderWeekView();
    case 'day':
      return renderDayView();
    default:
      return renderMonthView();
  }
}