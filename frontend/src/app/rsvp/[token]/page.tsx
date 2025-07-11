'use client';

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { 
  Calendar, 
  Clock, 
  MapPin, 
  User, 
  CheckCircle, 
  XCircle, 
  Clock as ClockIcon,
  Mail,
  AlertCircle,
  Download,
  ExternalLink
} from 'lucide-react';
import { calendarService, CalendarEventAttendee } from '@/services/calendar';

interface RSVPPageData {
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
}

export default function RSVPPage() {
  const params = useParams();
  const token = params.token as string;
  
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [data, setData] = useState<RSVPPageData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<'accepted' | 'declined' | 'tentative' | null>(null);
  const [attendeeName, setAttendeeName] = useState('');
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    loadRSVPData();
  }, [token]);

  const loadRSVPData = async () => {
    try {
      setLoading(true);
      const rsvpData = await calendarService.getRSVPDetails(token);
      setData(rsvpData);
      setAttendeeName(rsvpData.attendee.attendee_name || '');
      
      // Set current response if already responded
      if (rsvpData.attendee.response_status !== 'no_response') {
        setResponse(rsvpData.attendee.response_status as any);
        setSubmitted(true);
      }
    } catch (error) {
      console.error('Failed to load RSVP data:', error);
      setError('Invalid or expired invitation link');
    } finally {
      setLoading(false);
    }
  };

  const handleRSVPSubmit = async () => {
    if (!response || !data) return;

    try {
      setSubmitting(true);
      
      await calendarService.respondToRSVP(token, {
        response_status: response,
        attendee_name: attendeeName || undefined
      });
      
      setSubmitted(true);
      
      // Reload data to get updated information
      await loadRSVPData();
    } catch (error) {
      console.error('Failed to submit RSVP:', error);
      setError('Failed to submit response. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const formatEventDate = (startTime: string, endTime: string, allDay: boolean) => {
    const start = new Date(startTime);
    const end = new Date(endTime);
    
    if (allDay) {
      if (start.toDateString() === end.toDateString()) {
        return start.toLocaleDateString('en-US', { 
          weekday: 'long', 
          year: 'numeric', 
          month: 'long', 
          day: 'numeric' 
        });
      } else {
        return `${start.toLocaleDateString('en-US', { 
          weekday: 'long', 
          month: 'short', 
          day: 'numeric' 
        })} - ${end.toLocaleDateString('en-US', { 
          weekday: 'long', 
          month: 'short', 
          day: 'numeric', 
          year: 'numeric' 
        })}`;
      }
    } else {
      return start.toLocaleDateString('en-US', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      });
    }
  };

  const formatEventTime = (startTime: string, endTime: string, allDay: boolean) => {
    if (allDay) return 'All day';
    
    const start = new Date(startTime);
    const end = new Date(endTime);
    
    return `${start.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    })} - ${end.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    })}`;
  };

  const getResponseBadge = (responseStatus: string) => {
    const configs = {
      'accepted': { 
        icon: CheckCircle, 
        color: 'bg-green-100 text-green-800', 
        text: 'Attending' 
      },
      'declined': { 
        icon: XCircle, 
        color: 'bg-red-100 text-red-800', 
        text: 'Not Attending' 
      },
      'tentative': { 
        icon: ClockIcon, 
        color: 'bg-yellow-100 text-yellow-800', 
        text: 'Maybe' 
      },
    };

    const config = configs[responseStatus as keyof typeof configs];
    if (!config) return null;

    const Icon = config.icon;

    return (
      <Badge className={`${config.color} flex items-center gap-1`}>
        <Icon className="h-3 w-3" />
        {config.text}
      </Badge>
    );
  };

  const getCalendarUrls = () => {
    if (!data) return { google: '', outlook: '', ics: '' };

    const event = data.event;
    const title = encodeURIComponent(event.title);
    const description = encodeURIComponent(event.description || '');
    const location = encodeURIComponent(event.location || '');
    
    const start = new Date(event.start_time);
    const end = new Date(event.end_time);
    const startTime = start.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';
    const endTime = end.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';

    return {
      google: `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${title}&dates=${startTime}/${endTime}&details=${description}&location=${location}`,
      outlook: `https://outlook.live.com/calendar/0/deeplink/compose?subject=${title}&startdt=${startTime}&enddt=${endTime}&body=${description}&location=${location}`,
      ics: calendarService.downloadEventICS(event.id)
    };
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading invitation...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6">
            <div className="text-center">
              <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Invalid Invitation</h3>
              <p className="text-gray-600">{error}</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6">
            <div className="text-center">
              <AlertCircle className="h-12 w-12 text-gray-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Invitation Not Found</h3>
              <p className="text-gray-600">This invitation could not be found or has expired.</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const calendarUrls = getCalendarUrls();

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-2xl mx-auto px-4">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Meeting Invitation</h1>
          <p className="text-gray-600">Please respond to let us know if you'll be attending</p>
        </div>

        {/* Event Details Card */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              {data.event.title}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {data.event.description && (
              <p className="text-gray-700">{data.event.description}</p>
            )}
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-gray-500" />
                <span className="text-sm">
                  {formatEventDate(data.event.start_time, data.event.end_time, data.event.all_day)}
                </span>
              </div>
              
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-gray-500" />
                <span className="text-sm">
                  {formatEventTime(data.event.start_time, data.event.end_time, data.event.all_day)}
                </span>
              </div>

              {data.event.location && (
                <div className="flex items-center gap-2 md:col-span-2">
                  <MapPin className="h-4 w-4 text-gray-500" />
                  <span className="text-sm">{data.event.location}</span>
                </div>
              )}
            </div>

            {/* Attendee Info */}
            <Separator />
            <div className="flex items-center gap-2">
              <User className="h-4 w-4 text-gray-500" />
              <span className="text-sm">
                Invited: {data.attendee.attendee_name || data.attendee.attendee_email}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* RSVP Response Card */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Your Response</CardTitle>
            {submitted && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600">Current status:</span>
                {getResponseBadge(data.attendee.response_status)}
              </div>
            )}
          </CardHeader>
          <CardContent className="space-y-4">
            {data.attendee.attendee_type === 'external' && (
              <div>
                <Label htmlFor="attendeeName">Your Name</Label>
                <Input
                  id="attendeeName"
                  value={attendeeName}
                  onChange={(e) => setAttendeeName(e.target.value)}
                  placeholder="Enter your name"
                  disabled={submitting}
                />
              </div>
            )}

            <div>
              <Label>Will you be attending?</Label>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mt-2">
                <Button
                  variant={response === 'accepted' ? 'default' : 'outline'}
                  className={response === 'accepted' ? 'bg-green-600 hover:bg-green-700' : ''}
                  onClick={() => setResponse('accepted')}
                  disabled={submitting}
                >
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Yes, I'll attend
                </Button>
                
                <Button
                  variant={response === 'declined' ? 'default' : 'outline'}
                  className={response === 'declined' ? 'bg-red-600 hover:bg-red-700' : ''}
                  onClick={() => setResponse('declined')}
                  disabled={submitting}
                >
                  <XCircle className="h-4 w-4 mr-2" />
                  No, I can't attend
                </Button>
                
                <Button
                  variant={response === 'tentative' ? 'default' : 'outline'}
                  className={response === 'tentative' ? 'bg-yellow-600 hover:bg-yellow-700' : ''}
                  onClick={() => setResponse('tentative')}
                  disabled={submitting}
                >
                  <ClockIcon className="h-4 w-4 mr-2" />
                  Maybe
                </Button>
              </div>
            </div>

            <Button
              onClick={handleRSVPSubmit}
              disabled={!response || submitting}
              className="w-full"
            >
              {submitting ? 'Submitting...' : submitted ? 'Update Response' : 'Submit Response'}
            </Button>

            {submitted && response === 'accepted' && (
              <div className="mt-4 p-4 bg-green-50 rounded-lg">
                <h4 className="font-medium text-green-800 mb-2">Great! We're looking forward to seeing you.</h4>
                <p className="text-sm text-green-700 mb-3">Add this event to your calendar:</p>
                <div className="flex flex-wrap gap-2">
                  <a
                    href={calendarUrls.google}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                  >
                    <Calendar className="h-3 w-3 mr-1" />
                    Google Calendar
                    <ExternalLink className="h-3 w-3 ml-1" />
                  </a>
                  <a
                    href={calendarUrls.outlook}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                  >
                    <Calendar className="h-3 w-3 mr-1" />
                    Outlook
                    <ExternalLink className="h-3 w-3 ml-1" />
                  </a>
                  <a
                    href={calendarUrls.ics}
                    download
                    className="inline-flex items-center px-3 py-1 bg-gray-600 text-white text-sm rounded hover:bg-gray-700"
                  >
                    <Download className="h-3 w-3 mr-1" />
                    Download .ics
                  </a>
                </div>
              </div>
            )}

            {submitted && response === 'declined' && (
              <div className="mt-4 p-4 bg-red-50 rounded-lg">
                <h4 className="font-medium text-red-800">Thanks for letting us know.</h4>
                <p className="text-sm text-red-700">You'll be missed! If your plans change, you can update your response above.</p>
              </div>
            )}

            {submitted && response === 'tentative' && (
              <div className="mt-4 p-4 bg-yellow-50 rounded-lg">
                <h4 className="font-medium text-yellow-800">Thanks for responding.</h4>
                <p className="text-sm text-yellow-700">Please let us know when you can confirm your attendance.</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Footer */}
        <div className="text-center text-sm text-gray-500">
          <p>If you have questions about this event, please contact the organizer.</p>
          <p className="mt-1">This invitation was sent by Thanotopolis</p>
        </div>
      </div>
    </div>
  );
}