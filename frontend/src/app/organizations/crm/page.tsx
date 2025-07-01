'use client'

import React, { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import FieldMapping from '@/components/crm/FieldMapping'
import CSVPreview from '@/components/crm/CSVPreview'
import ContactCardView from '@/components/crm/ContactCardView'
import ContactTableView from '@/components/crm/ContactTableView'
import { parseCSV, createInitialMapping, validateMapping, generateFieldMappingJSON, type FieldMapping as FieldMappingType, type CSVParseResult } from '@/utils/csvParser'
import { 
  UserCheck, 
  Plus, 
  Search, 
  Filter, 
  Mail, 
  Phone, 
  Building, 
  Calendar,
  TrendingUp,
  Users,
  MessageSquare,
  CheckCircle,
  Clock,
  AlertCircle,
  Upload,
  Download,
  ArrowRight,
  ArrowLeft,
  Grid3X3,
  Table
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

interface ContactInteraction {
  id: string
  interaction_type: string
  subject?: string
  content: string
  interaction_date: string
  user_name?: string
}

interface DashboardStats {
  total_contacts: number
  contacts_by_status: Record<string, number>
  recent_interactions: ContactInteraction[]
  upcoming_tasks: ContactInteraction[]
  contact_growth: Record<string, number>
}

interface PaginatedContactsResponse {
  items: Contact[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export default function CRMPage() {
  const { token, user } = useAuth()
  const [dashboardStats, setDashboardStats] = useState<DashboardStats | null>(null)
  const [contacts, setContacts] = useState<Contact[]>([])
  const [loading, setLoading] = useState(true)
  const [contactsLoading, setContactsLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [showAllContacts, setShowAllContacts] = useState(false)
  const [showAddContact, setShowAddContact] = useState(false)
  const [showImportDialog, setShowImportDialog] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [viewMode, setViewMode] = useState<'cards' | 'table'>('cards')
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalContacts, setTotalContacts] = useState(0)
  const [pageSize, setPageSize] = useState(20)
  
  // Form state for adding contacts
  const [newContact, setNewContact] = useState({
    business_name: '',
    contact_name: '',
    contact_email: '',
    contact_role: '',
    phone: '',
    city: '',
    state: '',
    website: '',
    address: '',
    status: 'lead',
    notes: ''
  })
  
  // Import state
  const [importFile, setImportFile] = useState<File | null>(null)
  const [importResults, setImportResults] = useState<any>(null)
  const [csvData, setCsvData] = useState<CSVParseResult | null>(null)
  const [fieldMappings, setFieldMappings] = useState<FieldMappingType[]>([])
  const [importStep, setImportStep] = useState<'upload' | 'mapping' | 'results'>('upload')
  const [validationErrors, setValidationErrors] = useState<string[]>([])

  // Fetch dashboard data
  useEffect(() => {
    const fetchDashboard = async () => {
      if (!token) return

      try {
        const response = await fetch('/api/crm/dashboard', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        })

        if (response.ok) {
          const data = await response.json()
          setDashboardStats(data.stats)
          setContacts(data.recent_contacts)
        } else {
          console.error('Failed to fetch CRM dashboard')
        }
      } catch (error) {
        console.error('Error fetching CRM dashboard:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchDashboard()
  }, [token])

  // Handle search and filter changes with debounce
  useEffect(() => {
    if (showAllContacts) {
      const timeoutId = setTimeout(() => {
        handleSearchOrFilterChange()
      }, 300) // 300ms debounce for search
      
      return () => clearTimeout(timeoutId)
    }
  }, [searchTerm, statusFilter, showAllContacts])

  // Fetch contacts with pagination
  const fetchContacts = async (page: number = 1, search?: string, status?: string) => {
    if (!token) return
    
    setContactsLoading(true)
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString()
      })
      
      if (search) params.append('search', search)
      if (status && status !== 'all') params.append('status', status)
      
      const response = await fetch(`/api/crm/contacts?${params}`, {
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
        setShowAllContacts(true)
      } else {
        console.error('Failed to fetch contacts')
      }
    } catch (error) {
      console.error('Error fetching contacts:', error)
    } finally {
      setContactsLoading(false)
    }
  }

  // Legacy function for "View All" button
  const fetchAllContacts = () => fetchContacts(1, searchTerm, statusFilter)

  // Handle search and filter changes
  const handleSearchOrFilterChange = () => {
    if (showAllContacts) {
      fetchContacts(1, searchTerm, statusFilter)
    }
  }

  // Navigate to specific page
  const goToPage = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      fetchContacts(page, searchTerm, statusFilter)
    }
  }

  // Check if user has admin access
  if (!user || !['admin', 'super_admin'].includes(user.role)) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Card className="w-96">
          <CardContent className="p-6 text-center">
            <AlertCircle className="h-12 w-12 mx-auto text-red-500 mb-4" />
            <h2 className="text-xl font-semibold mb-2">Access Denied</h2>
            <p className="text-gray-600">
              CRM access is restricted to admin users only.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="p-6">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-24 bg-gray-200 rounded"></div>
              ))}
            </div>
            <div className="h-96 bg-gray-200 rounded"></div>
          </div>
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

  // Handle contact creation
  const handleCreateContact = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token) return
    
    setIsSubmitting(true)
    try {
      const response = await fetch('/api/crm/contacts', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(newContact)
      })
      
      if (response.ok) {
        // Reset form and close dialog
        setNewContact({
          business_name: '',
          contact_name: '',
          contact_email: '',
          contact_role: '',
          phone: '',
          city: '',
          state: '',
          website: '',
          address: '',
          status: 'lead',
          notes: ''
        })
        setShowAddContact(false)
        
        // Refresh the contacts list
        if (showAllContacts) {
          await fetchAllContacts()
        } else {
          const dashboardResponse = await fetch('/api/crm/dashboard', {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          })
          
          if (dashboardResponse.ok) {
            const data = await dashboardResponse.json()
            setDashboardStats(data.stats)
            setContacts(data.recent_contacts)
          }
        }
      } else {
        const error = await response.json()
        alert(`Error creating contact: ${error.detail}`)
      }
    } catch (error) {
      console.error('Error creating contact:', error)
      alert('Error creating contact. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }
  
  // Handle file upload and CSV parsing
  const handleFileUpload = async (file: File) => {
    try {
      const csvText = await file.text()
      const parseResult = parseCSV(csvText)
      setCsvData(parseResult)
      
      // Create initial field mappings
      const initialMappings = createInitialMapping(parseResult.headers)
      setFieldMappings(initialMappings)
      
      // Move to mapping step
      setImportFile(file)
      setImportStep('mapping')
      
      // Clear any previous validation errors
      setValidationErrors([])
    } catch (error) {
      console.error('Error parsing CSV:', error)
      alert('Error parsing CSV file. Please check the file format and try again.')
    }
  }

  // Handle field mapping changes
  const handleMappingChange = (mappings: FieldMappingType[]) => {
    setFieldMappings(mappings)
    
    // Validate mappings
    const validationResult = validateMapping(mappings)
    setValidationErrors(validationResult.errors)
  }

  // Reset import dialog
  const resetImportDialog = () => {
    setShowImportDialog(false)
    setImportStep('upload')
    setImportFile(null)
    setCsvData(null)
    setFieldMappings([])
    setValidationErrors([])
    setImportResults(null)
  }

  // Handle CSV import
  const handleImport = async () => {
    if (!token || !importFile || !csvData) return
    
    setIsSubmitting(true)
    try {
      const formData = new FormData()
      formData.append('file', importFile)
      
      // Generate field mapping from user selections
      const fieldMapping = generateFieldMappingJSON(fieldMappings)
      
      const response = await fetch(`/api/crm/contacts/import?field_mapping=${encodeURIComponent(fieldMapping)}&update_existing=false`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      })
      
      if (response.ok) {
        const results = await response.json()
        setImportResults(results)
        setImportStep('results')
        
        // Refresh the contacts list
        if (showAllContacts) {
          await fetchAllContacts()
        } else {
          const dashboardResponse = await fetch('/api/crm/dashboard', {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          })
          
          if (dashboardResponse.ok) {
            const data = await dashboardResponse.json()
            setDashboardStats(data.stats)
            setContacts(data.recent_contacts)
          }
        }
      } else {
        const error = await response.json()
        alert(`Error importing contacts: ${error.detail}`)
      }
    } catch (error) {
      console.error('Error importing contacts:', error)
      alert('Error importing contacts. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Handle contact update
  const handleContactUpdate = async (contactId: string, updatedContact: Partial<Contact>) => {
    if (!token) return
    
    try {
      const response = await fetch(`/api/crm/contacts/${contactId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(updatedContact)
      })
      
      if (response.ok) {
        // Update the contact in the local state
        setContacts(prevContacts => 
          prevContacts.map(contact => 
            contact.id === contactId 
              ? { ...contact, ...updatedContact }
              : contact
          )
        )
        
        // Optionally refresh dashboard stats if status changed
        if (updatedContact.status) {
          const dashboardResponse = await fetch('/api/crm/dashboard', {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          })
          
          if (dashboardResponse.ok) {
            const data = await dashboardResponse.json()
            setDashboardStats(data.stats)
          }
        }
      } else {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to update contact')
      }
    } catch (error) {
      console.error('Error updating contact:', error)
      throw error
    }
  }

  // Handle contact deletion
  const handleContactDelete = async (contactId: string) => {
    if (!token) return
    
    try {
      const response = await fetch(`/api/crm/contacts/${contactId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })
      
      if (response.ok) {
        // Remove the contact from the local state
        setContacts(prevContacts => 
          prevContacts.filter(contact => contact.id !== contactId)
        )
        
        // Refresh dashboard stats
        const dashboardResponse = await fetch('/api/crm/dashboard', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        })
        
        if (dashboardResponse.ok) {
          const data = await dashboardResponse.json()
          setDashboardStats(data.stats)
        }
      } else {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to delete contact')
      }
    } catch (error) {
      console.error('Error deleting contact:', error)
      throw error
    }
  }

  // Filter contacts based on search and status
  const filteredContacts = contacts.filter(contact => {
    const matchesSearch = searchTerm === '' || 
      contact.business_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      contact.contact_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      contact.contact_email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      contact.phone?.includes(searchTerm)
    
    const matchesStatus = statusFilter === 'all' || contact.status === statusFilter
    
    return matchesSearch && matchesStatus
  })

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center">
              <UserCheck className="h-8 w-8 mr-3 text-blue-600" />
              Customer Relationship Management
            </h1>
            <p className="text-gray-600 mt-1">
              Manage contacts, track interactions, and grow your business relationships
            </p>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" onClick={() => setShowImportDialog(true)}>
              <Upload className="h-4 w-4 mr-2" />
              Import Contacts
            </Button>
            <Button onClick={() => setShowAddContact(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Contact
            </Button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Contacts</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {dashboardStats?.total_contacts || 0}
                  </p>
                </div>
                <Users className="h-8 w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Active Customers</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {dashboardStats?.contacts_by_status?.customer || 0}
                  </p>
                </div>
                <CheckCircle className="h-8 w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Prospects</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {dashboardStats?.contacts_by_status?.prospect || 0}
                  </p>
                </div>
                <TrendingUp className="h-8 w-8 text-orange-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">New Leads</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {dashboardStats?.contacts_by_status?.lead || 0}
                  </p>
                </div>
                <Clock className="h-8 w-8 text-purple-600" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Contacts List */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>
                    Contacts ({filteredContacts.length}{showAllContacts && totalContacts > filteredContacts.length ? ` of ${totalContacts}` : ''})
                    {showAllContacts && <span className="text-sm font-normal text-gray-500 ml-2">(Page {currentPage} of {totalPages})</span>}
                    {!showAllContacts && <span className="text-sm font-normal text-gray-500 ml-2">(Recent 10)</span>}
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    <div className="flex border rounded-lg">
                      <Button
                        variant={viewMode === 'cards' ? 'default' : 'ghost'}
                        size="sm"
                        onClick={() => setViewMode('cards')}
                        className="rounded-r-none"
                      >
                        <Grid3X3 className="h-4 w-4" />
                      </Button>
                      <Button
                        variant={viewMode === 'table' ? 'default' : 'ghost'}
                        size="sm"
                        onClick={() => setViewMode('table')}
                        className="rounded-l-none"
                      >
                        <Table className="h-4 w-4" />
                      </Button>
                    </div>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={fetchAllContacts}
                      disabled={contactsLoading}
                    >
                      <Search className="h-4 w-4 mr-2" />
                      {contactsLoading ? 'Loading...' : showAllContacts ? `All ${totalContacts}` : 'View All'}
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {/* Search and Filter */}
                <div className="flex gap-4 mb-4">
                  <div className="flex-1">
                    <Input
                      placeholder="Search contacts..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-full"
                    />
                  </div>
                  <Select value={statusFilter} onValueChange={setStatusFilter}>
                    <SelectTrigger className="w-40">
                      <SelectValue placeholder="Status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Status</SelectItem>
                      <SelectItem value="lead">Lead</SelectItem>
                      <SelectItem value="prospect">Prospect</SelectItem>
                      <SelectItem value="customer">Customer</SelectItem>
                      <SelectItem value="inactive">Inactive</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Contact Views */}
                <div className={viewMode === 'table' ? '' : 'max-h-96 overflow-y-auto'}>
                  {viewMode === 'cards' ? (
                    <ContactCardView 
                      contacts={filteredContacts} 
                      onContactUpdate={handleContactUpdate}
                      onContactDelete={handleContactDelete}
                    />
                  ) : (
                    <ContactTableView 
                      contacts={filteredContacts} 
                      onContactUpdate={handleContactUpdate}
                      onContactDelete={handleContactDelete}
                    />
                  )}
                </div>

                {/* Pagination Controls */}
                {showAllContacts && totalPages > 1 && (
                  <div className="flex items-center justify-between mt-4 pt-4 border-t">
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
                        <ArrowLeft className="h-4 w-4 mr-1" />
                        Previous
                      </Button>
                      
                      <div className="flex items-center gap-1">
                        {/* Show page numbers */}
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
                        <ArrowRight className="h-4 w-4 ml-1" />
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Recent Activity */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <MessageSquare className="h-5 w-5 mr-2" />
                  Recent Activity
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 max-h-48 overflow-y-auto">
                  {dashboardStats?.recent_interactions?.slice(0, 5).map((interaction) => (
                    <div key={interaction.id} className="text-sm">
                      <p className="font-medium text-gray-900">{interaction.subject || 'No subject'}</p>
                      <p className="text-gray-600 text-xs">{interaction.user_name}</p>
                      <p className="text-gray-500 text-xs">
                        {new Date(interaction.interaction_date).toLocaleDateString()}
                      </p>
                    </div>
                  )) || <p className="text-gray-500 text-sm">No recent activity</p>}
                </div>
              </CardContent>
            </Card>

            {/* Upcoming Tasks */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Calendar className="h-5 w-5 mr-2" />
                  Upcoming Tasks
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 max-h-48 overflow-y-auto">
                  {dashboardStats?.upcoming_tasks?.slice(0, 5).map((task) => (
                    <div key={task.id} className="text-sm">
                      <p className="font-medium text-gray-900">{task.subject || 'No subject'}</p>
                      <p className="text-gray-600 text-xs">{task.content.substring(0, 50)}...</p>
                      <p className="text-gray-500 text-xs">
                        Due: {new Date(task.interaction_date).toLocaleDateString()}
                      </p>
                    </div>
                  )) || <p className="text-gray-500 text-sm">No upcoming tasks</p>}
                </div>
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Button variant="outline" className="w-full justify-start">
                  <Mail className="h-4 w-4 mr-2" />
                  Send Email Campaign
                </Button>
                <Button variant="outline" className="w-full justify-start">
                  <Download className="h-4 w-4 mr-2" />
                  Export Contacts
                </Button>
                <Button variant="outline" className="w-full justify-start">
                  <Filter className="h-4 w-4 mr-2" />
                  Advanced Filters
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Add Contact Dialog */}
      <Dialog open={showAddContact} onOpenChange={setShowAddContact}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto bg-white border border-gray-200 shadow-lg">
          <DialogHeader>
            <DialogTitle className="text-gray-900">Add New Contact</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateContact} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="business_name">Business Name *</Label>
                <Input
                  id="business_name"
                  value={newContact.business_name}
                  onChange={(e) => setNewContact({...newContact, business_name: e.target.value})}
                  required
                />
              </div>
              <div>
                <Label htmlFor="contact_name">Contact Name *</Label>
                <Input
                  id="contact_name"
                  value={newContact.contact_name}
                  onChange={(e) => setNewContact({...newContact, contact_name: e.target.value})}
                  required
                />
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="contact_email">Email</Label>
                <Input
                  id="contact_email"
                  type="email"
                  value={newContact.contact_email}
                  onChange={(e) => setNewContact({...newContact, contact_email: e.target.value})}
                />
              </div>
              <div>
                <Label htmlFor="contact_role">Role</Label>
                <Input
                  id="contact_role"
                  value={newContact.contact_role}
                  onChange={(e) => setNewContact({...newContact, contact_role: e.target.value})}
                />
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="phone">Phone</Label>
                <Input
                  id="phone"
                  value={newContact.phone}
                  onChange={(e) => setNewContact({...newContact, phone: e.target.value})}
                />
              </div>
              <div>
                <Label htmlFor="website">Website</Label>
                <Input
                  id="website"
                  value={newContact.website}
                  onChange={(e) => setNewContact({...newContact, website: e.target.value})}
                />
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="city">City</Label>
                <Input
                  id="city"
                  value={newContact.city}
                  onChange={(e) => setNewContact({...newContact, city: e.target.value})}
                />
              </div>
              <div>
                <Label htmlFor="state">State</Label>
                <Input
                  id="state"
                  value={newContact.state}
                  onChange={(e) => setNewContact({...newContact, state: e.target.value})}
                />
              </div>
            </div>
            
            <div>
              <Label htmlFor="status">Status</Label>
              <Select value={newContact.status} onValueChange={(value) => setNewContact({...newContact, status: value})}>
                <SelectTrigger>
                  <SelectValue placeholder="Select status" />
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
            
            <div>
              <Label htmlFor="address">Address</Label>
              <Input
                id="address"
                value={newContact.address}
                onChange={(e) => setNewContact({...newContact, address: e.target.value})}
              />
            </div>
            
            <div>
              <Label htmlFor="notes">Notes</Label>
              <Textarea
                id="notes"
                value={newContact.notes}
                onChange={(e) => setNewContact({...newContact, notes: e.target.value})}
                rows={3}
              />
            </div>
            
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setShowAddContact(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Creating...' : 'Create Contact'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
      
      {/* Import Contacts Dialog */}
      <Dialog open={showImportDialog} onOpenChange={setShowImportDialog}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto bg-white border border-gray-200 shadow-lg">
          <DialogHeader>
            <DialogTitle className="text-gray-900 flex items-center gap-2">
              <Upload className="h-5 w-5" />
              Import Contacts from CSV
              <div className="ml-auto flex items-center gap-2">
                {importStep === 'upload' && <span className="text-sm bg-blue-100 text-blue-800 px-2 py-1 rounded">Step 1: Upload</span>}
                {importStep === 'mapping' && <span className="text-sm bg-blue-100 text-blue-800 px-2 py-1 rounded">Step 2: Map Fields</span>}
                {importStep === 'results' && <span className="text-sm bg-green-100 text-green-800 px-2 py-1 rounded">Step 3: Results</span>}
              </div>
            </DialogTitle>
          </DialogHeader>
          
          {importStep === 'upload' && (
            <div className="space-y-4">
              <div>
                <Label htmlFor="csv-file">Choose CSV File</Label>
                <Input
                  id="csv-file"
                  type="file"
                  accept=".csv"
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) {
                      handleFileUpload(file)
                    }
                  }}
                  required
                />
                <p className="text-sm text-gray-600 mt-1">
                  Upload a CSV file with your contact data. The first row should contain column headers.
                </p>
              </div>
              
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h4 className="font-medium text-blue-900 mb-2">What happens next?</h4>
                <ol className="text-sm text-blue-800 space-y-1">
                  <li>1. We'll preview your CSV file</li>
                  <li>2. You'll map CSV columns to CRM fields</li>
                  <li>3. We'll import your contacts</li>
                </ol>
              </div>
              
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={resetImportDialog}>
                  Cancel
                </Button>
              </div>
            </div>
          )}
          
          {importStep === 'mapping' && csvData && (
            <div className="space-y-6">
              <CSVPreview 
                headers={csvData.headers}
                preview={csvData.preview}
                fileName={importFile?.name}
              />
              
              <FieldMapping
                mappings={fieldMappings}
                onMappingChange={handleMappingChange}
                validationErrors={validationErrors}
              />
              
              <div className="flex justify-between gap-2">
                <Button 
                  type="button" 
                  variant="outline" 
                  onClick={() => {
                    setImportStep('upload')
                    setCsvData(null)
                    setFieldMappings([])
                    setImportFile(null)
                  }}
                >
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Back to Upload
                </Button>
                <div className="flex gap-2">
                  <Button type="button" variant="outline" onClick={resetImportDialog}>
                    Cancel
                  </Button>
                  <Button 
                    onClick={handleImport} 
                    disabled={isSubmitting || validationErrors.length > 0}
                  >
                    {isSubmitting ? 'Importing...' : (
                      <>
                        Import {fieldMappings.filter(m => m.crmField).length > 0 ? `${fieldMappings.filter(m => m.crmField).length} Fields` : 'Contacts'}
                        <ArrowRight className="h-4 w-4 ml-2" />
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </div>
          )}
          
          {importStep === 'results' && importResults && (
            <div className="space-y-4">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <h3 className="font-semibold text-green-800 mb-2">Import Results</h3>
                <div className="text-sm text-green-700">
                  <p>Total rows processed: {importResults.total_rows}</p>
                  <p>Successfully imported: {importResults.successful_imports}</p>
                  <p>Failed imports: {importResults.failed_imports}</p>
                  <p>New contacts created: {importResults.created_contacts?.length || 0}</p>
                  <p>Existing contacts updated: {importResults.updated_contacts?.length || 0}</p>
                </div>
                
                {importResults.errors && importResults.errors.length > 0 && (
                  <div className="mt-3">
                    <h4 className="font-medium text-red-800 mb-1">Errors:</h4>
                    <div className="max-h-32 overflow-y-auto text-xs text-red-700">
                      {importResults.errors.map((error: any, idx: number) => (
                        <p key={idx}>Row {error.row}: {error.error}</p>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => {
                  setImportStep('upload')
                  setImportResults(null)
                  setCsvData(null)
                  setFieldMappings([])
                  setImportFile(null)
                }}>
                  Import Another File
                </Button>
                <Button onClick={resetImportDialog}>
                  Close
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}