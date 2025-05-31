// src/app/conversations/page.tsx
'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { conversationService } from '@/services/conversations';
import { Conversation } from '@/types/conversation';
import { Plus, MessageSquare, Users, Clock } from 'lucide-react';

export default function ConversationsPage() {
  const { token } = useAuth();
  const router = useRouter();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      router.push('/login');
      return;
    }

    loadConversations();
  }, [token, router]);

  const loadConversations = async () => {
    try {
      setIsLoading(true);
      const response = await conversationService.getConversations(token!);
      setConversations(response.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversations');
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 60) return `${diffMins} minutes ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)} hours ago`;
    if (diffMins < 10080) return `${Math.floor(diffMins / 1440)} days ago`;
    
    return date.toLocaleDateString();
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading conversations...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Conversations</h1>
        <Button 
          onClick={() => router.push('/conversations/new')}
          className="flex items-center"
        >
          <Plus className="mr-2 h-4 w-4" />
          New Conversation
        </Button>
      </div>

      {conversations.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <MessageSquare className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No conversations</h3>
            <p className="mt-1 text-sm text-gray-500">Get started by creating a new conversation.</p>
            <div className="mt-6">
              <Button onClick={() => router.push('/conversations/new')}>
                <Plus className="mr-2 h-4 w-4" />
                New Conversation
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {conversations.map((conversation) => (
            <Card 
              key={conversation.id}
              className="hover:shadow-lg transition-shadow cursor-pointer"
              onClick={() => router.push(`/conversations/${conversation.id}`)}
            >
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="text-lg font-medium text-gray-900 mb-1">
                      {conversation.title}
                    </h3>
                    {conversation.description && (
                      <p className="text-sm text-gray-500 line-clamp-2 mb-3">
                        {conversation.description}
                      </p>
                    )}
                    <div className="flex items-center text-xs text-gray-500 space-x-4">
                      <div className="flex items-center">
                        <Clock className="mr-1 h-3 w-3" />
                        {formatDate(conversation.updated_at || conversation.created_at)}
                      </div>
                      {conversation.participants && conversation.participants.length > 0 && (
                        <div className="flex items-center">
                          <Users className="mr-1 h-3 w-3" />
                          {conversation.participants.length + 1} participants
                        </div>
                      )}
                    </div>
                  </div>
                  <MessageSquare className="h-5 w-5 text-gray-400 ml-2 flex-shrink-0" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
