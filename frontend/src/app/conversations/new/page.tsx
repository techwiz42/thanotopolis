// src/app/conversations/new/page.tsx
'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { conversationService } from '@/services/conversations';
import { useToast } from '@/components/ui/use-toast';
import { ArrowLeft } from 'lucide-react';

export default function NewConversationPage() {
  const { token } = useAuth();
  const router = useRouter();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    description: ''
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.title.trim()) {
      toast({
        title: 'Validation Error',
        description: 'Please enter a title for the conversation',
        variant: 'destructive'
      });
      return;
    }

    if (!token) {
      toast({
        title: 'Authentication Error',
        description: 'You must be logged in to create conversations',
        variant: 'destructive'
      });
      router.push('/login');
      return;
    }

    try {
      setIsLoading(true);
      const response = await conversationService.createConversation(
        {
          title: formData.title.trim(),
          description: formData.description.trim() || undefined
        },
        token
      );

      toast({
        title: 'Success',
        description: 'Conversation created successfully'
      });

      // Navigate to the new conversation
      router.push(`/conversations/${response.data.id}`);
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to create conversation',
        variant: 'destructive'
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <Button
          variant="ghost"
          onClick={() => router.push('/conversations')}
          className="mb-4"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Conversations
        </Button>
        
        <h1 className="text-2xl font-bold text-gray-900">Create New Conversation</h1>
        <p className="mt-2 text-sm text-gray-600">
          Start a new AI-powered conversation with multiple participants
        </p>
      </div>

      <Card>
        <CardContent className="p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label 
                htmlFor="title" 
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Title *
              </label>
              <Input
                id="title"
                type="text"
                placeholder="Enter conversation title"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                disabled={isLoading}
                className="w-full"
                autoFocus
              />
            </div>

            <div>
              <label 
                htmlFor="description" 
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Description (optional)
              </label>
              <Textarea
                id="description"
                placeholder="Enter a brief description of this conversation"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                disabled={isLoading}
                rows={4}
                className="w-full"
              />
            </div>

            <div className="pt-4 flex gap-3">
              <Button
                type="submit"
                disabled={isLoading || !formData.title.trim()}
                className="flex-1"
              >
                {isLoading ? 'Creating...' : 'Create Conversation'}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => router.push('/conversations')}
                disabled={isLoading}
              >
                Cancel
              </Button>
            </div>
          </form>

          <div className="mt-6 p-4 bg-blue-50 rounded-lg">
            <h3 className="text-sm font-medium text-blue-900 mb-2">
              What happens next?
            </h3>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• You'll be taken to your new conversation</li>
              <li>• You can invite participants via email</li>
              <li>• AI agents will help facilitate the discussion</li>
              <li>• All messages are saved and can be searched</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
