// src/app/organizations/telephony/active-calls/page.tsx
'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Loader2, 
  Phone,
  PhoneIncoming,
  PhoneOutgoing,
  Radio,
  Mic,
  MicOff,
  Clock,
  Eye,
  RefreshCw,
  AlertCircle
} from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';

import { 
  telephonyService, 
  PhoneCall,
  CallsListResponse 
} from '@/services/telephony';

export default function ActiveCallsPage() {
  const router = useRouter();
  const { token } = useAuth();
  const { toast } = useToast();

  // State
  const [isLoading, setIsLoading] = useState(true);
  const [activeCalls, setActiveCalls] = useState<PhoneCall[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  // Load active calls
  const loadActiveCalls = useCallback(async () => {
    if (!token) return;

    try {
      setError(null);
      
      // Get calls with active statuses
      const activeStatuses = ['incoming', 'ringing', 'answered', 'in_progress'];
      const allActiveCalls: PhoneCall[] = [];
      
      // Fetch calls for each active status
      for (const status of activeStatuses) {
        try {
          const response: CallsListResponse = await telephonyService.getCalls(
            token, 
            1, 
            50, // Get up to 50 active calls per status
            status
          );
          allActiveCalls.push(...response.calls);
        } catch (statusError) {
          console.warn(`Failed to load calls with status ${status}:`, statusError);
        }
      }
      
      // Remove duplicates by call ID
      const uniqueCalls = allActiveCalls.filter((call, index, self) =>
        index === self.findIndex(c => c.id === call.id)
      );
      
      // Sort by created time (newest first)
      uniqueCalls.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      
      setActiveCalls(uniqueCalls);
      setLastRefresh(new Date());
      
    } catch (error: any) {
      console.error('Error loading active calls:', error);
      setError(error.message || 'Failed to load active calls');
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  // Auto-refresh every 5 seconds
  useEffect(() => {
    loadActiveCalls();
    
    const interval = setInterval(() => {
      loadActiveCalls();
    }, 5000);
    
    return () => clearInterval(interval);
  }, [loadActiveCalls]);

  // Manual refresh
  const handleRefresh = () => {
    setIsLoading(true);
    loadActiveCalls();
  };

  // View call details
  const handleViewCall = (callId: string) => {
    router.push(`/organizations/telephony/calls/${callId}`);
  };

  // Format duration
  const formatDuration = (startTime: string): string => {
    const start = new Date(startTime);
    const now = new Date();
    const durationMs = now.getTime() - start.getTime();
    const durationSec = Math.floor(durationMs / 1000);
    
    const minutes = Math.floor(durationSec / 60);
    const seconds = durationSec % 60;
    
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  // Get call urgency
  const getCallUrgency = (call: PhoneCall): 'high' | 'medium' | 'low' => {
    if (call.status === 'incoming' || call.status === 'ringing') {
      return 'high';
    }
    if (call.status === 'answered' || call.status === 'in_progress') {
      // Check if call has been going on for too long
      const startTime = new Date(call.start_time || call.created_at);
      const now = new Date();
      const durationMinutes = (now.getTime() - startTime.getTime()) / (1000 * 60);
      
      if (durationMinutes > 30) return 'high';
      if (durationMinutes > 15) return 'medium';
    }
    return 'low';
  };

  const getUrgencyColor = (urgency: 'high' | 'medium' | 'low'): string => {
    switch (urgency) {
      case 'high': return 'bg-red-100 text-red-800 border-red-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low': return 'bg-green-100 text-green-800 border-green-200';
    }
  };

  if (isLoading && activeCalls.length === 0) {
    return (
      <div className="container mx-auto py-8">
        <div className="flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin" />
          <span className="ml-2">Loading active calls...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 max-w-7xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">Active Calls</h1>
          <p className="text-muted-foreground">
            Monitor and manage live phone calls ({activeCalls.length} active)
          </p>
        </div>
        
        <div className="flex items-center space-x-4">
          <span className="text-sm text-muted-foreground">
            Last updated: {lastRefresh.toLocaleTimeString()}
          </span>
          <Button 
            variant="outline" 
            onClick={handleRefresh}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Active Calls Grid */}
      {activeCalls.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Phone className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No Active Calls</h3>
            <p className="text-muted-foreground text-center">
              All calls are currently completed or there are no incoming calls at the moment.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {activeCalls.map((call) => {
            const urgency = getCallUrgency(call);
            const urgencyColor = getUrgencyColor(urgency);
            
            return (
              <Card key={call.id} className={`${urgencyColor} transition-all hover:shadow-lg`}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg flex items-center">
                      {call.direction === 'inbound' ? (
                        <PhoneIncoming className="h-5 w-5 mr-2 text-green-600" />
                      ) : (
                        <PhoneOutgoing className="h-5 w-5 mr-2 text-blue-600" />
                      )}
                      {telephonyService.formatPhoneNumber(call.customer_phone_number)}
                    </CardTitle>
                    <Badge className={telephonyService.getCallStatusColor(call.status)}>
                      {call.status.replace('_', ' ')}
                    </Badge>
                  </div>
                  <CardDescription>
                    To: {telephonyService.formatPhoneNumber(call.organization_phone_number)}
                  </CardDescription>
                </CardHeader>
                
                <CardContent className="space-y-3">
                  {/* Call Timing */}
                  <div className="flex items-center space-x-4 text-sm">
                    <div className="flex items-center">
                      <Clock className="h-4 w-4 mr-1 text-muted-foreground" />
                      <span>
                        {call.start_time ? formatDuration(call.start_time) : 'Not started'}
                      </span>
                    </div>
                    {call.status === 'in_progress' && (
                      <div className="flex items-center">
                        <Radio className="h-4 w-4 mr-1 text-green-600" />
                        <span className="text-green-600 font-medium">LIVE</span>
                      </div>
                    )}
                  </div>

                  {/* Call Status Details */}
                  <div className="text-sm text-muted-foreground">
                    <div>Started: {new Date(call.created_at).toLocaleTimeString()}</div>
                    {call.answer_time && (
                      <div>Answered: {new Date(call.answer_time).toLocaleTimeString()}</div>
                    )}
                  </div>

                  {/* Action Buttons */}
                  <div className="flex space-x-2 pt-2">
                    <Button
                      size="sm"
                      onClick={() => handleViewCall(call.id)}
                      className="flex-1"
                    >
                      <Eye className="h-4 w-4 mr-2" />
                      View Details
                    </Button>
                    
                    {(call.status === 'answered' || call.status === 'in_progress') && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleViewCall(call.id)}
                        className="border-blue-200 text-blue-700 hover:bg-blue-50"
                      >
                        <Mic className="h-4 w-4 mr-2" />
                        Join Live
                      </Button>
                    )}
                  </div>

                  {/* Urgency Indicator */}
                  {urgency === 'high' && (
                    <div className="text-xs font-medium text-red-700 bg-red-50 px-2 py-1 rounded">
                      ⚠️ Requires immediate attention
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Stats Summary */}
      <div className="mt-8 grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">
              {activeCalls.filter(c => c.status === 'incoming' || c.status === 'ringing').length}
            </div>
            <div className="text-sm text-muted-foreground">Incoming Calls</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">
              {activeCalls.filter(c => c.status === 'answered' || c.status === 'in_progress').length}
            </div>
            <div className="text-sm text-muted-foreground">Active Calls</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">
              {activeCalls.filter(c => getCallUrgency(c) === 'high').length}
            </div>
            <div className="text-sm text-muted-foreground">High Priority</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">
              {activeCalls.length}
            </div>
            <div className="text-sm text-muted-foreground">Total Active</div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}