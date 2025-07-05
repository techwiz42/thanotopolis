'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { 
  Edit3, 
  Check, 
  X,
  Mail,
  Phone,
  Building,
  Calendar,
  MessageSquare,
  Trash2,
  Eye
} from 'lucide-react'

interface Contact {
  id: string
  business_name: string
  contact_name: string
  contact_email?: string
  contact_role?: string
  phone?: string
  city?: string
  state?: string
  status: string
  notes?: string
  created_at: string
  interaction_count: number
  last_interaction_date?: string
  created_by_user_id?: string
}

interface User {
  id: string
  email: string
  name: string
  role: string
  tenant_id?: string
}

interface ContactTableViewProps {
  contacts: Contact[]
  onContactUpdate: (contactId: string, updatedContact: Partial<Contact>) => Promise<void>
  onContactDelete: (contactId: string) => Promise<void>
  currentUser: User
}

const ContactTableView: React.FC<ContactTableViewProps> = ({ contacts, onContactUpdate, onContactDelete, currentUser }) => {
  const router = useRouter()
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState<Partial<Contact>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  const getStatusBadgeVariant = (status: string) => {
    switch (status.toLowerCase()) {
      case 'customer':
      case 'closed_won':
        return 'default'
      case 'prospect':
      case 'qualified':
        return 'secondary'
      case 'lead':
        return 'outline'
      case 'inactive':
      case 'closed_lost':
        return 'destructive'
      default:
        return 'outline'
    }
  }

  const formatStatus = (status: string) => {
    return status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const handleEditStart = (contact: Contact) => {
    setEditingId(contact.id)
    setEditForm(contact)
  }

  const handleEditCancel = () => {
    setEditingId(null)
    setEditForm({})
  }

  const handleEditSave = async () => {
    if (!editingId || !editForm) return
    
    setIsSubmitting(true)
    try {
      await onContactUpdate(editingId, editForm)
      setEditingId(null)
      setEditForm({})
    } catch (error) {
      console.error('Error updating contact:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleFieldChange = (field: keyof Contact, value: string) => {
    setEditForm(prev => ({ ...prev, [field]: value }))
  }

  const handleDelete = async (contactId: string) => {
    if (window.confirm('Are you sure you want to delete this contact? This action cannot be undone.')) {
      try {
        await onContactDelete(contactId)
      } catch (error) {
        alert('Failed to delete contact. Please try again.')
      }
    }
  }

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div className="overflow-x-auto max-h-[400px] sm:max-h-[500px] lg:max-h-[600px]">
        <table className="w-full border-collapse min-w-[800px] lg:min-w-full">
          <thead className="sticky top-0 z-10 bg-gray-50 shadow-sm">
            <tr className="border-b border-gray-200">
              <th className="sticky top-0 text-left p-2 sm:p-3 font-medium text-gray-900 text-xs sm:text-sm bg-gray-50">Business</th>
              <th className="sticky top-0 text-left p-2 sm:p-3 font-medium text-gray-900 text-xs sm:text-sm hidden sm:table-cell bg-gray-50">Contact</th>
              <th className="sticky top-0 text-left p-2 sm:p-3 font-medium text-gray-900 text-xs sm:text-sm hidden md:table-cell bg-gray-50">Email</th>
              <th className="sticky top-0 text-left p-2 sm:p-3 font-medium text-gray-900 text-xs sm:text-sm hidden lg:table-cell bg-gray-50">Phone</th>
              <th className="sticky top-0 text-left p-2 sm:p-3 font-medium text-gray-900 text-xs sm:text-sm hidden xl:table-cell bg-gray-50">Location</th>
              <th className="sticky top-0 text-left p-2 sm:p-3 font-medium text-gray-900 text-xs sm:text-sm bg-gray-50">Status</th>
              <th className="sticky top-0 text-left p-2 sm:p-3 font-medium text-gray-900 text-xs sm:text-sm hidden lg:table-cell bg-gray-50">Activity</th>
              <th className="sticky top-0 text-left p-2 sm:p-3 font-medium text-gray-900 text-xs sm:text-sm bg-gray-50">Actions</th>
            </tr>
          </thead>
        <tbody>
          {contacts.map((contact) => (
            <tr key={contact.id} className="border-b border-gray-100 hover:bg-gray-50">
              {editingId === contact.id ? (
                <>
                  <td className="p-2 sm:p-3">
                    <Input
                      value={editForm.business_name || ''}
                      onChange={(e) => handleFieldChange('business_name', e.target.value)}
                      placeholder="Business Name"
                      className="w-full min-w-0"
                    />
                  </td>
                  <td className="p-2 sm:p-3 hidden sm:table-cell">
                    <div className="space-y-1">
                      <Input
                        value={editForm.contact_name || ''}
                        onChange={(e) => handleFieldChange('contact_name', e.target.value)}
                        placeholder="Contact Name"
                        className="w-full min-w-0"
                      />
                      <Input
                        value={editForm.contact_role || ''}
                        onChange={(e) => handleFieldChange('contact_role', e.target.value)}
                        placeholder="Role"
                        className="w-full min-w-0 text-xs"
                      />
                    </div>
                  </td>
                  <td className="p-2 sm:p-3 hidden md:table-cell">
                    <Input
                      value={editForm.contact_email || ''}
                      onChange={(e) => handleFieldChange('contact_email', e.target.value)}
                      placeholder="Email"
                      type="email"
                      className="w-full min-w-0"
                    />
                  </td>
                  <td className="p-2 sm:p-3 hidden lg:table-cell">
                    <Input
                      value={editForm.phone || ''}
                      onChange={(e) => handleFieldChange('phone', e.target.value)}
                      placeholder="Phone"
                      className="w-full min-w-[120px]"
                    />
                  </td>
                  <td className="p-2 sm:p-3 hidden xl:table-cell">
                    <div className="space-y-1">
                      <Input
                        value={editForm.city || ''}
                        onChange={(e) => handleFieldChange('city', e.target.value)}
                        placeholder="City"
                        className="w-full min-w-0"
                      />
                      <Input
                        value={editForm.state || ''}
                        onChange={(e) => handleFieldChange('state', e.target.value)}
                        placeholder="State"
                        className="w-full min-w-0"
                      />
                    </div>
                  </td>
                  <td className="p-2 sm:p-3">
                    <Select 
                      value={editForm.status || contact.status} 
                      onValueChange={(value) => handleFieldChange('status', value)}
                    >
                      <SelectTrigger className="w-full min-w-0">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="lead">Lead</SelectItem>
                        <SelectItem value="prospect">Prospect</SelectItem>
                        <SelectItem value="customer">Customer</SelectItem>
                        <SelectItem value="qualified">Qualified</SelectItem>
                        <SelectItem value="closed_won">Closed Won</SelectItem>
                        <SelectItem value="closed_lost">Closed Lost</SelectItem>
                        <SelectItem value="inactive">Inactive</SelectItem>
                      </SelectContent>
                    </Select>
                  </td>
                  <td className="p-2 sm:p-3 hidden lg:table-cell">
                    <div className="text-xs text-gray-500">
                      <div className="flex items-center gap-1 mb-1">
                        <MessageSquare className="h-3 w-3" />
                        {contact.interaction_count}
                      </div>
                      {contact.last_interaction_date && (
                        <div className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {new Date(contact.last_interaction_date).toLocaleDateString()}
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="p-2 sm:p-3">
                    <div className="flex gap-1">
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        onClick={handleEditCancel}
                        disabled={isSubmitting}
                        className="h-8 w-8 p-0"
                      >
                        <X className="h-3 w-3" />
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        onClick={handleEditSave}
                        disabled={isSubmitting}
                        className="h-8 w-8 p-0"
                      >
                        <Check className="h-3 w-3" />
                      </Button>
                    </div>
                  </td>
                </>
              ) : (
                <>
                  <td className="p-2 sm:p-3">
                    <div className="flex items-center gap-2">
                      <Building className="h-4 w-4 text-gray-400 flex-shrink-0" />
                      <span className="font-medium text-gray-900 truncate text-xs sm:text-sm">{contact.business_name}</span>
                    </div>
                    <div className="sm:hidden mt-1 space-y-1">
                      <div className="text-xs text-gray-600">{contact.contact_name}</div>
                      {contact.contact_email && (
                        <div className="text-xs text-gray-500 truncate">{contact.contact_email}</div>
                      )}
                      {contact.phone && (
                        <div className="text-xs text-gray-500">{contact.phone}</div>
                      )}
                    </div>
                  </td>
                  <td className="p-2 sm:p-3 hidden sm:table-cell">
                    <div>
                      <div className="font-medium text-gray-900 text-sm">{contact.contact_name}</div>
                      {contact.contact_role && (
                        <div className="text-xs sm:text-sm text-gray-600">{contact.contact_role}</div>
                      )}
                    </div>
                  </td>
                  <td className="p-2 sm:p-3 hidden md:table-cell">
                    {contact.contact_email ? (
                      <div className="flex items-center gap-2">
                        <Mail className="h-3 w-3 text-gray-400 flex-shrink-0" />
                        <span className="text-xs sm:text-sm text-gray-900 truncate">{contact.contact_email}</span>
                      </div>
                    ) : (
                      <span className="text-gray-400 text-xs sm:text-sm">-</span>
                    )}
                  </td>
                  <td className="p-2 sm:p-3 hidden lg:table-cell">
                    {contact.phone ? (
                      <div className="flex items-center gap-2">
                        <Phone className="h-3 w-3 text-gray-400 flex-shrink-0" />
                        <span className="text-xs sm:text-sm text-gray-900">{contact.phone}</span>
                      </div>
                    ) : (
                      <span className="text-gray-400 text-xs sm:text-sm">-</span>
                    )}
                  </td>
                  <td className="p-2 sm:p-3 hidden xl:table-cell">
                    {(contact.city || contact.state) ? (
                      <span className="text-xs sm:text-sm text-gray-900">
                        {[contact.city, contact.state].filter(Boolean).join(', ')}
                      </span>
                    ) : (
                      <span className="text-gray-400 text-xs sm:text-sm">-</span>
                    )}
                  </td>
                  <td className="p-2 sm:p-3">
                    <Badge variant={getStatusBadgeVariant(contact.status)}>
                      {formatStatus(contact.status)}
                    </Badge>
                  </td>
                  <td className="p-2 sm:p-3 hidden lg:table-cell">
                    <div className="text-xs text-gray-500">
                      <div className="flex items-center gap-1 mb-1">
                        <MessageSquare className="h-3 w-3" />
                        <span>{contact.interaction_count} interactions</span>
                      </div>
                      {contact.last_interaction_date && (
                        <div className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          <span>{new Date(contact.last_interaction_date).toLocaleDateString()}</span>
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="p-2 sm:p-3">
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => router.push(`/organizations/crm/contacts/${contact.id}`)}
                        className="h-8 w-8 p-0"
                        title="View details"
                      >
                        <Eye className="h-3 w-3" />
                      </Button>
                      {(currentUser.role === 'admin' || currentUser.role === 'super_admin' || currentUser.role === 'org_admin' || contact.created_by_user_id === currentUser.id) && (
                        <>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleEditStart(contact)}
                            className="h-8 w-8 p-0"
                            title="Edit contact"
                          >
                            <Edit3 className="h-3 w-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(contact.id)}
                            className="h-8 w-8 p-0 text-red-600 hover:text-red-700 hover:bg-red-50"
                            title="Delete contact"
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </>
                      )}
                    </div>
                  </td>
                </>
              )}
            </tr>
          ))}
        </tbody>
        </table>
        
        {contacts.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            No contacts found
          </div>
        )}
      </div>
    </div>
  )
}

export default ContactTableView