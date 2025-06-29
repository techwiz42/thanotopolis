// frontend/src/app/organizations/telephony/calls/[id]/page.tsx
'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Loader2, 
  ArrowLeft,
  Play,
  Pause,
  Download,
  Phone,
  Clock,
  DollarSign,
  Calendar,
  User,
  FileText,
  PhoneIncoming,
  PhoneOutgoing,
  MapPin,
  Volume2,
  AlertCircle,
  Mic,
  MicOff,
  MessageSquare,
  Send,
  Radio
} from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';

import { 
  telephonyService, 
  PhoneCall as TelephonyPhoneCall,
  CallMessage 
} from '@/services/telephony';
import { useCallMessages } from '../hooks/useCallMessages';
import { CallMessagesList } from '../components/CallMessagesList';
import { useActiveCall } from '@/hooks/useActiveCall';

interface CallDetailsPageProps {
  params: {
    id: string;
  };
}

export default function CallDetailsPage({ params }: CallDetailsPageProps) {
  const router = useRouter();
  const { token } = useAuth();
  const { toast } = useToast();

  console.log('CallDetailsPage mounted with params:', params);
  console.log('Token available:', !!token);

  // State
  const [isLoading, setIsLoading] = useState(true);
  const [call, setCall] = useState<TelephonyPhoneCall | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPlayingRecording, setIsPlayingRecording] = useState(false);
  const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(null);
  const [agentMessage, setAgentMessage] = useState('');
  const [showLiveControls, setShowLiveControls] = useState(false);
  const [showFullTranscript, setShowFullTranscript] = useState(false);
  const [showMetadata, setShowMetadata] = useState(false);
  
  // Call messages hook
  const {
    messages,
    isLoading: messagesLoading,
    getSummary,
    deleteMessage,
    loadMessages
  } = useCallMessages({ 
    callId: params.id,
    autoLoad: false // We'll load manually after call is loaded
  });

  // Active call hook for real-time functionality
  const activeCall = useActiveCall(params.id, {
    autoStartStreaming: true,
    onNewMessage: (message) => {
      console.log('📞 New live message:', message);
      toast({
        title: "New Message",
        description: `${message.sender.name}: ${message.content.substring(0, 50)}...`,
        duration: 3000,
      });
    },
    onCallStatusChange: (status, updatedCall) => {
      console.log('📞 Call status changed:', status);
      setCall(updatedCall);
      
      if (status === 'answered' || status === 'in_progress') {
        setShowLiveControls(true);
      } else if (status === 'completed' || status === 'failed') {
        setShowLiveControls(false);
      }
    }
  });

  // Load call data
  useEffect(() => {
    const loadCall = async () => {
      if (!token || !params.id) return;

      try {
        setIsLoading(true);
        setError(null);
        
        // Load call data first, then messages
        const callData = await telephonyService.getCall(params.id, token);
        setCall(callData);
        
        // Check if this is an active call
        if (callData.status === 'answered' || callData.status === 'in_progress') {
          setShowLiveControls(true);
        }
        
        // Load messages manually
        try {
          await loadMessages();
        } catch (msgError) {
          console.warn('Failed to load messages:', msgError);
          // Don't fail the entire call loading if messages fail
        }
        
      } catch (error: any) {
        console.error('Error loading call:', error);
        setError(error.message || 'Failed to load call details');
        toast({
          title: "Error Loading Call",
          description: error.message || "Failed to load call details. Please try again.",
          variant: "destructive"
        });
      } finally {
        setIsLoading(false);
      }
    };

    loadCall();
  }, [token, params.id]);

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (audioElement) {
        audioElement.pause();
        audioElement.src = '';
      }
    };
  }, [audioElement]);

  // Handle audio playback
  const handlePlayRecording = () => {
    if (!call?.recording_url) return;

    if (isPlayingRecording && audioElement) {
      audioElement.pause();
      setIsPlayingRecording(false);
    } else {
      const audio = new Audio(call.recording_url);
      setAudioElement(audio);
      
      audio.onplay = () => setIsPlayingRecording(true);
      audio.onpause = () => setIsPlayingRecording(false);
      audio.onended = () => setIsPlayingRecording(false);
      audio.onerror = () => {
        setIsPlayingRecording(false);
        toast({
          title: "Playback Error",
          description: "Failed to play recording. Please try again.",
          variant: "destructive"
        });
      };
      
      audio.play().catch(error => {
        console.error('Error playing audio:', error);
        toast({
          title: "Playback Error",
          description: "Failed to play recording. Please try again.",
          variant: "destructive"
        });
      });
    }
  };

  // Download recording
  const handleDownloadRecording = () => {
    if (!call?.recording_url) return;
    
    const link = document.createElement('a');
    link.href = call.recording_url;
    link.download = `call-${call.call_sid}-recording.mp3`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Send agent response
  const handleSendAgentMessage = async () => {
    if (!agentMessage.trim()) return;

    try {
      await activeCall.sendAgentResponse(agentMessage.trim());
      setAgentMessage('');
      
      toast({
        title: "Message Sent",
        description: "Agent response sent to caller",
      });
    } catch (error: any) {
      console.error('Error sending agent message:', error);
      toast({
        title: "Error",
        description: error.message || "Failed to send message",
        variant: "destructive"
      });
    }
  };

  // Handle keyboard shortcuts
  const handleAgentMessageKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSendAgentMessage();
    }
  };

  // Format date/time
  const formatDateTime = (dateString: string): string => {
    return new Date(dateString).toLocaleString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  if (isLoading) {
    return (
      <div className="container mx-auto py-8">
        <div className="flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin" />
          <span className="ml-2">Loading call details...</span>
        </div>
      </div>
    );
  }

  if (error || !call) {
    return (
      <div className="container mx-auto py-8">
        <div className="flex items-center mb-6">
          <Button
            variant="ghost"
            onClick={() => router.back()}
            className="mr-4"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <h1 className="text-3xl font-bold">Call Details</h1>
        </div>
        
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {error || 'Call not found'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center">
          <Button
            variant="ghost"
            onClick={() => router.back()}
            className="mr-4"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-3xl font-bold">Call Details</h1>
            <p className="text-muted-foreground">
              Call {call.call_sid}
            </p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <Badge className={telephonyService.getCallStatusColor(call.status)}>
            {call.status.replace('_', ' ')}
          </Badge>
          {call.direction === 'inbound' ? (
            <PhoneIncoming className="h-5 w-5 text-green-600" />
          ) : (
            <PhoneOutgoing className="h-5 w-5 text-blue-600" />
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Call Information */}
        <div className="lg:col-span-2 space-y-6">
          {/* Call Overview */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Phone className="h-5 w-5 mr-2" />
                Call Overview
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Customer Phone</label>
                  <p className="text-lg font-medium">
                    {telephonyService.formatPhoneNumber(call.customer_phone_number)}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Organization Phone</label>
                  <p className="text-lg font-medium">
                    {telephonyService.formatPhoneNumber(call.organization_phone_number)}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Direction</label>
                  <div className="flex items-center">
                    {call.direction === 'inbound' ? (
                      <PhoneIncoming className="h-4 w-4 text-green-600 mr-2" />
                    ) : (
                      <PhoneOutgoing className="h-4 w-4 text-blue-600 mr-2" />
                    )}
                    <span className="capitalize">{call.direction}</span>
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Status</label>
                  <div>
                    <Badge className={telephonyService.getCallStatusColor(call.status)}>
                      {call.status.replace('_', ' ')}
                    </Badge>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Live Call Controls */}
          {showLiveControls && (
            <Card className="border-blue-200 bg-blue-50">
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Radio className="h-5 w-5 mr-2 text-blue-600" />
                  Live Call Controls
                  <Badge className="ml-2 bg-green-100 text-green-800">
                    {activeCall.isStreamActive ? 'LIVE' : 'CONNECTING...'}
                  </Badge>
                </CardTitle>
                <CardDescription>
                  Real-time call monitoring and agent response
                  {activeCall.currentLanguage && (
                    <span className="ml-2 text-sm font-medium">
                      Language: {activeCall.currentLanguage.toUpperCase()}
                    </span>
                  )}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Stream Status */}
                <div className="flex items-center space-x-4 p-3 bg-white rounded-lg border">
                  <div className="flex items-center space-x-2">
                    {activeCall.telephonyConnected ? (
                      <Mic className="h-4 w-4 text-green-600" />
                    ) : (
                      <MicOff className="h-4 w-4 text-red-600" />
                    )}
                    <span className="text-sm font-medium">
                      Audio Stream: {activeCall.telephonyConnected ? 'Connected' : 'Disconnected'}
                    </span>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <MessageSquare className="h-4 w-4 text-blue-600" />
                    <span className="text-sm font-medium">
                      Messages: {activeCall.messages.length}
                    </span>
                  </div>
                </div>

                {/* Agent Response Input */}
                <div className="p-4 bg-white rounded-lg border">
                  <label className="block text-sm font-medium mb-2">
                    Send Agent Response (TTS will be played to caller)
                  </label>
                  <div className="flex space-x-2">
                    <textarea
                      value={agentMessage}
                      onChange={(e) => setAgentMessage(e.target.value)}
                      onKeyDown={handleAgentMessageKeyDown}
                      placeholder="Type your response here... (Ctrl+Enter to send)"
                      className="flex-1 min-h-[80px] px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                      disabled={!activeCall.telephonyConnected}
                    />
                    <Button
                      onClick={handleSendAgentMessage}
                      disabled={!agentMessage.trim() || !activeCall.telephonyConnected}
                      size="sm"
                      className="self-end"
                    >
                      <Send className="h-4 w-4 mr-1" />
                      Send
                    </Button>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Message will be converted to speech and played to the caller in real-time
                  </p>
                </div>

                {/* Stream Controls */}
                <div className="flex space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={activeCall.startStream}
                    disabled={activeCall.telephonyConnected}
                  >
                    <Radio className="h-4 w-4 mr-2" />
                    Start Stream
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={activeCall.stopStream}
                    disabled={!activeCall.telephonyConnected}
                  >
                    <MicOff className="h-4 w-4 mr-2" />
                    Stop Stream
                  </Button>
                </div>

                {/* Error Display */}
                {activeCall.error && (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      {activeCall.error}
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>
          )}

          {/* Call Summary */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <FileText className="h-5 w-5 mr-2" />
                Call Summary
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="bg-muted p-4 rounded-lg">
                {call.summary ? (
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">
                    {call.summary}
                  </p>
                ) : call.status === 'completed' ? (
                  <p className="text-sm text-muted-foreground italic">
                    Summary is being generated for this completed call...
                  </p>
                ) : (
                  <p className="text-sm text-muted-foreground italic">
                    Summary will be available after the call is completed.
                  </p>
                )}
              </div>
              
              {/* Show Full Transcript Button */}
              {messages.length > 0 && (
                <div className="mt-4 text-center">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowFullTranscript(!showFullTranscript)}
                  >
                    {showFullTranscript ? 'Hide' : 'Show'} Full Transcript
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Full Transcript */}
          {showFullTranscript && messages.length > 0 && (
            <CallMessagesList 
              messages={messages}
              onDeleteMessage={deleteMessage}
              showActions={true}
              showTabs={true}
            />
          )}

          {/* Call Timeline */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Clock className="h-5 w-5 mr-2" />
                Call Timeline
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                <div className="flex items-center justify-between border-l-2 border-blue-200 pl-4">
                  <div>
                    <p className="font-medium">Call Created</p>
                    <p className="text-sm text-muted-foreground">
                      {formatDateTime(call.created_at)}
                    </p>
                  </div>
                </div>
                
                {call.start_time && (
                  <div className="flex items-center justify-between border-l-2 border-yellow-200 pl-4">
                    <div>
                      <p className="font-medium">Call Started</p>
                      <p className="text-sm text-muted-foreground">
                        {formatDateTime(call.start_time)}
                      </p>
                    </div>
                  </div>
                )}
                
                {call.answer_time && (
                  <div className="flex items-center justify-between border-l-2 border-green-200 pl-4">
                    <div>
                      <p className="font-medium">Call Answered</p>
                      <p className="text-sm text-muted-foreground">
                        {formatDateTime(call.answer_time)}
                      </p>
                    </div>
                  </div>
                )}
                
                {call.end_time && (
                  <div className="flex items-center justify-between border-l-2 border-red-200 pl-4">
                    <div>
                      <p className="font-medium">Call Ended</p>
                      <p className="text-sm text-muted-foreground">
                        {formatDateTime(call.end_time)}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Call Recording */}
          {call.recording_url && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Volume2 className="h-5 w-5 mr-2" />
                  Call Recording
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={handlePlayRecording}
                      disabled={!call.recording_url}
                    >
                      {isPlayingRecording ? (
                        <Pause className="h-4 w-4 mr-2" />
                      ) : (
                        <Play className="h-4 w-4 mr-2" />
                      )}
                      {isPlayingRecording ? 'Pause' : 'Play'}
                    </Button>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={handleDownloadRecording}
                    >
                      <Download className="h-4 w-4 mr-2" />
                      Download
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Call Metrics */}
          <Card>
            <CardHeader>
              <CardTitle>Call Metrics</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Clock className="h-4 w-4 mr-2 text-muted-foreground" />
                    <span className="text-sm">Duration</span>
                  </div>
                  <span className="font-medium">
                    {call.duration_seconds 
                      ? telephonyService.formatCallDuration(call.duration_seconds)
                      : 'N/A'
                    }
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Calendar className="h-4 w-4 mr-2 text-muted-foreground" />
                    <span className="text-sm">Date</span>
                  </div>
                  <span className="font-medium text-sm">
                    {new Date(call.created_at).toLocaleDateString()}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Clock className="h-4 w-4 mr-2 text-muted-foreground" />
                    <span className="text-sm">Time</span>
                  </div>
                  <span className="font-medium text-sm">
                    {new Date(call.created_at).toLocaleTimeString('en-US', {
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit'
                    })}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Call Metadata */}
          {call.call_metadata && Object.keys(call.call_metadata).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>Additional Information</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowMetadata(!showMetadata)}
                  >
                    {showMetadata ? 'Hide' : 'Show'}
                  </Button>
                </CardTitle>
              </CardHeader>
              {showMetadata && (
                <CardContent>
                  <div className="space-y-3">
                    {Object.entries(call.call_metadata).map(([key, value]) => {
                      const formattedKey = key
                        .split('_')
                        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                        .join(' ');
                      
                      let formattedValue: React.ReactNode = value;
                      
                      if (typeof value === 'object' && value !== null) {
                        formattedValue = (
                          <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                            {JSON.stringify(value, null, 2)}
                          </pre>
                        );
                      } else if (typeof value === 'boolean') {
                        formattedValue = (
                          <Badge variant={value ? 'default' : 'secondary'}>
                            {value ? 'Yes' : 'No'}
                          </Badge>
                        );
                      } else if (typeof value === 'number') {
                        formattedValue = (
                          <span className="font-mono">
                            {value.toLocaleString()}
                          </span>
                        );
                      } else if (value === null || value === undefined) {
                        formattedValue = (
                          <span className="text-muted-foreground italic">N/A</span>
                        );
                      }
                      
                      return (
                        <div key={key} className="border-b pb-2 last:border-0">
                          <div className="text-sm font-medium text-muted-foreground mb-1">
                            {formattedKey}
                          </div>
                          <div className="text-sm">
                            {formattedValue}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              )}
            </Card>
          )}

          {/* Technical Details */}
          <Card>
            <CardHeader>
              <CardTitle>Technical Details</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Call SID:</span>
                  <span className="text-xs font-mono">{call.call_sid}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Call ID:</span>
                  <span className="text-xs font-mono">{call.id}</span>
                </div>
                {call.platform_phone_number && (
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Platform:</span>
                    <span className="text-sm">
                      {telephonyService.formatPhoneNumber(call.platform_phone_number)}
                    </span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}