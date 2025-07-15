'use client'

import React, { useState, useEffect, use } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowLeft, AlertCircle, CheckCircle, Clock, MessageSquare, Send, User } from 'lucide-react'
import Link from 'next/link'

interface Issue {
  id: string
  title: string
  description: string
  type: string
  status: string
  priority: string
  reporter_name?: string
  reporter_email?: string
  created_at: string
  updated_at: string
  resolved_at?: string
  resolution?: string
  comments: Comment[]
}

interface Comment {
  id: string
  content: string
  user_id?: string
  author_name?: string
  author_email?: string
  created_at: string
}

export default function IssueDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter()
  const resolvedParams = use(params)
  const [issue, setIssue] = useState<Issue | null>(null)
  const [loading, setLoading] = useState(true)
  const [isAddingComment, setIsAddingComment] = useState(false)
  const [commentForm, setCommentForm] = useState({
    content: '',
    author_name: '',
    author_email: ''
  })

  useEffect(() => {
    fetchIssue()
  }, [resolvedParams.id])

  const fetchIssue = async () => {
    try {
      const response = await fetch(`/api/issues/${resolvedParams.id}`)
      if (!response.ok) throw new Error('Failed to fetch issue')
      
      const data = await response.json()
      setIssue(data)
    } catch (error) {
      console.error('Error fetching issue:', error)
      router.push('/issues')
    } finally {
      setLoading(false)
    }
  }

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsAddingComment(true)

    try {
      const response = await fetch(`/api/issues/${resolvedParams.id}/comments`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(commentForm)
      })

      if (!response.ok) throw new Error('Failed to add comment')

      // Reset form and refresh issue
      setCommentForm({ content: '', author_name: '', author_email: '' })
      await fetchIssue()
    } catch (error) {
      console.error('Error adding comment:', error)
      alert('Failed to add comment. Please try again.')
    } finally {
      setIsAddingComment(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'open':
        return <AlertCircle className="w-6 h-6 text-red-500" />
      case 'in_progress':
        return <Clock className="w-6 h-6 text-yellow-500" />
      case 'resolved':
      case 'closed':
        return <CheckCircle className="w-6 h-6 text-green-500" />
      default:
        return <AlertCircle className="w-6 h-6 text-gray-500" />
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'text-red-600 bg-red-50 border-red-200'
      case 'high':
        return 'text-orange-600 bg-orange-50 border-orange-200'
      case 'medium':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      case 'low':
        return 'text-green-600 bg-green-50 border-green-200'
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex justify-center items-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!issue) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <Link
            href="/issues"
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-5 h-5" />
            Back to Issues
          </Link>
        </div>

        {/* Issue Header */}
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="p-6">
            <div className="flex items-start gap-4 mb-4">
              {getStatusIcon(issue.status)}
              <div className="flex-1">
                <h1 className="text-2xl font-bold text-gray-900 mb-2">{issue.title}</h1>
                <div className="flex flex-wrap gap-3 text-sm">
                  <span className={`px-3 py-1 rounded-full border ${getPriorityColor(issue.priority)}`}>
                    {issue.priority} priority
                  </span>
                  <span className="text-gray-500">
                    {issue.type.replace('_', ' ')}
                  </span>
                  <span className="text-gray-500">
                    Reported by {issue.reporter_name || 'Anonymous'}
                  </span>
                  <span className="text-gray-500">
                    {formatDate(issue.created_at)}
                  </span>
                </div>
              </div>
            </div>

            <div className="prose max-w-none">
              <h3 className="text-lg font-medium text-gray-900 mb-2">Description</h3>
              <p className="text-gray-700 whitespace-pre-wrap">{issue.description}</p>
            </div>

            {issue.resolution && (
              <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
                <h3 className="text-lg font-medium text-green-900 mb-2">Resolution</h3>
                <p className="text-green-800">{issue.resolution}</p>
                {issue.resolved_at && (
                  <p className="text-sm text-green-600 mt-2">
                    Resolved on {formatDate(issue.resolved_at)}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Comments Section */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b">
            <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
              <MessageSquare className="w-6 h-6" />
              Comments ({issue.comments.length})
            </h2>
          </div>

          {/* Comments List */}
          {issue.comments.length > 0 && (
            <div className="divide-y">
              {issue.comments.map((comment) => (
                <div key={comment.id} className="p-6">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center">
                      <User className="w-5 h-5 text-gray-500" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="font-medium text-gray-900">
                          {comment.author_name || 'Anonymous'}
                        </span>
                        <span className="text-sm text-gray-500">
                          {formatDate(comment.created_at)}
                        </span>
                      </div>
                      <p className="text-gray-700 whitespace-pre-wrap">{comment.content}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Add Comment Form */}
          <div className="p-6 bg-gray-50">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Add a Comment</h3>
            <form onSubmit={handleAddComment}>
              <div className="space-y-4">
                <div>
                  <label htmlFor="content" className="block text-sm font-medium text-gray-700 mb-2">
                    Comment <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    id="content"
                    name="content"
                    required
                    value={commentForm.content}
                    onChange={(e) => setCommentForm({ ...commentForm, content: e.target.value })}
                    rows={4}
                    placeholder="Share your thoughts or updates..."
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="author_name" className="block text-sm font-medium text-gray-700 mb-2">
                      Your Name (Optional)
                    </label>
                    <input
                      type="text"
                      id="author_name"
                      name="author_name"
                      value={commentForm.author_name}
                      onChange={(e) => setCommentForm({ ...commentForm, author_name: e.target.value })}
                      placeholder="John Doe"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label htmlFor="author_email" className="block text-sm font-medium text-gray-700 mb-2">
                      Your Email (Optional)
                    </label>
                    <input
                      type="email"
                      id="author_email"
                      name="author_email"
                      value={commentForm.author_email}
                      onChange={(e) => setCommentForm({ ...commentForm, author_email: e.target.value })}
                      placeholder="john@example.com"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                </div>

                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={isAddingComment}
                    className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isAddingComment ? (
                      <>
                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                        Posting...
                      </>
                    ) : (
                      <>
                        <Send className="w-5 h-5" />
                        Post Comment
                      </>
                    )}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}