// Simplified voice hook that sends audio chunks directly
import { useState, useRef, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/components/ui/use-toast';

export const useSimpleVoice = ({ conversationId, onTranscript }: any) => {
  const { token } = useAuth();
  const { toast } = useToast();
  const [isRecording, setIsRecording] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);

  const startRecording = useCallback(async () => {
    if (!token) {
      toast({
        title: "Authentication Required",
        description: "Please log in to use voice features",
        variant: "destructive"
      });
      return;
    }

    try {
      // Get microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000,
          channelCount: 1
        } 
      });
      streamRef.current = stream;

      // Connect to WebSocket
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const backendHost = process.env.NEXT_PUBLIC_API_URL ? 
        new URL(process.env.NEXT_PUBLIC_API_URL).host : 'localhost:8000';
      const wsUrl = `${protocol}//${backendHost}/api/ws/voice/streaming-stt?token=${encodeURIComponent(token)}`;
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('STT WebSocket connected');
        
        // Create MediaRecorder - try different formats
        let recorder: MediaRecorder | null = null;
        const formats = [
          'audio/webm',
          'audio/webm;codecs=opus',
          'audio/ogg;codecs=opus'
        ];
        
        for (const format of formats) {
          if (MediaRecorder.isTypeSupported(format)) {
            console.log(`Using format: ${format}`);
            recorder = new MediaRecorder(stream, { 
              mimeType: format,
              audioBitsPerSecond: 16000
            });
            break;
          }
        }
        
        if (!recorder) {
          recorder = new MediaRecorder(stream);
          console.log('Using default format');
        }
        
        recorderRef.current = recorder;
        
        // Send audio chunks
        recorder.ondataavailable = (event) => {
          if (event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
            console.log(`Sending audio chunk: ${event.data.size} bytes`);
            ws.send(event.data);
          }
        };
        
        // Start recording with small time slices
        recorder.start(100); // Send every 100ms
        setIsRecording(true);
        console.log('Recording started');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('STT message:', data);
          
          if (data.type === 'transcript' && data.transcript) {
            onTranscript?.(data.transcript, data.is_final || data.speech_final);
          }
        } catch (error) {
          console.error('Error parsing STT message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('STT WebSocket error:', error);
        toast({
          title: "Voice Input Error",
          description: "Failed to connect to speech recognition",
          variant: "destructive"
        });
      };

      ws.onclose = () => {
        console.log('STT WebSocket closed');
        setIsRecording(false);
      };

    } catch (error) {
      console.error('Error starting recording:', error);
      toast({
        title: "Microphone Access Denied",
        description: "Please allow microphone access",
        variant: "destructive"
      });
    }
  }, [token, toast, onTranscript]);

  const stopRecording = useCallback(() => {
    console.log('Stopping recording');
    
    if (recorderRef.current && recorderRef.current.state === 'recording') {
      recorderRef.current.stop();
    }
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setIsRecording(false);
  }, []);

  return {
    isRecording,
    startRecording,
    stopRecording
  };
};