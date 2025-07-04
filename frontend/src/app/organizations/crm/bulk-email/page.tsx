'use client'

import React, { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Textarea } from '@/components/ui/textarea'
import { 
  Mail, 
  ArrowLeft, 
  Search, 
  Filter, 
  Send,
  FileText,
  Users,
  CheckSquare,
  Square,
  AlertCircle,
  CheckCircle,
  Eye,
  Settings
} from 'lucide-react'

interface EmailTemplate {
  id: string
  name: string
  subject: string
  html_content: string
  variables: string[]
  is_active: boolean
  created_at: string
}

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

interface PaginatedContactsResponse {
  items: Contact[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

interface BulkEmailResult {
  template_id: string
  total_contacts: number
  successful_sends: number
  failed_sends: number
  errors: Array<{
    contact_id: string
    contact_email: string
    error: string
  }>
}

const SEARCH_FIELDS = [
  { value: 'business_name', label: 'Business Name' },
  { value: 'contact_name', label: 'Contact Name' },
  { value: 'contact_email', label: 'Email' },
  { value: 'contact_role', label: 'Role' },
  { value: 'phone', label: 'Phone' },
  { value: 'city', label: 'City' },
  { value: 'state', label: 'State' },
  { value: 'notes', label: 'Notes' }
]

export default function BulkEmailPage() {
  const { token, user, organization, isLoading } = useAuth()
  const router = useRouter()
  
  // Organization data
  const [organizationName, setOrganizationName] = useState<string>('Your Organization')
  
  // Step management
  const [currentStep, setCurrentStep] = useState<'template' | 'contacts' | 'send' | 'results'>('template')
  
  // Template selection
  const [templates, setTemplates] = useState<EmailTemplate[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<EmailTemplate | null>(null)
  const [templatesLoading, setTemplatesLoading] = useState(true)
  
  // Contact selection
  const [contacts, setContacts] = useState<Contact[]>([])
  const [selectedContacts, setSelectedContacts] = useState<Set<string>>(new Set())
  const [allSelected, setAllSelected] = useState(false)
  const [contactsLoading, setContactsLoading] = useState(false)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalContacts, setTotalContacts] = useState(0)
  const [pageSize] = useState(20)
  
  // Search and filters
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedSearchFields, setSelectedSearchFields] = useState<string[]>(['business_name', 'contact_name', 'contact_email'])
  const [statusFilter, setStatusFilter] = useState('all')
  const [emailFilter, setEmailFilter] = useState('all') // all, with_email, without_email
  
  // Send state
  const [additionalVariables, setAdditionalVariables] = useState<Record<string, string>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [sendResults, setSendResults] = useState<BulkEmailResult | null>(null)
  
  // Preview
  const [showPreview, setShowPreview] = useState(false)

  // Fetch organization data
  useEffect(() => {
    const fetchOrganizationData = async () => {
      if (!token || !organization) return

      try {
        const response = await fetch('/api/organizations/current', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'X-Tenant-ID': organization,
            'Content-Type': 'application/json'
          }
        })

        if (response.ok) {
          const orgData = await response.json()
          setOrganizationName(orgData.name || 'Your Organization')
        }
      } catch (error) {
        console.error('Error fetching organization data:', error)
      }
    }

    if (token && organization) {
      fetchOrganizationData()
    }
  }, [token, organization])

  // Fetch templates
  useEffect(() => {
    const fetchTemplates = async () => {
      setTemplatesLoading(true)
      try {
        const response = await fetch('/api/crm/email-templates', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        })

        if (response.ok) {
          const data = await response.json()
          setTemplates(data)
        } else {
          console.error('Failed to fetch templates')
        }
      } catch (error) {
        console.error('Error fetching templates:', error)
      } finally {
        setTemplatesLoading(false)
      }
    }

    if (token) {
      fetchTemplates()
    }
  }, [token])

  // Fetch contacts when step changes or search changes
  useEffect(() => {
    if (currentStep === 'contacts' && token) {
      fetchContacts()
    }
  }, [currentStep, token, searchTerm, selectedSearchFields, statusFilter, emailFilter, currentPage])

  // Check authentication - wait for loading to complete
  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/login')
    }
  }, [user, isLoading, router])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-pulse">Loading...</div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  // Check if user has admin access (matching CRM page access requirements)
  if (user.role !== 'admin' && user.role !== 'super_admin' && user.role !== 'org_admin') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Card className="w-96">
          <CardContent className="p-6 text-center">
            <AlertCircle className="h-12 w-12 mx-auto text-red-500 mb-4" />
            <h2 className="text-xl font-semibold mb-2">Access Denied</h2>
            <p className="text-gray-600">
              You need administrator privileges to access the bulk email feature.
            </p>
            <Button 
              onClick={() => router.push('/organizations/crm')} 
              className="mt-4"
            >
              Return to CRM
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }


  const fetchContacts = async () => {
    if (!token) return
    
    setContactsLoading(true)
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        page_size: pageSize.toString()
      })
      
      if (searchTerm) {
        params.append('search_term', searchTerm)
        params.append('search_fields', selectedSearchFields.join(','))
      }
      
      if (statusFilter !== 'all') {
        params.append('status', statusFilter)
      }
      
      if (emailFilter === 'with_email') {
        params.append('has_email', 'true')
      } else if (emailFilter === 'without_email') {
        params.append('has_email', 'false')
      }
      
      const response = await fetch(`/api/crm/contacts/search?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        const data: PaginatedContactsResponse = await response.json()
        setContacts(data.items)
        setCurrentPage(data.page)
        setTotalPages(data.total_pages)
        setTotalContacts(data.total)
      } else {
        console.error('Failed to fetch contacts')
      }
    } catch (error) {
      console.error('Error fetching contacts:', error)
    } finally {
      setContactsLoading(false)
    }
  }

  const handleSelectTemplate = (template: EmailTemplate) => {
    setSelectedTemplate(template)
    setCurrentStep('contacts')
  }

  const handleContactToggle = (contactId: string) => {
    const newSelected = new Set(selectedContacts)
    if (newSelected.has(contactId)) {
      newSelected.delete(contactId)
    } else {
      newSelected.add(contactId)
    }
    setSelectedContacts(newSelected)
    setAllSelected(newSelected.size === contacts.length)
  }

  const handleSelectAll = () => {
    if (allSelected) {
      setSelectedContacts(new Set())
      setAllSelected(false)
    } else {
      const allIds = contacts.filter(c => c.contact_email).map(c => c.id)
      setSelectedContacts(new Set(allIds))
      setAllSelected(true)
    }
  }

  const handleSearch = () => {
    setCurrentPage(1)
    fetchContacts()
  }

  const goToPage = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page)
    }
  }

  const proceedToSend = () => {
    if (selectedContacts.size === 0) {
      alert('Please select at least one contact')
      return
    }
    setCurrentStep('send')
  }

  const handleSendEmails = async () => {
    if (!selectedTemplate || selectedContacts.size === 0) return
    
    setIsSubmitting(true)
    try {
      const response = await fetch('/api/crm/bulk-email', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          template_id: selectedTemplate.id,
          contact_ids: Array.from(selectedContacts),
          additional_variables: additionalVariables
        })
      })
      
      if (response.ok) {
        const results = await response.json()
        setSendResults(results)
        setCurrentStep('results')
      } else {
        const error = await response.json()
        alert(`Error sending emails: ${error.detail}`)
      }
    } catch (error) {
      console.error('Error sending emails:', error)
      alert('Error sending emails. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const getSelectedContactsWithEmail = () => {
    return contacts.filter(c => selectedContacts.has(c.id) && c.contact_email)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <Button variant="outline" onClick={() => router.push('/organizations/crm')}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to CRM
            </Button>
            <div>
              <h1 className="text-3xl font-bold text-gray-900 flex items-center">
                <Mail className="h-8 w-8 mr-3 text-blue-600" />
                Bulk Email Campaign
              </h1>
              <p className="text-gray-600 mt-1">
                Send personalized emails to multiple contacts using templates
              </p>
            </div>
          </div>
        </div>

        {/* Progress Steps */}
        <div className="flex items-center justify-center mb-8 px-4">
          <div className="flex items-center space-x-2 sm:space-x-4 overflow-x-auto">
            <div className={`flex items-center ${currentStep === 'template' ? 'text-blue-600' : currentStep === 'contacts' || currentStep === 'send' || currentStep === 'results' ? 'text-green-600' : 'text-gray-400'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 ${currentStep === 'template' ? 'border-blue-600 bg-blue-50' : currentStep === 'contacts' || currentStep === 'send' || currentStep === 'results' ? 'border-green-600 bg-green-50' : 'border-gray-300'}`}>
                <FileText className="h-4 w-4" />
              </div>
              <span className="ml-2 font-medium text-xs sm:text-sm">Choose Template</span>
            </div>
            
            <div className={`w-8 sm:w-12 h-0.5 ${currentStep === 'contacts' || currentStep === 'send' || currentStep === 'results' ? 'bg-green-600' : 'bg-gray-300'}`}></div>
            
            <div className={`flex items-center ${currentStep === 'contacts' ? 'text-blue-600' : currentStep === 'send' || currentStep === 'results' ? 'text-green-600' : 'text-gray-400'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 ${currentStep === 'contacts' ? 'border-blue-600 bg-blue-50' : currentStep === 'send' || currentStep === 'results' ? 'border-green-600 bg-green-50' : 'border-gray-300'}`}>
                <Users className="h-4 w-4" />
              </div>
              <span className="ml-2 font-medium text-xs sm:text-sm">Select Contacts</span>
            </div>
            
            <div className={`w-8 sm:w-12 h-0.5 ${currentStep === 'send' || currentStep === 'results' ? 'bg-green-600' : 'bg-gray-300'}`}></div>
            
            <div className={`flex items-center ${currentStep === 'send' ? 'text-blue-600' : currentStep === 'results' ? 'text-green-600' : 'text-gray-400'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 ${currentStep === 'send' ? 'border-blue-600 bg-blue-50' : currentStep === 'results' ? 'border-green-600 bg-green-50' : 'border-gray-300'}`}>
                <Send className="h-4 w-4" />
              </div>
              <span className="ml-2 font-medium text-xs sm:text-sm">Send Campaign</span>
            </div>
          </div>
        </div>

        {/* Step Content */}
        {currentStep === 'template' && (
          <Card>
            <CardHeader>
              <CardTitle>Choose Email Template</CardTitle>
            </CardHeader>
            <CardContent>
              {templatesLoading ? (
                <div className="text-center py-8">
                  <div className="animate-pulse">Loading templates...</div>
                </div>
              ) : templates.length === 0 ? (
                <div className="text-center py-8">
                  <FileText className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No Email Templates</h3>
                  <p className="text-gray-600 mb-4">Create an email template first to send bulk emails.</p>
                  <Button onClick={() => router.push('/organizations/crm/create-template')}>
                    Create Template
                  </Button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {templates.map((template) => (
                    <Card key={template.id} className="border border-gray-200 hover:border-blue-300 transition-colors cursor-pointer" onClick={() => handleSelectTemplate(template)}>
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex-1">
                            <h4 className="font-medium text-gray-900">{template.name}</h4>
                            <p className="text-sm text-gray-600 mt-1">{template.subject}</p>
                          </div>
                          <Badge variant={template.is_active ? 'default' : 'destructive'}>
                            {template.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                        </div>
                        
                        <div className="space-y-2">
                          <div className="text-xs text-gray-500">
                            Variables: {template.variables.length}
                          </div>
                          
                          {template.variables.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {template.variables.slice(0, 3).map((variable) => (
                                <Badge key={variable} variant="outline" className="text-xs">
                                  {variable}
                                </Badge>
                              ))}
                              {template.variables.length > 3 && (
                                <Badge variant="outline" className="text-xs">
                                  +{template.variables.length - 3}
                                </Badge>
                              )}
                            </div>
                          )}
                        </div>
                        
                        <div className="mt-3 pt-3 border-t">
                          <Button className="w-full" size="sm">
                            Select Template
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {currentStep === 'contacts' && (
          <div className="space-y-6">
            {/* Selected Template Info */}
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium">Selected Template: {selectedTemplate?.name}</h3>
                    <p className="text-sm text-gray-600">{selectedTemplate?.subject}</p>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => setCurrentStep('template')}>
                    Change Template
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Search and Filters */}
            <Card>
              <CardHeader>
                <CardTitle>Search and Filter Contacts</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div>
                    <Label>Search Term</Label>
                    <Input
                      placeholder="Enter search term..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                    />
                  </div>
                  
                  <div>
                    <Label>Status Filter</Label>
                    <Select value={statusFilter} onValueChange={setStatusFilter}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Status</SelectItem>
                        <SelectItem value="lead">Lead</SelectItem>
                        <SelectItem value="prospect">Prospect</SelectItem>
                        <SelectItem value="customer">Customer</SelectItem>
                        <SelectItem value="qualified">Qualified</SelectItem>
                        <SelectItem value="closed_won">Closed Won</SelectItem>
                        <SelectItem value="inactive">Inactive</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div>
                    <Label>Email Filter</Label>
                    <Select value={emailFilter} onValueChange={setEmailFilter}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Contacts</SelectItem>
                        <SelectItem value="with_email">With Email Only</SelectItem>
                        <SelectItem value="without_email">Without Email</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div>
                  <Label>Search Fields</Label>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {SEARCH_FIELDS.map((field) => (
                      <div key={field.value} className="flex items-center space-x-2">
                        <Checkbox
                          id={field.value}
                          checked={selectedSearchFields.includes(field.value)}
                          onCheckedChange={(checked) => {
                            if (checked) {
                              setSelectedSearchFields([...selectedSearchFields, field.value])
                            } else {
                              setSelectedSearchFields(selectedSearchFields.filter(f => f !== field.value))
                            }
                          }}
                        />
                        <Label htmlFor={field.value} className="text-sm">{field.label}</Label>
                      </div>
                    ))}
                  </div>
                </div>

                <Button onClick={handleSearch} disabled={contactsLoading}>
                  <Search className="h-4 w-4 mr-2" />
                  {contactsLoading ? 'Searching...' : 'Search Contacts'}
                </Button>
              </CardContent>
            </Card>

            {/* Contacts List */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>
                    Select Contacts ({selectedContacts.size} selected of {contacts.filter(c => c.contact_email).length} with email)
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleSelectAll}
                      disabled={contacts.filter(c => c.contact_email).length === 0}
                    >
                      {allSelected ? (
                        <>
                          <Square className="h-4 w-4 mr-2" />
                          Deselect All
                        </>
                      ) : (
                        <>
                          <CheckSquare className="h-4 w-4 mr-2" />
                          Select All
                        </>
                      )}
                    </Button>
                    <Button
                      onClick={proceedToSend}
                      disabled={selectedContacts.size === 0}
                    >
                      Continue with {selectedContacts.size} contacts
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {contactsLoading ? (
                  <div className="text-center py-8">
                    <div className="animate-pulse">Loading contacts...</div>
                  </div>
                ) : contacts.length === 0 ? (
                  <div className="text-center py-8">
                    <Users className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No Contacts Found</h3>
                    <p className="text-gray-600">Try adjusting your search criteria or create new contacts.</p>
                  </div>
                ) : (
                  <>
                    <div className="space-y-3">
                      {contacts.map((contact) => (
                        <div key={contact.id} className={`p-3 border rounded-lg flex items-center justify-between ${!contact.contact_email ? 'opacity-50 bg-gray-50' : 'hover:bg-gray-50'}`}>
                          <div className="flex items-center space-x-3">
                            <Checkbox
                              checked={selectedContacts.has(contact.id)}
                              onCheckedChange={() => handleContactToggle(contact.id)}
                              disabled={!contact.contact_email}
                            />
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <p className="font-medium text-gray-900">{contact.contact_name}</p>
                                <Badge variant="outline">{contact.status}</Badge>
                                {!contact.contact_email && (
                                  <Badge variant="destructive" className="text-xs">No Email</Badge>
                                )}
                              </div>
                              <p className="text-sm text-gray-600">{contact.business_name}</p>
                              <p className="text-sm text-gray-500">{contact.contact_email || 'No email address'}</p>
                            </div>
                          </div>
                          <div className="text-right text-sm text-gray-500">
                            <p>{contact.city}, {contact.state}</p>
                            <p>{contact.contact_role}</p>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Pagination */}
                    {totalPages > 1 && (
                      <div className="flex items-center justify-between mt-6 pt-4 border-t">
                        <div className="text-sm text-gray-600">
                          Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, totalContacts)} of {totalContacts} contacts
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => goToPage(currentPage - 1)}
                            disabled={currentPage <= 1 || contactsLoading}
                          >
                            Previous
                          </Button>
                          
                          <div className="flex items-center gap-1">
                            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                              let pageNum: number;
                              if (totalPages <= 5) {
                                pageNum = i + 1;
                              } else if (currentPage <= 3) {
                                pageNum = i + 1;
                              } else if (currentPage >= totalPages - 2) {
                                pageNum = totalPages - 4 + i;
                              } else {
                                pageNum = currentPage - 2 + i;
                              }
                              
                              return (
                                <Button
                                  key={pageNum}
                                  variant={pageNum === currentPage ? "default" : "outline"}
                                  size="sm"
                                  onClick={() => goToPage(pageNum)}
                                  disabled={contactsLoading}
                                  className="w-8 h-8 p-0"
                                >
                                  {pageNum}
                                </Button>
                              );
                            })}
                          </div>
                          
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => goToPage(currentPage + 1)}
                            disabled={currentPage >= totalPages || contactsLoading}
                          >
                            Next
                          </Button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {currentStep === 'send' && selectedTemplate && (
          <div className="space-y-6">
            {/* Campaign Summary */}
            <Card>
              <CardHeader>
                <CardTitle>Campaign Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div>
                    <Label className="text-sm font-medium">Template</Label>
                    <p className="text-lg font-semibold">{selectedTemplate.name}</p>
                    <p className="text-sm text-gray-600">{selectedTemplate.subject}</p>
                  </div>
                  <div>
                    <Label className="text-sm font-medium">Recipients</Label>
                    <p className="text-lg font-semibold">{getSelectedContactsWithEmail().length} contacts</p>
                    <p className="text-sm text-gray-600">With valid email addresses</p>
                  </div>
                  <div>
                    <Label className="text-sm font-medium">Variables</Label>
                    <p className="text-lg font-semibold">{selectedTemplate.variables.length} template variables</p>
                    <p className="text-sm text-gray-600">Will be personalized for each contact</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Additional Variables */}
            {selectedTemplate.variables.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Additional Variables (Optional)</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-600 mb-4">
                    Override or add custom values for template variables. Leave blank to use default contact data.
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {selectedTemplate.variables.map((variable) => (
                      <div key={variable}>
                        <Label htmlFor={variable}>{variable}</Label>
                        <Input
                          id={variable}
                          placeholder={`Default from contact data`}
                          value={additionalVariables[variable] || ''}
                          onChange={(e) => setAdditionalVariables({
                            ...additionalVariables,
                            [variable]: e.target.value
                          })}
                        />
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Preview and Send */}
            <Card>
              <CardHeader>
                <CardTitle>Review and Send</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-4">
                  <Button variant="outline" onClick={() => setShowPreview(true)}>
                    <Eye className="h-4 w-4 mr-2" />
                    Preview Email
                  </Button>
                  <Button variant="outline" onClick={() => setCurrentStep('contacts')}>
                    <Users className="h-4 w-4 mr-2" />
                    Modify Recipients
                  </Button>
                </div>

                <div className="pt-4 border-t">
                  <Button
                    onClick={handleSendEmails}
                    disabled={isSubmitting}
                    className="w-full"
                    size="lg"
                  >
                    {isSubmitting ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Sending Emails...
                      </>
                    ) : (
                      <>
                        <Send className="h-4 w-4 mr-2" />
                        Send to {getSelectedContactsWithEmail().length} Recipients
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {currentStep === 'results' && sendResults && (
          <Card>
            <CardHeader>
              <CardTitle>Campaign Results</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {/* Summary Stats */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div className="text-center p-4 bg-green-50 rounded-lg">
                    <CheckCircle className="h-8 w-8 mx-auto text-green-600 mb-2" />
                    <p className="text-2xl font-bold text-green-600">{sendResults.successful_sends}</p>
                    <p className="text-sm text-gray-600">Successful Sends</p>
                  </div>
                  <div className="text-center p-4 bg-red-50 rounded-lg">
                    <AlertCircle className="h-8 w-8 mx-auto text-red-600 mb-2" />
                    <p className="text-2xl font-bold text-red-600">{sendResults.failed_sends}</p>
                    <p className="text-sm text-gray-600">Failed Sends</p>
                  </div>
                  <div className="text-center p-4 bg-blue-50 rounded-lg">
                    <Users className="h-8 w-8 mx-auto text-blue-600 mb-2" />
                    <p className="text-2xl font-bold text-blue-600">{sendResults.total_contacts}</p>
                    <p className="text-sm text-gray-600">Total Recipients</p>
                  </div>
                </div>

                {/* Error Details */}
                {sendResults.errors.length > 0 && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-3">Failed Sends ({sendResults.errors.length})</h4>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {sendResults.errors.map((error, index) => (
                        <div key={index} className="p-3 bg-red-50 border border-red-200 rounded">
                          <p className="font-medium text-red-800">{error.contact_email}</p>
                          <p className="text-sm text-red-600">{error.error}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-4 pt-4 border-t">
                  <Button onClick={() => router.push('/organizations/crm')}>
                    Return to CRM
                  </Button>
                  <Button variant="outline" onClick={() => {
                    setCurrentStep('template')
                    setSelectedTemplate(null)
                    setSelectedContacts(new Set())
                    setSendResults(null)
                    setAdditionalVariables({})
                  }}>
                    Send Another Campaign
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Preview Dialog */}
      <Dialog open={showPreview} onOpenChange={setShowPreview}>
        <DialogContent className="w-[95vw] max-w-[90vw] sm:max-w-[80vw] lg:max-w-[1000px] xl:max-w-[1200px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Email Preview</DialogTitle>
          </DialogHeader>
          {selectedTemplate && (
            <div className="space-y-4">
              <div>
                <Label className="font-medium">Subject</Label>
                <p className="border rounded p-2 bg-gray-50">{selectedTemplate.subject}</p>
              </div>
              <div>
                <Label className="font-medium">Preview (with sample data)</Label>
                <div className="border rounded p-4 bg-white">
                  <iframe
                    srcDoc={selectedTemplate.html_content.replace(/\{\{([^}]+)\}\}/g, (match, variable) => {
                      if (additionalVariables[variable]) return additionalVariables[variable]
                      switch (variable) {
                        case 'contact_name': return 'John Doe'
                        case 'business_name': return 'Sample Company'
                        case 'organization_name': return organizationName
                        case 'contact_email': return 'john.doe@example.com'
                        case 'contact_role': return 'CEO'
                        default: return `{{${variable}}}`
                      }
                    })}
                    className="w-full h-[300px] sm:h-[400px] lg:h-[500px] border"
                    title="Email Preview"
                    sandbox="allow-same-origin"
                  />
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}