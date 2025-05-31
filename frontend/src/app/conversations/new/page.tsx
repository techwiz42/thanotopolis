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
  
  // Generate default title with username and timestamp
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
    return `${user?.first_name || user?.username || user?.email || 'User'} - ${dateStr} ${timeStr}`;
  };

  const [title, setTitle] = useState(generateDefaultTitle());
  const [description, setDescription] = useState('');
  const [participantEmails, setParticipantEmails] = useState<string[]>([]);
  const [currentEmail, setCurrentEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleAddEmail = () => {
    const trimmedEmail = currentEmail.trim();
    if (trimmedEmail && !participantEmails.includes(trimmedEmail)) {
      // Basic email validation
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (emailRegex.test(trimmedEmail)) {
        setParticipantEmails([...participantEmails, trimmedEmail]);
        setCurrentEmail('');
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
    setParticipantEmails(participantEmails.filter(email => email !== emailToRemove));
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
        title: title.trim() || generateDefaultTitle(),
        description: description.trim()
      };

      console.log('Creating conversation with data:', conversationData);
      
      const conversation = await conversationService.createConversation(conversationData, token);
      
      console.log('Create conversation response:', conversation);
      console.log('Conversation ID:', conversation?.id);
      
      // Backend now returns conversation directly (not wrapped in data)
      if (!conversation || !conversation.id) {
        console.error('Invalid conversation response:', conversation);
        throw new Error('Invalid response from server - missing conversation ID');
      }
      
      const conversationId = conversation.id;
      console.log('Successfully extracted conversation ID:', conversationId);

      // Add participants if any
      if (participantEmails.length > 0) {
        console.log('Adding participants:', participantEmails);
        for (const email of participantEmails) {
          try {
            await conversationService.addParticipant(conversationId, { email }, token);
            console.log(`Successfully added participant: ${email}`);
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
      console.log('Navigating to:', `/conversations/${conversationId}`);
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
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter conversation title"
            />
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
