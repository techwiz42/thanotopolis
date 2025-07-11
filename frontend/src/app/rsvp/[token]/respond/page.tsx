'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { 
  CheckCircle, 
  XCircle, 
  Clock,
  Calendar,
  AlertCircle,
  ArrowLeft
} from 'lucide-react';
import { calendarService } from '@/services/calendar';

export default function QuickRSVPPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  
  const token = params.token as string;
  const status = searchParams.get('status') as 'accepted' | 'declined' | 'tentative';
  
  const [loading, setLoading] = useState(false);
  const [attendeeName, setAttendeeName] = useState('');
  const [completed, setCompleted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [eventTitle, setEventTitle] = useState('');

  useEffect(() => {
    if (status && ['accepted', 'declined', 'tentative'].includes(status)) {
      loadEventInfo();
    } else {
      setError('Invalid response status');
    }
  }, [token, status]);

  const loadEventInfo = async () => {
    try {
      const rsvpData = await calendarService.getRSVPDetails(token);
      setEventTitle(rsvpData.event.title);
      setAttendeeName(rsvpData.attendee.attendee_name || '');
    } catch (error) {
      console.error('Failed to load event info:', error);
      setError('Invalid or expired invitation link');
    }
  };

  const handleQuickResponse = async () => {
    if (!status) return;

    try {
      setLoading(true);
      
      await calendarService.respondToRSVP(token, {
        response_status: status,
        attendee_name: attendeeName || undefined
      });
      
      setCompleted(true);
    } catch (error) {
      console.error('Failed to submit RSVP:', error);
      setError('Failed to submit response. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getStatusInfo = () => {
    const configs = {
      'accepted': {
        icon: CheckCircle,
        color: 'text-green-600',
        bgColor: 'bg-green-50',
        borderColor: 'border-green-200',
        title: 'Confirm Your Attendance',
        message: 'Great! You\'re accepting this invitation.',
        completedTitle: 'You\'re Attending!',
        completedMessage: 'Thanks for confirming. We\'re looking forward to seeing you!'
      },
      'declined': {
        icon: XCircle,
        color: 'text-red-600',
        bgColor: 'bg-red-50',
        borderColor: 'border-red-200',
        title: 'Decline Invitation',
        message: 'You\'re declining this invitation.',
        completedTitle: 'Response Recorded',
        completedMessage: 'Thanks for letting us know. You\'ll be missed!'
      },
      'tentative': {
        icon: Clock,
        color: 'text-yellow-600',
        bgColor: 'bg-yellow-50',
        borderColor: 'border-yellow-200',
        title: 'Maybe Attending',
        message: 'You\'re marking your attendance as tentative.',
        completedTitle: 'Response Recorded',
        completedMessage: 'Thanks for responding. Please let us know when you can confirm!'
      }
    };

    return configs[status] || configs['tentative'];
  };

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6">
            <div className="text-center">
              <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Error</h3>
              <p className="text-gray-600 mb-4">{error}</p>
              <Button 
                variant="outline" 
                onClick={() => router.push(`/rsvp/${token}`)}
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Go to Full RSVP Page
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const statusInfo = getStatusInfo();
  const Icon = statusInfo.icon;

  if (completed) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Card className={`w-full max-w-md ${statusInfo.bgColor} ${statusInfo.borderColor} border-2`}>
          <CardContent className="pt-6">
            <div className="text-center">
              <Icon className={`h-16 w-16 ${statusInfo.color} mx-auto mb-4`} />
              <h2 className={`text-xl font-bold ${statusInfo.color} mb-2`}>
                {statusInfo.completedTitle}
              </h2>
              <p className="text-gray-700 mb-4">{statusInfo.completedMessage}</p>
              {eventTitle && (
                <p className="text-sm text-gray-600 mb-6">
                  Event: <span className="font-medium">{eventTitle}</span>
                </p>
              )}
              <div className="space-y-2">
                <Button 
                  variant="outline" 
                  onClick={() => router.push(`/rsvp/${token}`)}
                  className="w-full"
                >
                  View Event Details
                </Button>
                {status === 'accepted' && (
                  <p className="text-xs text-gray-500">
                    Add this event to your calendar from the event details page
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <Card className={`w-full max-w-md ${statusInfo.bgColor} ${statusInfo.borderColor} border-2`}>
        <CardHeader className="text-center">
          <Icon className={`h-12 w-12 ${statusInfo.color} mx-auto mb-2`} />
          <CardTitle className={statusInfo.color}>
            {statusInfo.title}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-center text-gray-700">{statusInfo.message}</p>
          
          {eventTitle && (
            <div className="text-center">
              <p className="text-sm text-gray-600">
                Event: <span className="font-medium">{eventTitle}</span>
              </p>
            </div>
          )}

          <div>
            <Label htmlFor="attendeeName">Your Name (optional)</Label>
            <Input
              id="attendeeName"
              value={attendeeName}
              onChange={(e) => setAttendeeName(e.target.value)}
              placeholder="Enter your name"
              disabled={loading}
            />
            <p className="text-xs text-gray-500 mt-1">
              This helps us know who responded
            </p>
          </div>

          <div className="space-y-2">
            <Button
              onClick={handleQuickResponse}
              disabled={loading}
              className="w-full"
            >
              {loading ? 'Submitting...' : `Confirm: ${status.replace('_', ' ')}`}
            </Button>
            
            <Button 
              variant="outline" 
              onClick={() => router.push(`/rsvp/${token}`)}
              className="w-full"
              disabled={loading}
            >
              <Calendar className="h-4 w-4 mr-2" />
              View Full Event Details
            </Button>
          </div>

          <div className="text-center">
            <p className="text-xs text-gray-500">
              You can change your response later if needed
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}