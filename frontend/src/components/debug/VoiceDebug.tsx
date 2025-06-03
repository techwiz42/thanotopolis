// src/components/debug/VoiceDebug.tsx
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useVoice } from '@/contexts/VoiceContext';
import { useAuth } from '@/contexts/AuthContext';
import { VoiceInput } from '@/components/voice/VoiceInput';
import { Mic, MicOff, AlertCircle, CheckCircle, XCircle } from 'lucide-react';

export const VoiceDebug: React.FC = () => {
  const [transcriptionLog, setTranscriptionLog] = useState<Array<{
    text: string;
    isFinal: boolean;
    timestamp: Date;
  }>>([]);
  const [statusLog, setStatusLog] = useState<Array<{
    status: string;
    timestamp: Date;
  }>>([]);
  const [permissionStatus, setPermissionStatus] = useState<'unknown' | 'granted' | 'denied'>('unknown');
  
  const { inputEnabled, setInputEnabled } = useVoice();
  const { token } = useAuth();

  const handleTranscription = (text: string, isFinal: boolean) => {
    console.log('VoiceDebug - Transcription:', { text, isFinal });
    setTranscriptionLog(prev => [...prev, {
      text,
      isFinal,
      timestamp: new Date()
    }].slice(-10)); // Keep last 10 entries
  };

  const handleStatusChange = (status: 'idle' | 'connecting' | 'recording' | 'error') => {
    console.log('VoiceDebug - Status change:', status);
    setStatusLog(prev => [...prev, {
      status,
      timestamp: new Date()
    }].slice(-10)); // Keep last 10 entries
  };

  const checkMicrophonePermission = async () => {
    try {
      const result = await navigator.permissions.query({ name: 'microphone' as PermissionName });
      setPermissionStatus(result.state as 'granted' | 'denied');
      console.log('Microphone permission:', result.state);
    } catch (error) {
      console.error('Error checking microphone permission:', error);
      // Fallback: try to access microphone
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach(track => track.stop());
        setPermissionStatus('granted');
      } catch (micError) {
        setPermissionStatus('denied');
      }
    }
  };

  const testWebSocketConnection = async () => {
    if (!token) {
      console.error('No authentication token available');
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws/voice/streaming-stt?token=${token}`;
    
    console.log('Testing WebSocket connection to:', wsUrl);
    
    try {
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('✓ WebSocket connection successful');
        ws.close();
      };
      
      ws.onerror = (error) => {
        console.error('✗ WebSocket connection failed:', error);
      };
      
      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
      };
    } catch (error) {
      console.error('✗ WebSocket creation failed:', error);
    }
  };

  const clearLogs = () => {
    setTranscriptionLog([]);
    setStatusLog([]);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'recording': return <Mic className="w-4 h-4 text-green-500" />;
      case 'connecting': return <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />;
      case 'error': return <XCircle className="w-4 h-4 text-red-500" />;
      default: return <MicOff className="w-4 h-4 text-gray-500" />;
    }
  };

  const getPermissionIcon = () => {
    switch (permissionStatus) {
      case 'granted': return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'denied': return <XCircle className="w-5 h-5 text-red-500" />;
      default: return <AlertCircle className="w-5 h-5 text-yellow-500" />;
    }
  };

  return (
    <div className="space-y-4 p-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mic className="w-5 h-5" />
            Voice Input Debug Console
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* System Status */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <h4 className="font-medium">System Status</h4>
              <div className="space-y-1 text-sm">
                <div className="flex items-center gap-2">
                  <Badge variant={inputEnabled ? "default" : "secondary"}>
                    Voice Input: {inputEnabled ? "Enabled" : "Disabled"}
                  </Badge>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={token ? "default" : "destructive"}>
                    Auth Token: {token ? "Available" : "Missing"}
                  </Badge>
                </div>
                <div className="flex items-center gap-2">
                  {getPermissionIcon()}
                  <span>Microphone: {permissionStatus}</span>
                </div>
              </div>
            </div>
            
            <div className="space-y-2">
              <h4 className="font-medium">Quick Tests</h4>
              <div className="space-y-2">
                <Button 
                  onClick={() => setInputEnabled(!inputEnabled)}
                  size="sm"
                  variant="outline"
                >
                  {inputEnabled ? "Disable" : "Enable"} Voice Input
                </Button>
                <Button 
                  onClick={checkMicrophonePermission}
                  size="sm"
                  variant="outline"
                >
                  Check Mic Permission
                </Button>
                <Button 
                  onClick={testWebSocketConnection}
                  size="sm"
                  variant="outline"
                >
                  Test WebSocket
                </Button>
              </div>
            </div>
          </div>

          {/* Voice Input Component */}
          <div className="border rounded-lg p-4">
            <h4 className="font-medium mb-2">Live Voice Input Test</h4>
            <div className="flex items-center gap-4">
              <VoiceInput
                onTranscription={handleTranscription}
                onStatusChange={handleStatusChange}
                disabled={!inputEnabled}
              />
              <span className="text-sm text-gray-600">
                Click the microphone to test voice input
              </span>
            </div>
          </div>

          {/* Status Log */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium">Status Log</h4>
                <Button onClick={clearLogs} size="sm" variant="outline">Clear</Button>
              </div>
              <div className="border rounded-lg p-2 h-32 overflow-y-auto text-xs space-y-1">
                {statusLog.length === 0 ? (
                  <div className="text-gray-500">No status updates yet</div>
                ) : (
                  statusLog.map((entry, index) => (
                    <div key={index} className="flex items-center gap-2">
                      {getStatusIcon(entry.status)}
                      <span>{entry.status}</span>
                      <span className="text-gray-500 ml-auto">
                        {entry.timestamp.toLocaleTimeString()}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div>
              <h4 className="font-medium mb-2">Transcription Log</h4>
              <div className="border rounded-lg p-2 h-32 overflow-y-auto text-xs space-y-1">
                {transcriptionLog.length === 0 ? (
                  <div className="text-gray-500">No transcriptions yet</div>
                ) : (
                  transcriptionLog.map((entry, index) => (
                    <div key={index} className="border-b border-gray-100 pb-1">
                      <div className="flex items-center gap-2">
                        <Badge variant={entry.isFinal ? "default" : "secondary"}>
                          {entry.isFinal ? "Final" : "Interim"}
                        </Badge>
                        <span className="text-gray-500">
                          {entry.timestamp.toLocaleTimeString()}
                        </span>
                      </div>
                      <div className="mt-1">"{entry.text}"</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Browser Information */}
          <div>
            <h4 className="font-medium mb-2">Browser Information</h4>
            <div className="text-xs space-y-1 bg-gray-50 p-2 rounded">
              <div>User Agent: {navigator.userAgent}</div>
              <div>Protocol: {window.location.protocol}</div>
              <div>Host: {window.location.host}</div>
              <div>
                WebSocket URL: {`${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/ws/voice/streaming-stt`}
              </div>
              <div>
                MediaDevices Available: {navigator.mediaDevices ? 'Yes' : 'No'}
              </div>
              <div>
                getUserMedia Available: {typeof navigator.mediaDevices?.getUserMedia === 'function' ? 'Yes' : 'No'}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
