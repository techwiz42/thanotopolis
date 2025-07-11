'use client';

import React, { useState, useEffect } from 'react';
import { Calendar, CalendarDays, Plus, ChevronLeft, ChevronRight, Clock, MapPin, User, Building2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

import { calendarService, CalendarEvent, CalendarStats } from '@/services/calendar';
import { EventForm } from '@/components/calendar/EventForm';
import { CalendarView } from '@/components/calendar/CalendarView';
import { EventCard } from '@/components/calendar/EventCard';

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

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

export default function CalendarPage() {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [stats, setStats] = useState<CalendarStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<'month' | 'week' | 'day'>('month');
  const [showEventForm, setShowEventForm] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);

  const currentYear = currentDate.getFullYear();
  const currentMonth = currentDate.getMonth();

  useEffect(() => {
    loadData();
  }, [currentYear, currentMonth]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [monthEvents, monthStats] = await Promise.all([
        calendarService.getMonthEvents(currentYear, currentMonth),
        calendarService.getStats(currentMonth + 1, currentYear)
      ]);
      setEvents(monthEvents);
      setStats(monthStats);
    } catch (error) {
      console.error('Failed to load calendar data:', error);
    } finally {
      setLoading(false);
    }
  };

  const navigateMonth = (direction: 'prev' | 'next') => {
    const newDate = new Date(currentDate);
    if (direction === 'prev') {
      newDate.setMonth(currentMonth - 1);
    } else {
      newDate.setMonth(currentMonth + 1);
    }
    setCurrentDate(newDate);
  };

  const goToToday = () => {
    setCurrentDate(new Date());
  };

  const handleEventCreated = async (event: CalendarEvent) => {
    await loadData();
    setShowEventForm(false);
    setSelectedEvent(null);
  };

  const handleEventUpdated = async (event: CalendarEvent) => {
    await loadData();
    setShowEventForm(false);
    setSelectedEvent(null);
  };

  const handleEventDeleted = async () => {
    await loadData();
    setShowEventForm(false);
    setSelectedEvent(null);
  };

  const openEventForm = (event?: CalendarEvent, date?: Date) => {
    setSelectedEvent(event || null);
    if (date) {
      setSelectedDate(date);
    }
    setShowEventForm(true);
  };

  const getTodayEvents = () => {
    const today = new Date();
    return events.filter(event => {
      const eventDate = new Date(event.start_time);
      return eventDate.toDateString() === today.toDateString();
    });
  };

  const getUpcomingEvents = () => {
    const now = new Date();
    return events
      .filter(event => new Date(event.start_time) > now)
      .sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime())
      .slice(0, 5);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Calendar className="h-6 w-6" />
            Calendar
          </h1>
          <p className="text-gray-600">Manage your appointments and events</p>
        </div>
        
        <div className="flex items-center gap-2">
          <Button onClick={goToToday} variant="outline">
            Today
          </Button>
          <Dialog open={showEventForm} onOpenChange={setShowEventForm}>
            <DialogTrigger asChild>
              <Button onClick={() => openEventForm()}>
                <Plus className="h-4 w-4 mr-2" />
                New Event
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg max-h-[90vh] resize overflow-hidden flex flex-col">
              <DialogHeader className="flex-shrink-0">
                <DialogTitle>
                  {selectedEvent ? 'Edit Event' : 'Create New Event'}
                </DialogTitle>
              </DialogHeader>
              <div className="flex-1 overflow-y-auto pr-2">
                <EventForm
                  event={selectedEvent}
                  defaultDate={selectedDate}
                  onEventCreated={handleEventCreated}
                  onEventUpdated={handleEventUpdated}
                  onEventDeleted={handleEventDeleted}
                  onCancel={() => setShowEventForm(false)}
                />
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Total Events</p>
                  <p className="text-2xl font-bold">{stats.total_events}</p>
                </div>
                <CalendarDays className="h-8 w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Appointments</p>
                  <p className="text-2xl font-bold">{stats.events_by_type.appointment || 0}</p>
                </div>
                <Clock className="h-8 w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Meetings</p>
                  <p className="text-2xl font-bold">{stats.events_by_type.meeting || 0}</p>
                </div>
                <User className="h-8 w-8 text-purple-600" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Services</p>
                  <p className="text-2xl font-bold">{stats.events_by_type.service || 0}</p>
                </div>
                <Building2 className="h-8 w-8 text-orange-600" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Calendar View */}
        <div className="lg:col-span-3">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => navigateMonth('prev')}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <h2 className="text-lg font-semibold">
                      {MONTHS[currentMonth]} {currentYear}
                    </h2>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => navigateMonth('next')}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                
                <Tabs value={view} onValueChange={(v) => setView(v as 'month' | 'week' | 'day')}>
                  <TabsList>
                    <TabsTrigger value="month">Month</TabsTrigger>
                    <TabsTrigger value="week">Week</TabsTrigger>
                    <TabsTrigger value="day">Day</TabsTrigger>
                  </TabsList>
                </Tabs>
              </div>
            </CardHeader>
            <CardContent>
              <CalendarView
                currentDate={currentDate}
                events={events}
                view={view}
                onDateClick={setSelectedDate}
                onEventClick={(event) => openEventForm(event)}
                onCreateEvent={(date) => openEventForm(undefined, date)}
              />
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Today's Events */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Today's Events</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {getTodayEvents().length === 0 ? (
                  <p className="text-gray-500 text-sm">No events today</p>
                ) : (
                  getTodayEvents().map((event) => (
                    <EventCard
                      key={event.id}
                      event={event}
                      compact
                      onClick={() => openEventForm(event)}
                    />
                  ))
                )}
              </div>
            </CardContent>
          </Card>

          {/* Upcoming Events */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Upcoming Events</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {getUpcomingEvents().length === 0 ? (
                  <p className="text-gray-500 text-sm">No upcoming events</p>
                ) : (
                  getUpcomingEvents().map((event) => (
                    <EventCard
                      key={event.id}
                      event={event}
                      compact
                      onClick={() => openEventForm(event)}
                    />
                  ))
                )}
              </div>
            </CardContent>
          </Card>

          {/* Quick Filters */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Filters</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div>
                  <label className="text-sm font-medium">Event Type</label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="All types" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All types</SelectItem>
                      <SelectItem value="appointment">Appointments</SelectItem>
                      <SelectItem value="meeting">Meetings</SelectItem>
                      <SelectItem value="service">Services</SelectItem>
                      <SelectItem value="call">Calls</SelectItem>
                      <SelectItem value="reminder">Reminders</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div>
                  <label className="text-sm font-medium">Status</label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="All statuses" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All statuses</SelectItem>
                      <SelectItem value="confirmed">Confirmed</SelectItem>
                      <SelectItem value="tentative">Tentative</SelectItem>
                      <SelectItem value="cancelled">Cancelled</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}