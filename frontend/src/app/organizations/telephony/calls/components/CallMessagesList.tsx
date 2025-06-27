import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { 
  Volume2, 
  MessageCircle, 
  FileText, 
  Settings,
  Filter,
  Download
} from 'lucide-react';
import { CallMessageItem } from './CallMessageItem';
import { CallMessageGroup } from './CallMessageGroup';
import { telephonyService, CallMessage } from '@/services/telephony';
import { useToast } from '@/components/ui/use-toast';

interface CallMessagesListProps {
  messages: CallMessage[];
  onEditMessage?: (messageId: string) => void;
  onDeleteMessage?: (messageId: string) => void;
  showActions?: boolean;
  showTabs?: boolean;
}

export function CallMessagesList({ 
  messages, 
  onEditMessage, 
  onDeleteMessage, 
  showActions = true,
  showTabs = true
}: CallMessagesListProps) {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState('all');

  const sortedMessages = telephonyService.sortMessagesByTimestamp(messages);
  const messagesByType = telephonyService.groupMessagesByType(messages);

  const handleDownloadTranscript = () => {
    const transcript = telephonyService.getCallTranscript(messages);
    if (!transcript) {
      toast({
        title: "No Transcript",
        description: "No transcript messages found for this call",
        variant: "destructive"
      });
      return;
    }

    const blob = new Blob([transcript], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'call-transcript.txt';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    toast({
      title: "Downloaded",
      description: "Call transcript downloaded successfully"
    });
  };

  if (messages.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <MessageCircle className="h-5 w-5 mr-2" />
            Call Messages
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            No messages available for this call
          </div>
        </CardContent>
      </Card>
    );
  }

  const renderMessagesList = (messagesToRender: CallMessage[]) => {
    const groupedMessages = telephonyService.groupConsecutiveMessagesBySender(messagesToRender);
    
    return (
      <div className="space-y-3">
        {groupedMessages.map((messageGroup, index) => (
          <CallMessageGroup
            key={messageGroup[0].id}
            messages={messageGroup}
            onEdit={onEditMessage}
            onDelete={onDeleteMessage}
            showActions={showActions}
          />
        ))}
      </div>
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center">
            <MessageCircle className="h-5 w-5 mr-2" />
            Call Messages
          </div>
          <div className="flex items-center space-x-2">
            <Badge variant="secondary">
              {messages.length} total
            </Badge>
            {messagesByType.transcript?.length > 0 && (
              <Button 
                variant="outline" 
                size="sm"
                onClick={handleDownloadTranscript}
              >
                <Download className="h-4 w-4 mr-2" />
                Download Transcript
              </Button>
            )}
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {showTabs ? (
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-5">
              <TabsTrigger value="all" className="flex items-center">
                <MessageCircle className="h-4 w-4 mr-1" />
                All ({messages.length})
              </TabsTrigger>
              <TabsTrigger value="transcript" className="flex items-center">
                <Volume2 className="h-4 w-4 mr-1" />
                Transcript ({messagesByType.transcript?.length || 0})
              </TabsTrigger>
              <TabsTrigger value="summary" className="flex items-center">
                <FileText className="h-4 w-4 mr-1" />
                Summary ({messagesByType.summary?.length || 0})
              </TabsTrigger>
              <TabsTrigger value="system" className="flex items-center">
                <Settings className="h-4 w-4 mr-1" />
                System ({messagesByType.system?.length || 0})
              </TabsTrigger>
              <TabsTrigger value="note" className="flex items-center">
                <FileText className="h-4 w-4 mr-1" />
                Notes ({messagesByType.note?.length || 0})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="all" className="mt-4">
              {renderMessagesList(sortedMessages)}
            </TabsContent>

            <TabsContent value="transcript" className="mt-4">
              {messagesByType.transcript?.length > 0 ? (
                renderMessagesList(telephonyService.sortMessagesByTimestamp(messagesByType.transcript))
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  No transcript messages found
                </div>
              )}
            </TabsContent>

            <TabsContent value="summary" className="mt-4">
              {messagesByType.summary?.length > 0 ? (
                renderMessagesList(telephonyService.sortMessagesByTimestamp(messagesByType.summary))
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  No summary messages found
                </div>
              )}
            </TabsContent>

            <TabsContent value="system" className="mt-4">
              {messagesByType.system?.length > 0 ? (
                renderMessagesList(telephonyService.sortMessagesByTimestamp(messagesByType.system))
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  No system messages found
                </div>
              )}
            </TabsContent>

            <TabsContent value="note" className="mt-4">
              {messagesByType.note?.length > 0 ? (
                renderMessagesList(telephonyService.sortMessagesByTimestamp(messagesByType.note))
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  No note messages found
                </div>
              )}
            </TabsContent>
          </Tabs>
        ) : (
          <div className="mt-4">
            {renderMessagesList(sortedMessages)}
          </div>
        )}
      </CardContent>
    </Card>
  );
}