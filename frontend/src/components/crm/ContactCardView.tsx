'use client'

import React, { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { 
  Building, 
  Mail, 
  Phone, 
  MapPin, 
  Edit3, 
  Check, 
  X,
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

interface ContactCardViewProps {
  contacts: Contact[]
  onContactUpdate: (contactId: string, updatedContact: Partial<Contact>) => Promise<void>
  onContactDelete: (contactId: string) => Promise<void>
}

const ContactCardView: React.FC<ContactCardViewProps> = ({ contacts, onContactUpdate, onContactDelete }) => {
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
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {contacts.map((contact) => (
        <Card key={contact.id} className="hover:shadow-md transition-shadow">
          <CardContent className="p-4">
            {editingId === contact.id ? (
              <div className="space-y-3">
                <div>
                  <Input
                    value={editForm.business_name || ''}
                    onChange={(e) => handleFieldChange('business_name', e.target.value)}
                    placeholder="Business Name"
                    className="font-semibold"
                  />
                </div>
                
                <div className="flex items-center gap-2">
                  <Select 
                    value={editForm.status || contact.status} 
                    onValueChange={(value) => handleFieldChange('status', value)}
                  >
                    <SelectTrigger className="w-32">
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
                </div>

                <div className="space-y-2">
                  <Input
                    value={editForm.contact_name || ''}
                    onChange={(e) => handleFieldChange('contact_name', e.target.value)}
                    placeholder="Contact Name"
                  />
                  <Input
                    value={editForm.contact_role || ''}
                    onChange={(e) => handleFieldChange('contact_role', e.target.value)}
                    placeholder="Role"
                  />
                  <Input
                    value={editForm.contact_email || ''}
                    onChange={(e) => handleFieldChange('contact_email', e.target.value)}
                    placeholder="Email"
                    type="email"
                  />
                  <Input
                    value={editForm.phone || ''}
                    onChange={(e) => handleFieldChange('phone', e.target.value)}
                    placeholder="Phone"
                  />
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      value={editForm.city || ''}
                      onChange={(e) => handleFieldChange('city', e.target.value)}
                      placeholder="City"
                    />
                    <Input
                      value={editForm.state || ''}
                      onChange={(e) => handleFieldChange('state', e.target.value)}
                      placeholder="State"
                    />
                  </div>
                  <Textarea
                    value={editForm.notes || ''}
                    onChange={(e) => handleFieldChange('notes', e.target.value)}
                    placeholder="Notes"
                    rows={2}
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={handleEditCancel}
                    disabled={isSubmitting}
                  >
                    <X className="h-3 w-3 mr-1" />
                    Cancel
                  </Button>
                  <Button 
                    size="sm" 
                    onClick={handleEditSave}
                    disabled={isSubmitting}
                  >
                    <Check className="h-3 w-3 mr-1" />
                    {isSubmitting ? 'Saving...' : 'Save'}
                  </Button>
                </div>
              </div>
            ) : (
              <div>
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2 flex-1">
                    <Building className="h-4 w-4 text-gray-400 flex-shrink-0" />
                    <h3 className="font-semibold text-gray-900 truncate">{contact.business_name}</h3>
                  </div>
                  <div className="flex gap-1 flex-shrink-0">
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
                </div>

                <div className="mb-3">
                  <Badge variant={getStatusBadgeVariant(contact.status)}>
                    {formatStatus(contact.status)}
                  </Badge>
                </div>

                <div className="space-y-2 text-sm text-gray-600">
                  <div className="font-medium text-gray-900">{contact.contact_name}</div>
                  
                  {contact.contact_role && (
                    <div className="text-gray-600">{contact.contact_role}</div>
                  )}
                  
                  {contact.contact_email && (
                    <div className="flex items-center gap-2">
                      <Mail className="h-3 w-3 flex-shrink-0" />
                      <span className="truncate">{contact.contact_email}</span>
                    </div>
                  )}
                  
                  {contact.phone && (
                    <div className="flex items-center gap-2">
                      <Phone className="h-3 w-3 flex-shrink-0" />
                      <span>{contact.phone}</span>
                    </div>
                  )}
                  
                  {(contact.city || contact.state) && (
                    <div className="flex items-center gap-2">
                      <MapPin className="h-3 w-3 flex-shrink-0" />
                      <span>{[contact.city, contact.state].filter(Boolean).join(', ')}</span>
                    </div>
                  )}
                  
                  {contact.notes && (
                    <div className="text-xs text-gray-500 line-clamp-2 mt-2">
                      {contact.notes}
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between pt-3 mt-3 border-t border-gray-100 text-xs text-gray-500">
                  <div className="flex items-center gap-1">
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
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export default ContactCardView