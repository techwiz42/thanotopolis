// src/app/conversations/new/page.tsx
'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Loader2, Plus, X } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';
import { conversationService } from '@/services/conversations';

export default function NewConversationPage() {
  const router = useRouter();
  const { user, token } = useAuth();
  const { toast } = useToast();
  
  // Generate title with participant emails
  const generateTitleWithParticipants = (emails: string[] = []) => {
    const allEmails = [user?.email, ...emails].filter(Boolean) as string[];
    
    if (allEmails.length === 0) {
      return "New Conversation";
    } else if (allEmails.length === 1) {
      return `Conversation with ${allEmails[0]}`;
    } else if (allEmails.length === 2) {
      return `Conversation with ${allEmails[0]} and ${allEmails[1]}`;
    } else if (allEmails.length <= 4) {
      // For 3-4 participants, list all emails
      return `Conversation with ${allEmails.slice(0, -1).join(', ')}, and ${allEmails[allEmails.length - 1]}`;
    } else {
      // For 5+ participants, show first few and indicate more
      return `Conversation with ${allEmails.slice(0, 3).join(', ')}, and ${allEmails.length - 3} others`;
    }
  };

  // Generate default title with username and timestamp (fallback)
  const generateDefaultTitle = () => {
    const now = new Date();
    const dateStr = now.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric' 
    });
    const timeStr = now.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
    return `${user?.username || user?.email || 'User'} - ${dateStr} ${timeStr}`;
  };

  const [title, setTitle] = useState(generateTitleWithParticipants([]));
  const [description, setDescription] = useState('');
  const [participantEmails, setParticipantEmails] = useState<string[]>([]);
  const [currentEmail, setCurrentEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [userModifiedTitle, setUserModifiedTitle] = useState(false);

  const handleAddEmail = () => {
    const trimmedEmail = currentEmail.trim();
    if (trimmedEmail && !participantEmails.includes(trimmedEmail)) {
      // Basic email validation
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (emailRegex.test(trimmedEmail)) {
        const newEmails = [...participantEmails, trimmedEmail];
        setParticipantEmails(newEmails);
        setCurrentEmail('');
        
        // Auto-update title unless user has manually modified it
        if (!userModifiedTitle) {
          setTitle(generateTitleWithParticipants(newEmails));
        }
      } else {
        toast({
          title: "Invalid Email",
          description: "Please enter a valid email address",
          variant: "destructive"
        });
      }
    }
  };

  const handleRemoveEmail = (emailToRemove: string) => {
    const newEmails = participantEmails.filter(email => email !== emailToRemove);
    setParticipantEmails(newEmails);
    
    // Auto-update title unless user has manually modified it
    if (!userModifiedTitle) {
      setTitle(generateTitleWithParticipants(newEmails));
    }
  };

  const handleTitleChange = (newTitle: string) => {
    setTitle(newTitle);
    setUserModifiedTitle(true);
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddEmail();
    }
  };

  const handleCreateConversation = async () => {
    if (!token) {
      toast({
        title: "Authentication Error",
        description: "You must be logged in to create a conversation",
        variant: "destructive"
      });
      return;
    }

    setIsLoading(true);

    try {
      // Create the conversation
      const conversationData = {
        // Only send title if user manually modified it, otherwise let backend generate it
        title: userModifiedTitle ? title.trim() : '',
        description: description.trim()
      };

      console.log('Creating conversation with data:', conversationData);
      
      const conversation = await conversationService.createConversation(conversationData, token);
      
      console.log('Conversation creation response:', conversation);
      
      const conversationId = conversation.id;
      console.log('Extracted conversation ID:', conversationId);

      // Add participants if any
      if (participantEmails.length > 0) {
        // Add participants one by one (you might want to create a batch endpoint)
        for (const email of participantEmails) {
          try {
            await conversationService.addParticipant(conversationId, { email }, token);
          } catch (error) {
            console.error(`Failed to add participant ${email}:`, error);
            toast({
              title: "Warning",
              description: `Failed to add participant: ${email}`,
              variant: "destructive"
            });
          }
        }
      }

      toast({
        title: "Success",
        description: "Conversation created successfully",
      });

      // Navigate to the new conversation
      router.push(`/conversations/${conversationId}`);
    } catch (error) {
      console.error('Error creating conversation:', error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to create conversation",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-4 max-w-2xl">
      <Card>
        <CardHeader>
          <CardTitle>Create New Conversation</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="title">Title</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => handleTitleChange(e.target.value)}
              placeholder="Enter conversation title"
            />
            {!userModifiedTitle && participantEmails.length > 0 && (
              <p className="text-sm text-gray-600">
                Title will be auto-generated based on participants
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description (Optional)</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Enter conversation description"
              rows={3}
            />
          </div>

          <div className="space-y-2">
            <Label>Participants</Label>
            <div className="flex gap-2">
              <Input
                value={currentEmail}
                onChange={(e) => setCurrentEmail(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Enter participant email"
                type="email"
              />
              <Button
                type="button"
                variant="outline"
                onClick={handleAddEmail}
                disabled={!currentEmail.trim()}
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            
            {participantEmails.length > 0 && (
              <div className="mt-2 space-y-1">
                {participantEmails.map((email) => (
                  <div
                    key={email}
                    className="flex items-center justify-between bg-gray-100 rounded px-3 py-1"
                  >
                    <span className="text-sm">{email}</span>
                    <button
                      onClick={() => handleRemoveEmail(email)}
                      className="text-red-500 hover:text-red-700"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex gap-2 pt-4">
            <Button
              variant="outline"
              onClick={() => router.push('/conversations')}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreateConversation}
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Conversation'
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
