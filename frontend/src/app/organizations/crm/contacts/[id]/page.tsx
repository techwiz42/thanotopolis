'use client'

import React, { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useRouter, useParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { 
  ArrowLeft, 
  Building, 
  Mail, 
  Phone, 
  MapPin, 
  Calendar, 
  MessageSquare,
  User,
  Globe,
  Edit,
  Clock,
  Send,
  PhoneCall,
  Users,
  FileText,
  CheckSquare
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
  address?: string
  website?: string
  status: string
  notes?: string
  created_at: string
  interaction_count: number
  last_interaction_date?: string
  billing_status?: string
  subscription_status?: string
  // Cemetery-specific fields
  ethnic_orientation?: string
  preferred_language?: string
  secondary_language?: string
  family_name?: string
  relationship_to_deceased?: string
  deceased_name?: string
  date_of_birth?: string
  date_of_death?: string
  service_type?: string
  service_date?: string
  service_location?: string
  plot_number?: string
  plot_type?: string
  contract_amount_cents?: number
  amount_paid_cents?: number
  balance_due_cents?: number
  payment_plan?: string
  payment_status?: string
  special_requests?: string
  religious_preferences?: string
  veteran_status?: string
}

interface ContactInteraction {
  id: string
  interaction_type: string
  subject?: string
  content: string
  interaction_date: string
  user_name: string
  metadata?: Record<string, any>
}

const INTERACTION_ICONS = {
  email: Mail,
  phone_call: PhoneCall,
  meeting: Users,
  note: FileText,
  task: CheckSquare,
  follow_up: Clock
}

const INTERACTION_COLORS = {
  email: 'text-blue-600 bg-blue-50',
  phone_call: 'text-green-600 bg-green-50',
  meeting: 'text-purple-600 bg-purple-50',
  note: 'text-gray-600 bg-gray-50',
  task: 'text-orange-600 bg-orange-50',
  follow_up: 'text-yellow-600 bg-yellow-50'
}

export default function ContactDetailPage() {
  const { token, user, organization, isLoading } = useAuth()
  const router = useRouter()
  const params = useParams()
  const contactId = params.id as string

  const [contact, setContact] = useState<Contact | null>(null)
  const [interactions, setInteractions] = useState<ContactInteraction[]>([])
  const [contactLoading, setContactLoading] = useState(true)
  const [interactionsLoading, setInteractionsLoading] = useState(true)

  // Fetch contact details
  useEffect(() => {
    const fetchContact = async () => {
      if (!token || !organization || !contactId) return

      try {
        const response = await fetch(`/api/crm/contacts/${contactId}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'X-Tenant-ID': organization,
            'Content-Type': 'application/json'
          }
        })

        if (response.ok) {
          const data = await response.json()
          setContact(data)
        } else {
          console.error('Failed to fetch contact')
          router.push('/organizations/crm')
        }
      } catch (error) {
        console.error('Error fetching contact:', error)
        router.push('/organizations/crm')
      } finally {
        setContactLoading(false)
      }
    }

    fetchContact()
  }, [token, organization, contactId, router])

  // Fetch contact interactions
  useEffect(() => {
    const fetchInteractions = async () => {
      if (!token || !organization || !contactId) return

      try {
        const response = await fetch(`/api/crm/contacts/${contactId}/interactions`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'X-Tenant-ID': organization,
            'Content-Type': 'application/json'
          }
        })

        if (response.ok) {
          const data = await response.json()
          setInteractions(data)
        } else {
          console.error('Failed to fetch interactions')
        }
      } catch (error) {
        console.error('Error fetching interactions:', error)
      } finally {
        setInteractionsLoading(false)
      }
    }

    fetchInteractions()
  }, [token, organization, contactId])

  // Check authentication
  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/login')
    }
  }, [user, isLoading, router])

  if (isLoading || contactLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-pulse">Loading contact details...</div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  if (!contact) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold mb-2">Contact not found</h2>
          <Button onClick={() => router.push('/organizations/crm')}>
            Return to CRM
          </Button>
        </div>
      </div>
    )
  }

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

  const formatInteractionType = (type: string) => {
    return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <Button variant="outline" onClick={() => router.push('/organizations/crm')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to CRM
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{contact.contact_name}</h1>
            <p className="text-gray-600">{contact.business_name}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Contact Information */}
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center">
                    <User className="h-5 w-5 mr-2" />
                    Contact Information
                  </CardTitle>
                  <Button variant="outline" size="sm">
                    <Edit className="h-4 w-4 mr-2" />
                    Edit
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="flex items-center text-sm text-gray-600 mb-1">
                    <Building className="h-4 w-4 mr-2" />
                    Business
                  </div>
                  <p className="font-medium">{contact.business_name}</p>
                </div>

                <div>
                  <div className="flex items-center text-sm text-gray-600 mb-1">
                    <User className="h-4 w-4 mr-2" />
                    Name & Role
                  </div>
                  <p className="font-medium">{contact.contact_name}</p>
                  {contact.contact_role && (
                    <p className="text-sm text-gray-600">{contact.contact_role}</p>
                  )}
                </div>

                {contact.contact_email && (
                  <div>
                    <div className="flex items-center text-sm text-gray-600 mb-1">
                      <Mail className="h-4 w-4 mr-2" />
                      Email
                    </div>
                    <p className="font-medium">{contact.contact_email}</p>
                  </div>
                )}

                {contact.phone && (
                  <div>
                    <div className="flex items-center text-sm text-gray-600 mb-1">
                      <Phone className="h-4 w-4 mr-2" />
                      Phone
                    </div>
                    <p className="font-medium">{contact.phone}</p>
                  </div>
                )}

                {(contact.city || contact.state || contact.address) && (
                  <div>
                    <div className="flex items-center text-sm text-gray-600 mb-1">
                      <MapPin className="h-4 w-4 mr-2" />
                      Location
                    </div>
                    {contact.address && <p className="font-medium">{contact.address}</p>}
                    {(contact.city || contact.state) && (
                      <p className="font-medium">
                        {[contact.city, contact.state].filter(Boolean).join(', ')}
                      </p>
                    )}
                  </div>
                )}

                {contact.website && (
                  <div>
                    <div className="flex items-center text-sm text-gray-600 mb-1">
                      <Globe className="h-4 w-4 mr-2" />
                      Website
                    </div>
                    <p className="font-medium">{contact.website}</p>
                  </div>
                )}

                <Separator />

                <div>
                  <div className="flex items-center text-sm text-gray-600 mb-2">
                    Status
                  </div>
                  <Badge variant={getStatusBadgeVariant(contact.status)}>
                    {formatStatus(contact.status)}
                  </Badge>
                </div>

                <div>
                  <div className="flex items-center text-sm text-gray-600 mb-1">
                    <Calendar className="h-4 w-4 mr-2" />
                    Created
                  </div>
                  <p className="font-medium">{new Date(contact.created_at).toLocaleDateString()}</p>
                </div>

                {contact.notes && (
                  <div>
                    <div className="flex items-center text-sm text-gray-600 mb-1">
                      <FileText className="h-4 w-4 mr-2" />
                      Notes
                    </div>
                    <p className="text-sm bg-gray-50 p-3 rounded border">{contact.notes}</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Cemetery Information */}
            {(contact.deceased_name || contact.plot_number || contact.service_type || 
              contact.ethnic_orientation || contact.contract_amount_cents !== null ||
              contact.religious_preferences || contact.special_requests) && (
              <Card className="mt-6">
                <CardHeader>
                  <CardTitle className="text-lg">Cemetery Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Deceased Information */}
                  {(contact.deceased_name || contact.date_of_birth || contact.date_of_death) && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Deceased Information</h4>
                      {contact.deceased_name && (
                        <p className="text-sm"><span className="text-gray-600">Name:</span> {contact.deceased_name}</p>
                      )}
                      {contact.date_of_birth && (
                        <p className="text-sm"><span className="text-gray-600">Date of Birth:</span> {new Date(contact.date_of_birth).toLocaleDateString()}</p>
                      )}
                      {contact.date_of_death && (
                        <p className="text-sm"><span className="text-gray-600">Date of Death:</span> {new Date(contact.date_of_death).toLocaleDateString()}</p>
                      )}
                      {contact.relationship_to_deceased && (
                        <p className="text-sm"><span className="text-gray-600">Relationship:</span> {contact.relationship_to_deceased}</p>
                      )}
                    </div>
                  )}

                  {/* Cultural & Language */}
                  {(contact.ethnic_orientation || contact.preferred_language || contact.secondary_language) && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Cultural Preferences</h4>
                      {contact.ethnic_orientation && (
                        <p className="text-sm"><span className="text-gray-600">Ethnic Orientation:</span> {contact.ethnic_orientation}</p>
                      )}
                      {contact.preferred_language && (
                        <p className="text-sm"><span className="text-gray-600">Preferred Language:</span> {contact.preferred_language}</p>
                      )}
                      {contact.secondary_language && (
                        <p className="text-sm"><span className="text-gray-600">Secondary Language:</span> {contact.secondary_language}</p>
                      )}
                    </div>
                  )}

                  {/* Service Information */}
                  {(contact.service_type || contact.service_date || contact.service_location) && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Service Details</h4>
                      {contact.service_type && (
                        <p className="text-sm"><span className="text-gray-600">Type:</span> {contact.service_type}</p>
                      )}
                      {contact.service_date && (
                        <p className="text-sm"><span className="text-gray-600">Date:</span> {new Date(contact.service_date).toLocaleDateString()}</p>
                      )}
                      {contact.service_location && (
                        <p className="text-sm"><span className="text-gray-600">Location:</span> {contact.service_location}</p>
                      )}
                    </div>
                  )}

                  {/* Plot Information */}
                  {(contact.plot_number || contact.plot_type) && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Plot Details</h4>
                      {contact.plot_number && (
                        <p className="text-sm"><span className="text-gray-600">Plot Number:</span> {contact.plot_number}</p>
                      )}
                      {contact.plot_type && (
                        <p className="text-sm"><span className="text-gray-600">Plot Type:</span> {contact.plot_type}</p>
                      )}
                    </div>
                  )}

                  {/* Financial Information */}
                  {(contact.contract_amount_cents !== null || contact.amount_paid_cents !== null || 
                    contact.balance_due_cents !== null || contact.payment_plan || contact.payment_status) && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Financial Details</h4>
                      {contact.contract_amount_cents !== null && contact.contract_amount_cents !== undefined && (
                        <p className="text-sm"><span className="text-gray-600">Contract Amount:</span> ${(contact.contract_amount_cents / 100).toFixed(2)}</p>
                      )}
                      {contact.amount_paid_cents !== null && contact.amount_paid_cents !== undefined && (
                        <p className="text-sm"><span className="text-gray-600">Amount Paid:</span> ${(contact.amount_paid_cents / 100).toFixed(2)}</p>
                      )}
                      {contact.balance_due_cents !== null && contact.balance_due_cents !== undefined && (
                        <p className="text-sm"><span className="text-gray-600">Balance Due:</span> ${(contact.balance_due_cents / 100).toFixed(2)}</p>
                      )}
                      {contact.payment_plan && (
                        <p className="text-sm"><span className="text-gray-600">Payment Plan:</span> {contact.payment_plan}</p>
                      )}
                      {contact.payment_status && (
                        <p className="text-sm"><span className="text-gray-600">Payment Status:</span> {contact.payment_status}</p>
                      )}
                    </div>
                  )}

                  {/* Special Preferences */}
                  {(contact.religious_preferences || contact.veteran_status || contact.special_requests) && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Special Preferences</h4>
                      {contact.religious_preferences && (
                        <p className="text-sm"><span className="text-gray-600">Religious Preferences:</span> {contact.religious_preferences}</p>
                      )}
                      {contact.veteran_status && (
                        <p className="text-sm"><span className="text-gray-600">Veteran Status:</span> {contact.veteran_status}</p>
                      )}
                      {contact.special_requests && (
                        <div className="mt-2">
                          <p className="text-sm text-gray-600">Special Requests:</p>
                          <p className="text-sm bg-gray-50 p-2 rounded border mt-1">{contact.special_requests}</p>
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>

          {/* Interaction History */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <MessageSquare className="h-5 w-5 mr-2" />
                  Interaction History ({contact.interaction_count})
                </CardTitle>
              </CardHeader>
              <CardContent>
                {interactionsLoading ? (
                  <div className="text-center py-8">
                    <div className="animate-pulse">Loading interactions...</div>
                  </div>
                ) : interactions.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <MessageSquare className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No interactions yet</h3>
                    <p className="text-gray-600">Start engaging with this contact to see interaction history here.</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {interactions.map((interaction) => {
                      const IconComponent = INTERACTION_ICONS[interaction.interaction_type as keyof typeof INTERACTION_ICONS] || MessageSquare
                      const colorClass = INTERACTION_COLORS[interaction.interaction_type as keyof typeof INTERACTION_COLORS] || 'text-gray-600 bg-gray-50'
                      
                      return (
                        <div key={interaction.id} className="flex gap-4 p-4 border border-gray-200 rounded-lg">
                          <div className={`flex items-center justify-center w-10 h-10 rounded-full flex-shrink-0 ${colorClass}`}>
                            <IconComponent className="h-5 w-5" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between mb-1">
                              <div className="flex items-center gap-2">
                                <h4 className="font-medium text-gray-900">
                                  {formatInteractionType(interaction.interaction_type)}
                                </h4>
                                {interaction.metadata?.bulk_email && (
                                  <Badge variant="outline" className="text-xs">Bulk Email</Badge>
                                )}
                              </div>
                              <div className="flex items-center text-xs text-gray-500">
                                <Clock className="h-3 w-3 mr-1" />
                                {new Date(interaction.interaction_date).toLocaleString()}
                              </div>
                            </div>
                            {interaction.subject && (
                              <p className="font-medium text-sm text-gray-700 mb-1">{interaction.subject}</p>
                            )}
                            <p className="text-sm text-gray-600 mb-2">{interaction.content}</p>
                            <div className="flex items-center text-xs text-gray-500">
                              <User className="h-3 w-3 mr-1" />
                              by {interaction.user_name}
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}