import React, { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Play, 
  Pause, 
  MoreHorizontal,
  Edit,
  Trash2,
  Copy,
  Download
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { telephonyService, CallMessage } from '@/services/telephony';
import { useToast } from '@/components/ui/use-toast';

interface CallMessageItemProps {
  message: CallMessage;
  onEdit?: (messageId: string) => void;
  onDelete?: (messageId: string) => void;
  showActions?: boolean;
}

export function CallMessageItem({ 
  message, 
  onEdit, 
  onDelete, 
  showActions = true 
}: CallMessageItemProps) {
  const { toast } = useToast();
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(null);

  // Handle audio playback for message segments
  const handlePlayAudio = () => {
    const audioUrl = message.metadata?.recording_segment_url;
    if (!audioUrl) return;

    if (isPlayingAudio && audioElement) {
      audioElement.pause();
      setIsPlayingAudio(false);
    } else {
      const audio = new Audio(audioUrl);
      setAudioElement(audio);
      
      audio.onplay = () => setIsPlayingAudio(true);
      audio.onpause = () => setIsPlayingAudio(false);
      audio.onended = () => setIsPlayingAudio(false);
      audio.onerror = () => {
        setIsPlayingAudio(false);
        toast({
          title: "Playback Error",
          description: "Failed to play audio segment. Please try again.",
          variant: "destructive"
        });
      };
      
      audio.play().catch(error => {
        console.error('Error playing audio:', error);
        toast({
          title: "Playback Error",
          description: "Failed to play audio segment. Please try again.",
          variant: "destructive"
        });
      });
    }
  };

  const handleCopyContent = () => {
    navigator.clipboard.writeText(message.content);
    toast({
      title: "Copied",
      description: "Message content copied to clipboard"
    });
  };

  const handleDownloadAudio = () => {
    const audioUrl = message.metadata?.recording_segment_url;
    if (!audioUrl) return;
    
    const link = document.createElement('a');
    link.href = audioUrl;
    link.download = `message-${message.id}-audio.mp3`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const hasAudioSegment = telephonyService.hasAudioSegment(message);

  return (
    <div className="flex flex-col space-y-2 p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Badge className={telephonyService.getSenderTypeColor(message.sender.type)}>
            {telephonyService.getMessageSenderName(message.sender)}
          </Badge>
          <Badge variant="outline" className={telephonyService.getMessageTypeColor(message.message_type)}>
            {message.message_type}
          </Badge>
          <span className="text-xs text-muted-foreground">
            {formatTimestamp(message.timestamp)}
          </span>
        </div>
        
        <div className="flex items-center space-x-1">
          {/* Audio controls */}
          {hasAudioSegment && (
            <>
              <Button 
                variant="ghost" 
                size="sm" 
                className="h-6 w-6 p-0"
                onClick={handlePlayAudio}
                title="Play audio segment"
              >
                {isPlayingAudio ? (
                  <Pause className="h-3 w-3" />
                ) : (
                  <Play className="h-3 w-3" />
                )}
              </Button>
              {message.metadata?.recording_segment_url && (
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="h-6 w-6 p-0"
                  onClick={handleDownloadAudio}
                  title="Download audio segment"
                >
                  <Download className="h-3 w-3" />
                </Button>
              )}
            </>
          )}
          
          {/* Actions menu */}
          {showActions && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                  <MoreHorizontal className="h-3 w-3" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={handleCopyContent}>
                  <Copy className="h-4 w-4 mr-2" />
                  Copy content
                </DropdownMenuItem>
                {onEdit && (
                  <DropdownMenuItem onClick={() => onEdit(message.id)}>
                    <Edit className="h-4 w-4 mr-2" />
                    Edit message
                  </DropdownMenuItem>
                )}
                {onDelete && (
                  <DropdownMenuItem 
                    onClick={() => onDelete(message.id)}
                    className="text-destructive"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Delete message
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="text-sm leading-relaxed">
        {message.content}
      </div>

      {/* Metadata */}
      {message.metadata && Object.keys(message.metadata).length > 0 && (
        <div className="flex flex-wrap gap-3 text-xs text-muted-foreground mt-2 pt-2 border-t">
          {message.metadata.confidence_score && (
            <span>
              Confidence: {Math.round(message.metadata.confidence_score * 100)}%
            </span>
          )}
          {message.metadata.language && (
            <span>Language: {message.metadata.language}</span>
          )}
          {message.metadata.audio_start_time !== undefined && message.metadata.audio_end_time !== undefined && (
            <span>
              Audio: {message.metadata.audio_start_time}s - {message.metadata.audio_end_time}s
            </span>
          )}
          {message.metadata.is_automated && (
            <span className="text-blue-600">Automated</span>
          )}
        </div>
      )}
    </div>
  );
}