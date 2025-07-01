'use client'

import React, { useState } from 'react'
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
  Trash2
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
}

interface ContactTableViewProps {
  contacts: Contact[]
  onContactUpdate: (contactId: string, updatedContact: Partial<Contact>) => Promise<void>
  onContactDelete: (contactId: string) => Promise<void>
}

const ContactTableView: React.FC<ContactTableViewProps> = ({ contacts, onContactUpdate, onContactDelete }) => {
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
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50">
            <th className="text-left p-3 font-medium text-gray-900">Business</th>
            <th className="text-left p-3 font-medium text-gray-900">Contact</th>
            <th className="text-left p-3 font-medium text-gray-900">Email</th>
            <th className="text-left p-3 font-medium text-gray-900">Phone</th>
            <th className="text-left p-3 font-medium text-gray-900">Location</th>
            <th className="text-left p-3 font-medium text-gray-900">Status</th>
            <th className="text-left p-3 font-medium text-gray-900">Activity</th>
            <th className="text-left p-3 font-medium text-gray-900">Actions</th>
          </tr>
        </thead>
        <tbody>
          {contacts.map((contact) => (
            <tr key={contact.id} className="border-b border-gray-100 hover:bg-gray-50">
              {editingId === contact.id ? (
                <>
                  <td className="p-3">
                    <Input
                      value={editForm.business_name || ''}
                      onChange={(e) => handleFieldChange('business_name', e.target.value)}
                      placeholder="Business Name"
                      className="w-full min-w-[150px]"
                    />
                  </td>
                  <td className="p-3">
                    <div className="space-y-1">
                      <Input
                        value={editForm.contact_name || ''}
                        onChange={(e) => handleFieldChange('contact_name', e.target.value)}
                        placeholder="Contact Name"
                        className="w-full min-w-[120px]"
                      />
                      <Input
                        value={editForm.contact_role || ''}
                        onChange={(e) => handleFieldChange('contact_role', e.target.value)}
                        placeholder="Role"
                        className="w-full min-w-[120px] text-xs"
                      />
                    </div>
                  </td>
                  <td className="p-3">
                    <Input
                      value={editForm.contact_email || ''}
                      onChange={(e) => handleFieldChange('contact_email', e.target.value)}
                      placeholder="Email"
                      type="email"
                      className="w-full min-w-[180px]"
                    />
                  </td>
                  <td className="p-3">
                    <Input
                      value={editForm.phone || ''}
                      onChange={(e) => handleFieldChange('phone', e.target.value)}
                      placeholder="Phone"
                      className="w-full min-w-[120px]"
                    />
                  </td>
                  <td className="p-3">
                    <div className="space-y-1">
                      <Input
                        value={editForm.city || ''}
                        onChange={(e) => handleFieldChange('city', e.target.value)}
                        placeholder="City"
                        className="w-full min-w-[100px]"
                      />
                      <Input
                        value={editForm.state || ''}
                        onChange={(e) => handleFieldChange('state', e.target.value)}
                        placeholder="State"
                        className="w-full min-w-[100px]"
                      />
                    </div>
                  </td>
                  <td className="p-3">
                    <Select 
                      value={editForm.status || contact.status} 
                      onValueChange={(value) => handleFieldChange('status', value)}
                    >
                      <SelectTrigger className="w-full min-w-[120px]">
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
                  <td className="p-3">
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
                  <td className="p-3">
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
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      <Building className="h-4 w-4 text-gray-400 flex-shrink-0" />
                      <span className="font-medium text-gray-900 truncate">{contact.business_name}</span>
                    </div>
                  </td>
                  <td className="p-3">
                    <div>
                      <div className="font-medium text-gray-900">{contact.contact_name}</div>
                      {contact.contact_role && (
                        <div className="text-sm text-gray-600">{contact.contact_role}</div>
                      )}
                    </div>
                  </td>
                  <td className="p-3">
                    {contact.contact_email ? (
                      <div className="flex items-center gap-2">
                        <Mail className="h-3 w-3 text-gray-400 flex-shrink-0" />
                        <span className="text-sm text-gray-900 truncate">{contact.contact_email}</span>
                      </div>
                    ) : (
                      <span className="text-gray-400 text-sm">-</span>
                    )}
                  </td>
                  <td className="p-3">
                    {contact.phone ? (
                      <div className="flex items-center gap-2">
                        <Phone className="h-3 w-3 text-gray-400 flex-shrink-0" />
                        <span className="text-sm text-gray-900">{contact.phone}</span>
                      </div>
                    ) : (
                      <span className="text-gray-400 text-sm">-</span>
                    )}
                  </td>
                  <td className="p-3">
                    {(contact.city || contact.state) ? (
                      <span className="text-sm text-gray-900">
                        {[contact.city, contact.state].filter(Boolean).join(', ')}
                      </span>
                    ) : (
                      <span className="text-gray-400 text-sm">-</span>
                    )}
                  </td>
                  <td className="p-3">
                    <Badge variant={getStatusBadgeVariant(contact.status)}>
                      {formatStatus(contact.status)}
                    </Badge>
                  </td>
                  <td className="p-3">
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
                  <td className="p-3">
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleEditStart(contact)}
                        className="h-8 w-8 p-0"
                      >
                        <Edit3 className="h-3 w-3" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(contact.id)}
                        className="h-8 w-8 p-0 text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
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
  )
}

export default ContactTableView