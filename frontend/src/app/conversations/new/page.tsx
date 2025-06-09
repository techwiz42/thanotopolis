// src/app/conversations/new/page.tsx
'use client';

import React, { useState, useEffect } from 'react';
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
  

  const [title, setTitle] = useState('');
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
        const newEmails = [...participantEmails, trimmedEmail];
        setParticipantEmails(newEmails);
        setCurrentEmail('');
        
        // Don't auto-update title - let backend generate it
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
    
    // Don't auto-update title - let backend generate it
  };

  const handleTitleChange = (newTitle: string) => {
    setTitle(newTitle);
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
      // Parse emails from the current input field
      const emailsToAdd = currentEmail.trim()
        .split(/[,;\s]+/) // Split by comma, semicolon, or whitespace
        .map(email => email.trim())
        .filter(email => {
          // Basic email validation
          const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
          return email && emailRegex.test(email);
        });

      // Combine with any previously added emails
      const allEmails = Array.from(new Set([...participantEmails, ...emailsToAdd])); // Remove duplicates

      // Create the conversation
      const conversationData: any = {
        description: description.trim(),
        participant_emails: allEmails  // Include all participant emails
      };
      
      // Only include title if user provided one
      if (title.trim()) {
        conversationData.title = title.trim();
      }

      
      const conversation = await conversationService.createConversation(conversationData, token);
      const conversationId = conversation.id;

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
            <p className="text-sm text-gray-600">
              Leave empty to auto-generate title with participant emails
            </p>
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
            <p className="text-sm text-gray-600 mb-2">
              Enter email addresses separated by commas or spaces
            </p>
            <div className="flex gap-2">
              <Input
                value={currentEmail}
                onChange={(e) => setCurrentEmail(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Enter participant emails (comma or space separated)"
                type="email"
              />
              <Button
                type="button"
                variant="outline"
                onClick={(e) => {
                  e.preventDefault();
                  handleAddEmail();
                }}
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
