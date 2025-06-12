'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { User } from '@/types/user.types'

const OrganizationMembersPage = () => {
  const { user, tokens, organization } = useAuth()
  const router = useRouter()
  const [members, setMembers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [success, setSuccess] = useState('')

  // Check admin access
  useEffect(() => {
    if (user && user.role !== 'admin' && user.role !== 'super_admin' && user.role !== 'org_admin') {
      router.push('/conversations')
      return
    }
  }, [user, router])

  // Fetch organization members
  useEffect(() => {
    const fetchMembers = async () => {
      if (!tokens?.access_token || !organization || !user?.tenant_id) {
        setLoading(false)
        return
      }

      try {
        const response = await fetch(`/api/organizations/${user.tenant_id}/users`, {
          headers: {
            'Authorization': `Bearer ${tokens.access_token}`,
            'X-Tenant-ID': organization,
            'Content-Type': 'application/json'
          }
        })

        if (!response.ok) {
          throw new Error('Failed to fetch organization members')
        }

        const membersData = await response.json()
        setMembers(membersData)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load members')
      } finally {
        setLoading(false)
      }
    }

    fetchMembers()
  }, [tokens, organization, user])

  const handleDeactivateUser = async (userId: string, userName: string) => {
    if (!tokens?.access_token || !organization || !user?.tenant_id) return

    if (!confirm(`Are you sure you want to deactivate ${userName}? They will lose access to the organization.`)) {
      return
    }

    setActionLoading(userId)
    setError('')
    setSuccess('')

    try {
      const response = await fetch(`/api/organizations/${user.tenant_id}/users/${userId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`,
          'X-Tenant-ID': organization,
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to deactivate user')
      }

      // Update local state
      setMembers(prev => prev.map(member => 
        member.id === userId ? { ...member, is_active: false } : member
      ))

      setSuccess(`${userName} has been deactivated successfully`)
      setTimeout(() => setSuccess(''), 3000)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to deactivate user')
    } finally {
      setActionLoading(null)
    }
  }

  const handleReactivateUser = async (userId: string, userName: string) => {
    if (!tokens?.access_token || !organization || !user?.tenant_id) return

    setActionLoading(userId)
    setError('')
    setSuccess('')

    try {
      const response = await fetch(`/api/organizations/${user.tenant_id}/users/${userId}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`,
          'X-Tenant-ID': organization,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ is_active: true })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to reactivate user')
      }

      // Update local state
      setMembers(prev => prev.map(member => 
        member.id === userId ? { ...member, is_active: true } : member
      ))

      setSuccess(`${userName} has been reactivated successfully`)
      setTimeout(() => setSuccess(''), 3000)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reactivate user')
    } finally {
      setActionLoading(null)
    }
  }

  const handleUpdateRole = async (userId: string, userName: string, newRole: string) => {
    if (!tokens?.access_token || !organization || !user?.tenant_id) return

    if (!confirm(`Are you sure you want to change ${userName}'s role to ${newRole}?`)) {
      return
    }

    setActionLoading(userId)
    setError('')
    setSuccess('')

    try {
      const response = await fetch(`/api/organizations/${user.tenant_id}/users/${userId}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`,
          'X-Tenant-ID': organization,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ role: newRole })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to update user role')
      }

      const updatedUser = await response.json()
      
      // Update local state
      setMembers(prev => prev.map(member => 
        member.id === userId ? updatedUser : member
      ))

      setSuccess(`${userName}'s role has been updated to ${newRole}`)
      setTimeout(() => setSuccess(''), 3000)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update user role')
    } finally {
      setActionLoading(null)
    }
  }

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'super_admin':
        return 'bg-red-100 text-red-800'
      case 'admin':
        return 'bg-purple-100 text-purple-800'
      case 'org_admin':
        return 'bg-blue-100 text-blue-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getAvailableRoles = (currentUserRole: string, targetUserRole: string) => {
    // Super admins can assign any role
    if (currentUserRole === 'super_admin') {
      return ['user', 'org_admin', 'admin', 'super_admin']
    }
    
    // Regular admins can assign up to admin
    if (currentUserRole === 'admin') {
      return ['user', 'org_admin', 'admin']
    }
    
    // Org admins can only assign up to org_admin
    if (currentUserRole === 'org_admin') {
      return ['user', 'org_admin']
    }
    
    return ['user']
  }

  if (!user) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-6">Organization Members</h1>
        <div>Loading user data...</div>
      </div>
    )
  }

  if (user.role !== 'admin' && user.role !== 'super_admin' && user.role !== 'org_admin') {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-6">Organization Members</h1>
        <div>You don't have permission to manage organization members.</div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-6">Organization Members</h1>
        <div>Loading members...</div>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Organization Members</h1>
        <div className="flex gap-2">
          <Button 
            onClick={() => router.push('/organizations/edit')}
            variant="outline"
          >
            Back to Organization
          </Button>
          <Button 
            onClick={() => router.push('/admin')}
            variant="outline"
          >
            Back to Admin
          </Button>
        </div>
      </div>

      {error && (
        <Card className="p-4 mb-6 bg-red-50 border-red-200">
          <p className="text-sm text-red-800">{error}</p>
        </Card>
      )}

      {success && (
        <Card className="p-4 mb-6 bg-green-50 border-green-200">
          <p className="text-sm text-green-800">{success}</p>
        </Card>
      )}

      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">Members ({members.length})</h2>
        
        {members.length === 0 ? (
          <p className="text-gray-500">No members found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-2">Name</th>
                  <th className="text-left py-3 px-2">Email</th>
                  <th className="text-left py-3 px-2">Username</th>
                  <th className="text-left py-3 px-2">Role</th>
                  <th className="text-left py-3 px-2">Status</th>
                  <th className="text-left py-3 px-2">Member Since</th>
                  <th className="text-left py-3 px-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {members.map((member) => (
                  <tr key={member.id} className="border-b hover:bg-gray-50">
                    <td className="py-3 px-2">
                      {member.first_name || member.last_name ? 
                        `${member.first_name || ''} ${member.last_name || ''}`.trim() : 
                        '-'
                      }
                    </td>
                    <td className="py-3 px-2">{member.email}</td>
                    <td className="py-3 px-2">{member.username}</td>
                    <td className="py-3 px-2">
                      <select
                        value={member.role}
                        onChange={(e) => handleUpdateRole(member.id, member.username, e.target.value)}
                        disabled={member.id === user.id || actionLoading === member.id}
                        className="text-xs px-2 py-1 rounded-full border focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        {getAvailableRoles(user.role, member.role).map(role => (
                          <option key={role} value={role}>
                            {role.replace('_', ' ')}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="py-3 px-2">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        member.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {member.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="py-3 px-2 text-sm text-gray-600">
                      {new Date(member.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-2">
                      <div className="flex gap-2">
                        {member.id !== user.id && (
                          <>
                            {member.is_active ? (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleDeactivateUser(member.id, member.username)}
                                disabled={actionLoading === member.id}
                                className="text-red-600 hover:text-red-700 hover:bg-red-50"
                              >
                                {actionLoading === member.id ? 'Processing...' : 'Deactivate'}
                              </Button>
                            ) : (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleReactivateUser(member.id, member.username)}
                                disabled={actionLoading === member.id}
                                className="text-green-600 hover:text-green-700 hover:bg-green-50"
                              >
                                {actionLoading === member.id ? 'Processing...' : 'Reactivate'}
                              </Button>
                            )}
                          </>
                        )}
                        {member.id === user.id && (
                          <span className="text-xs text-gray-500 px-2 py-1">You</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}

export default OrganizationMembersPage