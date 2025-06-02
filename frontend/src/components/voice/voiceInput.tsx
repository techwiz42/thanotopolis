// src/components/voice/VoiceInput.tsx
import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Mic, MicOff, Volume2, VolumeX } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';
import { useAuth } from '@/contexts/AuthContext';

export interface VoiceInputProps {
  onTranscription: (text: string, isFinal: boolean) => void;
  onStatusChange?: (status: 'idle' | 'connecting' | 'recording' | 'error') => void;
  disabled?: boolean;
  className?: string;
}

interface AudioWorkletMessage {
  audioData: Float32Array;
}

export const VoiceInput: React.FC<VoiceInputProps> = ({
  onTranscription,
  onStatusChange,
  disabled = false,
  className = ''
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'connecting' | 'recording' | 'error'>('idle');
  const [currentTranscript, setCurrentTranscript] = useState('');
  
  const wsRef = useRef<WebSocket | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const { token } = useAuth();
  const { toast } = useToast();

  // Update parent component when status changes
  useEffect(() => {
    onStatusChange?.(connectionStatus);
  }, [connectionStatus, onStatusChange]);

  const createAudioWorklet = useCallback(async (audioContext: AudioContext) => {
    try {
      // Create a simple worklet for audio processing
      const workletCode = `
        class AudioProcessor extends AudioWorkletProcessor {
          constructor() {
            super();
            this.bufferSize = 4096;
            this.buffer = new Float32Array(this.bufferSize);
            this.bufferIndex = 0;
          }

          process(inputs) {
            const input = inputs[0];
            if (input.length > 0) {
              const channel = input[0];
              for (let i = 0; i < channel.length; i++) {
                this.buffer[this.bufferIndex] = channel[i];
                this.bufferIndex++;
                
                if (this.bufferIndex >= this.bufferSize) {
                  // Convert to 16-bit PCM
                  const pcmData = new Int16Array(this.bufferSize);
                  for (let j = 0; j < this.bufferSize; j++) {
                    pcmData[j] = Math.max(-32768, Math.min(32767, this.buffer[j] * 32768));
                  }
                  
                  this.port.postMessage({
                    audioData: pcmData
                  });
                  
                  this.bufferIndex = 0;
                }
              }
            }
            return true;
          }
        }
        
        registerProcessor('audio-processor', AudioProcessor);
      `;

      const blob = new Blob([workletCode], { type: 'application/javascript' });
      const workletUrl = URL.createObjectURL(blob);
      
      await audioContext.audioWorklet.addModule(workletUrl);
      URL.revokeObjectURL(workletUrl);
      
      return new AudioWorkletNode(audioContext, 'audio-processor');
    } catch (error) {
      console.error('Failed to create audio worklet:', error);
      throw error;
    }
  }, []);

  const connectToDeepgram = useCallback(async () => {
    if (!token) {
      toast({
        title: "Authentication Required",
        description: "Please log in to use voice input",
        variant: "destructive"
      });
      return false;
    }

    try {
      setIsConnecting(true);
      setConnectionStatus('connecting');

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/api/ws/voice/streaming-stt?token=${token}`;
      
      const ws = new WebSocket(wsUrl);
      
      return new Promise<boolean>((resolve) => {
        ws.onopen = () => {
          console.log('Connected to Deepgram streaming STT');
          
          // Send configuration
          ws.send(JSON.stringify({
            type: 'config',
            config: {
              model: 'nova-2',
              language: 'en-US',
              encoding: 'linear16',
              sample_rate: 16000,
              channels: 1,
              punctuate: true,
              interim_results: true,
              smart_format: true
            }
          }));
          
          wsRef.current = ws;
          setIsConnecting(false);
          setConnectionStatus('recording');
          resolve(true);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            
            switch (data.type) {
              case 'ready':
                console.log('Deepgram ready:', data.message);
                break;
                
              case 'transcription':
                const transcript = data.transcript || '';
                const isFinal = data.is_final || data.speech_final || false;
                
                if (transcript) {
                  setCurrentTranscript(isFinal ? '' : transcript);
                  onTranscription(transcript, isFinal);
                }
                break;
                
              case 'speech_started':
                console.log('Speech started detected');
                break;
                
              case 'utterance_end':
                console.log('Utterance ended');
                setCurrentTranscript('');
                break;
                
              case 'error':
                console.error('Deepgram error:', data.message);
                toast({
                  title: "Voice Input Error",
                  description: data.message || "An error occurred with voice input",
                  variant: "destructive"
                });
                break;
            }
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          setConnectionStatus('error');
          toast({
            title: "Connection Error",
            description: "Failed to connect to voice input service",
            variant: "destructive"
          });
          resolve(false);
        };

        ws.onclose = () => {
          console.log('Deepgram connection closed');
          wsRef.current = null;
          setConnectionStatus('idle');
        };
      });
    } catch (error) {
      console.error('Error connecting to Deepgram:', error);
      setIsConnecting(false);
      setConnectionStatus('error');
      return false;
    }
  }, [token, toast, onTranscription]);

  const startRecording = useCallback(async () => {
    try {
      if (disabled) return;

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      mediaStreamRef.current = stream;

      // Create audio context
      const audioContext = new AudioContext({ sampleRate: 16000 });
      audioContextRef.current = audioContext;

      // Connect to Deepgram
      const connected = await connectToDeepgram();
      if (!connected) {
        stream.getTracks().forEach(track => track.stop());
        return;
      }

      // Create audio worklet
      const workletNode = await createAudioWorklet(audioContext);
      workletNodeRef.current = workletNode;

      // Connect audio pipeline
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(workletNode);
      workletNode.connect(audioContext.destination);

      // Handle audio data from worklet
      workletNode.port.onmessage = (event) => {
        const { audioData } = event.data;
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          // Convert Int16Array to ArrayBuffer and send
          wsRef.current.send(audioData.buffer);
        }
      };

      setIsRecording(true);
      
    } catch (error) {
      console.error('Error starting recording:', error);
      setConnectionStatus('error');
      
      if (error instanceof Error && error.name === 'NotAllowedError') {
        toast({
          title: "Microphone Access Denied",
          description: "Please allow microphone access to use voice input",
          variant: "destructive"
        });
      } else {
        toast({
          title: "Recording Error",
          description: "Failed to start voice recording",
          variant: "destructive"
        });
      }
    }
  }, [disabled, connectToDeepgram, createAudioWorklet, toast]);

  const stopRecording = useCallback(() => {
    try {
      // Stop media stream
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach(track => track.stop());
        mediaStreamRef.current = null;
      }

      // Close audio context
      if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
      }

      // Clean up worklet
      if (workletNodeRef.current) {
        workletNodeRef.current.disconnect();
        workletNodeRef.current = null;
      }

      // Close WebSocket
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }

      setIsRecording(false);
      setCurrentTranscript('');
      setConnectionStatus('idle');
      
    } catch (error) {
      console.error('Error stopping recording:', error);
    }
  }, []);

  const toggleRecording = useCallback(() => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }, [isRecording, startRecording, stopRecording]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopRecording();
    };
  }, [stopRecording]);

  const getButtonColor = () => {
    if (disabled) return 'bg-gray-300';
    if (connectionStatus === 'error') return 'bg-red-500 hover:bg-red-600';
    if (isRecording) return 'bg-red-500 hover:bg-red-600 animate-pulse';
    if (isConnecting) return 'bg-yellow-500 hover:bg-yellow-600';
    return 'bg-blue-500 hover:bg-blue-600';
  };

  const getButtonIcon = () => {
    if (disabled) return <MicOff className="w-4 h-4" />;
    if (isRecording) return <Volume2 className="w-4 h-4" />;
    return <Mic className="w-4 h-4" />;
  };

  const getTooltipText = () => {
    if (disabled) return 'Voice input disabled';
    if (connectionStatus === 'error') return 'Voice input error - click to retry';
    if (isRecording) return 'Click to stop recording';
    if (isConnecting) return 'Connecting to voice service...';
    return 'Click to start voice input';
  };

  return (
    <div className={`flex flex-col items-center ${className}`}>
      <Button
        onClick={toggleRecording}
        disabled={disabled || isConnecting}
        className={`p-2 rounded-full transition-colors ${getButtonColor()}`}
        title={getTooltipText()}
        size="sm"
      >
        {getButtonIcon()}
      </Button>
      
      {currentTranscript && (
        <div className="mt-2 text-xs text-gray-600 max-w-xs text-center">
          <span className="italic">"{currentTranscript}"</span>
        </div>
      )}
      
      {connectionStatus === 'connecting' && (
        <div className="mt-1 text-xs text-gray-500">
          Connecting...
        </div>
      )}
      
      {connectionStatus === 'recording' && isRecording && (
        <div className="mt-1 text-xs text-green-600">
          Listening...
        </div>
      )}
    </div>
  );
};
