'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
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
  FileText,
  Edit,
  Trash2,
  Eye,
  Play,
  Pause,
  BarChart3
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

interface EmailTemplate {
  id: string
  name: string
  subject: string
  html_content: string
  text_content?: string
  variables: string[]
  created_at: string
}

interface PaginatedContactsResponse {
  items: Contact[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export default function CRMPage() {
  const { token, user, organization } = useAuth()
  const router = useRouter()
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
  const [activeTab, setActiveTab] = useState<'contacts' | 'templates'>('contacts')
  
  // Email template state
  const [emailTemplates, setEmailTemplates] = useState<EmailTemplate[]>([])
  const [templatesLoading, setTemplatesLoading] = useState(false)
  const [showTemplateUpload, setShowTemplateUpload] = useState(false)
  const [showTemplateView, setShowTemplateView] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState<EmailTemplate | null>(null)
  const [templateFile, setTemplateFile] = useState<File | null>(null)
  const [templateName, setTemplateName] = useState('')
  const [templateSubject, setTemplateSubject] = useState('')
  const [isEditingTemplate, setIsEditingTemplate] = useState(false)
  const [editTemplateName, setEditTemplateName] = useState('')
  const [editTemplateSubject, setEditTemplateSubject] = useState('')
  const [editTemplateContent, setEditTemplateContent] = useState('')
  
  // Create new template state
  const [showCreateTemplate, setShowCreateTemplate] = useState(false)
  const [newTemplateName, setNewTemplateName] = useState('')
  const [newTemplateSubject, setNewTemplateSubject] = useState('')
  const [newTemplateContent, setNewTemplateContent] = useState('')
  
  // Feature not implemented modal state
  const [showNotImplementedModal, setShowNotImplementedModal] = useState(false)
  const [notImplementedFeature, setNotImplementedFeature] = useState('')
  
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

  // Fetch email templates when templates tab is active
  useEffect(() => {
    if (activeTab === 'templates' && token) {
      fetchEmailTemplates()
    }
  }, [activeTab, token])


  // Fetch email templates
  const fetchEmailTemplates = async () => {
    if (!token) return
    
    setTemplatesLoading(true)
    try {
      const response = await fetch('/api/crm/email-templates', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        const templates = await response.json()
        setEmailTemplates(templates)
      } else {
        console.error('Failed to fetch email templates')
      }
    } catch (error) {
      console.error('Error fetching email templates:', error)
    } finally {
      setTemplatesLoading(false)
    }
  }

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

  // Check if user is authenticated
  if (!user) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Card className="w-96">
          <CardContent className="p-6 text-center">
            <AlertCircle className="h-12 w-12 mx-auto text-red-500 mb-4" />
            <h2 className="text-xl font-semibold mb-2">Authentication Required</h2>
            <p className="text-gray-600">
              Please log in to access the CRM.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Check if user has access (any authenticated user can access CRM)
  // Non-admin users will have limited functionality within the CRM

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

  // Handle template upload
  const handleTemplateUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token || !templateFile || !templateName || !templateSubject) return
    
    setIsSubmitting(true)
    try {
      const formData = new FormData()
      formData.append('file', templateFile)
      
      const response = await fetch(`/api/crm/email-templates/upload?name=${encodeURIComponent(templateName)}&subject=${encodeURIComponent(templateSubject)}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      })
      
      if (response.ok) {
        // Reset form and close dialog
        setTemplateFile(null)
        setTemplateName('')
        setTemplateSubject('')
        setShowTemplateUpload(false)
        
        // Refresh templates
        await fetchEmailTemplates()
        
        alert('Email template uploaded successfully!')
      } else {
        const error = await response.json()
        alert(`Error uploading template: ${error.detail}`)
      }
    } catch (error) {
      console.error('Error uploading template:', error)
      alert('Error uploading template. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Handle template deletion
  const handleTemplateDelete = async (templateId: string) => {
    if (!token || !confirm('Are you sure you want to delete this email template?')) return
    
    try {
      const response = await fetch(`/api/crm/email-templates/${templateId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })
      
      if (response.ok) {
        // Remove template from local state
        setEmailTemplates(prevTemplates => 
          prevTemplates.filter(template => template.id !== templateId)
        )
      } else {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to delete template')
      }
    } catch (error) {
      console.error('Error deleting template:', error)
      alert('Error deleting template. Please try again.')
    }
  }


  // Handle template update
  const handleTemplateUpdate = async () => {
    if (!token || !selectedTemplate) return
    
    setIsSubmitting(true)
    try {
      const updateData: any = {}
      
      if (editTemplateName !== selectedTemplate.name) {
        updateData.name = editTemplateName
      }
      if (editTemplateSubject !== selectedTemplate.subject) {
        updateData.subject = editTemplateSubject
      }
      if (editTemplateContent !== selectedTemplate.html_content) {
        updateData.html_content = editTemplateContent
        // Re-extract variables from updated content
        const variableRegex = /\{\{([^}]+)\}\}/g
        const variables: string[] = []
        let match
        while ((match = variableRegex.exec(editTemplateContent)) !== null) {
          if (!variables.includes(match[1])) {
            variables.push(match[1])
          }
        }
        updateData.variables = variables
      }
      
      if (Object.keys(updateData).length === 0) {
        setIsEditingTemplate(false)
        return
      }
      
      const response = await fetch(`/api/crm/email-templates/${selectedTemplate.id}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(updateData)
      })
      
      if (response.ok) {
        const updatedTemplate = await response.json()
        
        // Update local state
        setEmailTemplates(prevTemplates => 
          prevTemplates.map(template => 
            template.id === selectedTemplate.id ? updatedTemplate : template
          )
        )
        
        // Update selected template
        setSelectedTemplate(updatedTemplate)
        setIsEditingTemplate(false)
        
        alert('Template updated successfully!')
      } else {
        const error = await response.json()
        alert(`Error updating template: ${error.detail}`)
      }
    } catch (error) {
      console.error('Error updating template:', error)
      alert('Error updating template. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Start editing template
  const startEditingTemplate = (template: EmailTemplate) => {
    setEditTemplateName(template.name)
    setEditTemplateSubject(template.subject)
    setEditTemplateContent(template.html_content)
    setIsEditingTemplate(true)
  }

  // Handle create new template
  const handleCreateTemplate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token || !newTemplateName || !newTemplateSubject || !newTemplateContent) return
    
    setIsSubmitting(true)
    try {
      // Extract variables from content
      const variableRegex = /\{\{([^}]+)\}\}/g
      const variables: string[] = []
      let match
      while ((match = variableRegex.exec(newTemplateContent)) !== null) {
        if (!variables.includes(match[1])) {
          variables.push(match[1])
        }
      }
      
      const response = await fetch(`/api/crm/email-templates`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: newTemplateName,
          subject: newTemplateSubject,
          html_content: newTemplateContent,
          text_content: null,
          variables: variables
        })
      })
      
      if (response.ok) {
        const newTemplate = await response.json()
        
        // Add to templates list
        setEmailTemplates(prevTemplates => [...prevTemplates, newTemplate])
        
        // Reset form and close dialog
        setNewTemplateName('')
        setNewTemplateSubject('')
        setNewTemplateContent('')
        setShowCreateTemplate(false)
        
        alert('Template created successfully!')
      } else {
        const error = await response.json()
        alert(`Error creating template: ${error.detail}`)
      }
    } catch (error) {
      console.error('Error creating template:', error)
      alert('Error creating template. Please try again.')
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
    <div className="min-h-screen bg-gray-50 w-full overflow-x-hidden">
      {/* Sticky Header */}
      <div className="sticky top-0 bg-white border-b border-gray-200 z-50 shadow-sm">
        <div className="p-4 sm:p-6 max-w-full">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="min-w-0 flex-1">
              <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-gray-900 flex items-center">
                <UserCheck className="h-5 w-5 sm:h-6 sm:w-6 lg:h-8 lg:w-8 mr-2 sm:mr-3 text-blue-600 flex-shrink-0" />
                <span className="truncate">Customer Relationship Management</span>
              </h1>
              <p className="text-xs sm:text-sm lg:text-base text-gray-600 mt-1">
                Manage contacts, track interactions, and grow your business relationships
              </p>
            </div>
            <div className="flex flex-wrap gap-2 sm:gap-3 w-full sm:w-auto sm:flex-shrink-0">
              {activeTab === 'contacts' && (
                <>
                  <Button variant="outline" onClick={() => setShowImportDialog(true)} className="flex-1 sm:flex-initial">
                    <Upload className="h-4 w-4 mr-2" />
                    <span className="hidden sm:inline">Import Contacts</span>
                    <span className="sm:hidden">Import</span>
                  </Button>
                  <Button onClick={() => setShowAddContact(true)} className="flex-1 sm:flex-initial">
                    <Plus className="h-4 w-4 mr-2" />
                    <span className="hidden sm:inline">Add Contact</span>
                    <span className="sm:hidden">Add</span>
                  </Button>
                </>
              )}
              {activeTab === 'templates' && (
                <>
                  <Button onClick={() => setShowCreateTemplate(true)} className="w-full sm:w-auto">
                    <Plus className="h-4 w-4 mr-2" />
                    Create Template
                  </Button>
                  <Button variant="outline" onClick={() => setShowTemplateUpload(true)} className="w-full sm:w-auto">
                    <Upload className="h-4 w-4 mr-2" />
                    Upload Template
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="p-4 sm:p-6 max-w-full overflow-x-hidden">

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as 'contacts' | 'templates')} className="mb-6">
          <TabsList className="grid w-full grid-cols-2 max-w-full sm:max-w-md mx-auto sm:mx-0">
            <TabsTrigger value="contacts" className="flex items-center gap-2 text-xs sm:text-sm">
              <Users className="h-3 w-3 sm:h-4 sm:w-4" />
              <span className="hidden xs:inline">Contacts</span>
              <span className="xs:hidden">Contacts</span>
            </TabsTrigger>
            <TabsTrigger value="templates" className="flex items-center gap-2 text-xs sm:text-sm">
              <FileText className="h-3 w-3 sm:h-4 sm:w-4" />
              <span className="hidden xs:inline">Email Templates</span>
              <span className="xs:hidden">Templates</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="contacts">
            {/* Stats Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 lg:gap-6 mb-6 sm:mb-8">
              <Card className="min-w-0">
                <CardContent className="p-3 sm:p-4 lg:p-6">
                  <div className="flex items-center justify-between">
                    <div className="min-w-0 flex-1">
                      <p className="text-xs sm:text-sm font-medium text-gray-600 truncate">Total Contacts</p>
                      <p className="text-lg sm:text-xl lg:text-2xl font-bold text-gray-900">
                        {dashboardStats?.total_contacts || 0}
                      </p>
                    </div>
                    <Users className="h-5 w-5 sm:h-6 sm:w-6 lg:h-8 lg:w-8 text-blue-600 flex-shrink-0" />
                  </div>
                </CardContent>
              </Card>

              <Card className="min-w-0">
                <CardContent className="p-3 sm:p-4 lg:p-6">
                  <div className="flex items-center justify-between">
                    <div className="min-w-0 flex-1">
                      <p className="text-xs sm:text-sm font-medium text-gray-600 truncate">Active Customers</p>
                      <p className="text-lg sm:text-xl lg:text-2xl font-bold text-gray-900">
                        {dashboardStats?.contacts_by_status?.customer || 0}
                      </p>
                    </div>
                    <CheckCircle className="h-5 w-5 sm:h-6 sm:w-6 lg:h-8 lg:w-8 text-green-600 flex-shrink-0" />
                  </div>
                </CardContent>
              </Card>

              <Card className="min-w-0">
                <CardContent className="p-3 sm:p-4 lg:p-6">
                  <div className="flex items-center justify-between">
                    <div className="min-w-0 flex-1">
                      <p className="text-xs sm:text-sm font-medium text-gray-600 truncate">Prospects</p>
                      <p className="text-lg sm:text-xl lg:text-2xl font-bold text-gray-900">
                        {dashboardStats?.contacts_by_status?.prospect || 0}
                      </p>
                    </div>
                    <TrendingUp className="h-5 w-5 sm:h-6 sm:w-6 lg:h-8 lg:w-8 text-orange-600 flex-shrink-0" />
                  </div>
                </CardContent>
              </Card>

              <Card className="min-w-0">
                <CardContent className="p-3 sm:p-4 lg:p-6">
                  <div className="flex items-center justify-between">
                    <div className="min-w-0 flex-1">
                      <p className="text-xs sm:text-sm font-medium text-gray-600 truncate">New Leads</p>
                      <p className="text-lg sm:text-xl lg:text-2xl font-bold text-gray-900">
                        {dashboardStats?.contacts_by_status?.lead || 0}
                      </p>
                    </div>
                    <Clock className="h-5 w-5 sm:h-6 sm:w-6 lg:h-8 lg:w-8 text-purple-600 flex-shrink-0" />
                  </div>
                </CardContent>
              </Card>
            </div>

        {/* Main Content */}
        <div>
          {/* Contacts List */}
          <div>
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>
                    Contacts ({filteredContacts.length}{showAllContacts && totalContacts > filteredContacts.length ? ` of ${totalContacts}` : ''})
                    {showAllContacts && <span className="text-sm font-normal text-gray-500 ml-2">(Page {currentPage} of {totalPages})</span>}
                    {!showAllContacts && <span className="text-sm font-normal text-gray-500 ml-2">(Recent 10)</span>}
                  </CardTitle>
                  <div className="flex gap-2">
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
                {/* Sidebar Actions */}
            <div className="mb-4 sm:mb-6 p-3 sm:p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <h3 className="font-medium text-blue-900 mb-2 sm:mb-3 text-sm sm:text-base">Quick Actions</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                <Button 
                  variant="outline" 
                  className="justify-start text-xs sm:text-sm bg-white hover:bg-blue-100 w-full"
                  onClick={() => router.push('/organizations/crm/bulk-email')}
                >
                  <Mail className="h-4 w-4 mr-2 flex-shrink-0" />
                  <span className="truncate">Send Email Campaign</span>
                </Button>
                <Button 
                  variant="outline" 
                  className="justify-start text-xs sm:text-sm bg-white hover:bg-blue-100 w-full"
                  onClick={() => router.push('/organizations/crm/campaigns')}
                >
                  <BarChart3 className="h-4 w-4 mr-2 flex-shrink-0" />
                  <span className="truncate">View Campaigns</span>
                </Button>
                <Button 
                  variant="outline" 
                  className="justify-start text-xs sm:text-sm bg-white hover:bg-blue-100 w-full"
                  onClick={() => {
                    setNotImplementedFeature('Export Contacts')
                    setShowNotImplementedModal(true)
                  }}
                >
                  <Download className="h-4 w-4 mr-2 flex-shrink-0" />
                  <span className="truncate">Export Contacts</span>
                </Button>
                <Button 
                  variant="outline" 
                  className="justify-start text-xs sm:text-sm bg-white hover:bg-blue-100 w-full"
                  onClick={() => {
                    setNotImplementedFeature('Advanced Filters')
                    setShowNotImplementedModal(true)
                  }}
                >
                  <Filter className="h-4 w-4 mr-2 flex-shrink-0" />
                  <span className="truncate">Advanced Filters</span>
                </Button>
              </div>
            </div>

            {/* Search and Filter */}
                <div className="bg-white py-3 sm:py-4 border-b border-gray-100 mb-4">
                  <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
                    <div className="flex-1">
                      <Input
                        placeholder="Search contacts..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full"
                      />
                    </div>
                    <Select value={statusFilter} onValueChange={setStatusFilter}>
                      <SelectTrigger className="w-full sm:w-40">
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
                </div>

                {/* Contact Table - Fixed height with scrolling */}
                <div className="border rounded-lg overflow-hidden">
                  <div className="max-h-[400px] sm:max-h-[500px] lg:max-h-[600px] overflow-y-auto">
                    <ContactTableView 
                      contacts={filteredContacts} 
                      onContactUpdate={handleContactUpdate}
                      onContactDelete={handleContactDelete}
                      currentUser={{
                        id: user.id,
                        email: user.email,
                        name: [user.first_name, user.last_name].filter(Boolean).join(' ') || user.email,
                        role: user.role,
                        tenant_id: user.tenant_id
                      }}
                    />
                  </div>
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
        </div>
          </TabsContent>

          <TabsContent value="templates">
            {/* Email Templates */}
            <Card className="w-full">
              <CardHeader>
                <CardTitle className="flex items-center">
                  <FileText className="h-5 w-5 mr-2" />
                  Email Templates ({emailTemplates.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="w-full">
                {templatesLoading ? (
                  <div className="text-center py-8">
                    <div className="animate-pulse">Loading templates...</div>
                  </div>
                ) : emailTemplates.length === 0 ? (
                  <div className="text-center py-8">
                    <FileText className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No Email Templates</h3>
                    <p className="text-gray-600 mb-4">Upload your first email template to get started.</p>
                    <Button onClick={() => setShowTemplateUpload(true)}>
                      <Upload className="h-4 w-4 mr-2" />
                      Upload Template
                    </Button>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 w-full">
                    {emailTemplates.map((template) => (
                      <Card key={template.id} className="border border-gray-200">
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between mb-3">
                            <div className="flex-1 min-w-0">
                              <h4 className="font-medium text-gray-900 truncate">{template.name}</h4>
                              <p className="text-sm text-gray-600 truncate">{template.subject}</p>
                            </div>
                            <div className="flex items-center gap-1 ml-2 flex-shrink-0">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setSelectedTemplate(template)
                                  setIsEditingTemplate(false)
                                  setShowTemplateView(true)
                                }}
                                title="View template"
                              >
                                <Eye className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setSelectedTemplate(template)
                                  startEditingTemplate(template)
                                  setShowTemplateView(true)
                                }}
                                title="Edit template"
                              >
                                <Edit className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleTemplateDelete(template.id)}
                                className="text-red-600 hover:text-red-700"
                                title="Delete template"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>
                          
                          <div className="space-y-2">
                            <div className="flex items-center justify-between text-xs text-gray-500">
                              <span>Variables: {template.variables.length}</span>
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
                            
                            <p className="text-xs text-gray-500">
                              Created: {new Date(template.created_at).toLocaleDateString()}
                            </p>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Add Contact Dialog */}
      <Dialog open={showAddContact} onOpenChange={setShowAddContact}>
        <DialogContent className="w-[95vw] max-w-[95vw] sm:max-w-2xl max-h-[95vh] overflow-y-auto bg-white border border-gray-200 shadow-lg">
          <DialogHeader>
            <DialogTitle className="text-gray-900">Add New Contact</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateContact} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
        <DialogContent className="w-[98vw] max-w-[98vw] sm:max-w-[95vw] lg:max-w-[1000px] xl:max-w-[1200px] max-h-[95vh] overflow-y-auto bg-white border border-gray-200 shadow-lg">
          <DialogHeader>
            <DialogTitle className="text-gray-900 flex items-center gap-2">
              <Upload className="h-5 w-5" />
              Import Contacts from CSV
              <div className="ml-auto flex items-center gap-2 hidden sm:flex">
                {importStep === 'upload' && <span className="text-xs sm:text-sm bg-blue-100 text-blue-800 px-2 py-1 rounded">Step 1: Upload</span>}
                {importStep === 'mapping' && <span className="text-xs sm:text-sm bg-blue-100 text-blue-800 px-2 py-1 rounded">Step 2: Map Fields</span>}
                {importStep === 'results' && <span className="text-xs sm:text-sm bg-green-100 text-green-800 px-2 py-1 rounded">Step 3: Results</span>}
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

      {/* Template Upload Dialog */}
      <Dialog open={showTemplateUpload} onOpenChange={setShowTemplateUpload}>
        <DialogContent className="w-[95vw] max-w-[95vw] sm:max-w-[80vw] lg:max-w-[900px] xl:max-w-[1000px] bg-white border border-gray-200 shadow-lg">
          <DialogHeader>
            <DialogTitle className="text-gray-900">Upload Email Template</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleTemplateUpload} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="template-name">Template Name *</Label>
                <Input
                  id="template-name"
                  value={templateName}
                  onChange={(e) => setTemplateName(e.target.value)}
                  placeholder="e.g., Welcome Email"
                  className="w-full"
                  required
                />
              </div>
              <div>
                <Label htmlFor="template-subject">Email Subject *</Label>
                <Input
                  id="template-subject"
                  value={templateSubject}
                  onChange={(e) => setTemplateSubject(e.target.value)}
                  placeholder="e.g., Welcome to {{organization_name}}"
                  className="w-full"
                  required
                />
              </div>
            </div>
            
            <div>
              <Label htmlFor="template-file">HTML File *</Label>
              <Input
                id="template-file"
                type="file"
                accept=".html,.htm"
                className="w-full"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  setTemplateFile(file || null)
                }}
                required
              />
              <p className="text-sm text-gray-600 mt-1">
                Upload an HTML file with your email template. Use &#123;&#123;variable&#125;&#125; for dynamic content.
              </p>
            </div>
            
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setShowTemplateUpload(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Uploading...' : 'Upload Template'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Feature Not Implemented Modal */}
      <Dialog open={showNotImplementedModal} onOpenChange={setShowNotImplementedModal}>
        <DialogContent className="w-[95vw] max-w-md bg-white border border-gray-200 shadow-lg">
          <DialogHeader>
            <DialogTitle className="text-gray-900 flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-orange-500" />
              Feature Not Available
            </DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-gray-600">
              <strong>{notImplementedFeature}</strong> is not yet implemented. This feature is coming soon!
            </p>
          </div>
          <div className="flex justify-end">
            <Button 
              variant="outline" 
              onClick={() => setShowNotImplementedModal(false)}
            >
              OK
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Create Template Dialog */}
      <Dialog open={showCreateTemplate} onOpenChange={setShowCreateTemplate}>
        <DialogContent className="w-[98vw] max-w-[98vw] sm:max-w-[95vw] lg:max-w-[1200px] xl:max-w-[1400px] h-[95vh] flex flex-col bg-white border border-gray-200 shadow-lg overflow-hidden">
          <DialogHeader>
            <DialogTitle className="text-gray-900 flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Create New Email Template
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateTemplate} className="space-y-4 flex-1 overflow-y-auto min-h-0">
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 xl:gap-6 h-full min-h-0">
              {/* Left Column - Form */}
              <div className="space-y-4 min-w-0 overflow-y-auto">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="new-template-name">Template Name *</Label>
                    <Input
                      id="new-template-name"
                      value={newTemplateName}
                      onChange={(e) => setNewTemplateName(e.target.value)}
                      placeholder="e.g., Welcome Email"
                      className="w-full"
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="new-template-subject">Email Subject *</Label>
                    <Input
                      id="new-template-subject"
                      value={newTemplateSubject}
                      onChange={(e) => setNewTemplateSubject(e.target.value)}
                      placeholder="e.g., Welcome to {{organization_name}}"
                      className="w-full"
                      required
                    />
                  </div>
                </div>
                
                <div className="flex-1 min-h-0">
                  <Label htmlFor="new-template-content">HTML Content *</Label>
                  <Textarea
                    id="new-template-content"
                    value={newTemplateContent}
                    onChange={(e) => setNewTemplateContent(e.target.value)}
                    className="font-mono text-sm w-full resize-none min-h-[400px] sm:min-h-[500px] lg:min-h-[600px]"
                    placeholder={`Enter HTML content with {{variable}} placeholders...

Example:
<h2>Welcome {{contact_name}}!</h2>
<p>Thank you for your interest in {{organization_name}}.</p>
<p>We're excited to work with {{business_name}}.</p>
<p>Best regards,<br>{{organization_name}} Team</p>`}
                    required
                  />
                  <p className="text-sm text-gray-600 mt-2">
                    Available variables: &#123;&#123;contact_name&#125;&#125;, &#123;&#123;business_name&#125;&#125;, &#123;&#123;organization_name&#125;&#125;, etc.
                  </p>
                </div>
                
                <div className="flex justify-end gap-2 pt-4">
                  <Button type="button" variant="outline" onClick={() => {
                    setNewTemplateName('')
                    setNewTemplateSubject('')
                    setNewTemplateContent('')
                    setShowCreateTemplate(false)
                  }}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={isSubmitting}>
                    {isSubmitting ? 'Creating...' : 'Create Template'}
                  </Button>
                </div>
              </div>
              
              {/* Right Column - Preview */}
              <div className="flex-1 min-w-0 overflow-y-auto">
                <Label className="text-sm font-medium">Live Preview</Label>
                <div className="border rounded p-4 bg-gray-50 h-[400px] sm:h-[500px] lg:h-[600px] mt-2">
                  {newTemplateContent ? (
                    <iframe
                      srcDoc={newTemplateContent}
                      className="w-full h-full border rounded"
                      title="Email Template Preview"
                    />
                  ) : (
                    <div className="flex items-center justify-center h-full text-gray-500">
                      <p>Preview will appear here as you type...</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Template View Dialog */}
      <Dialog open={showTemplateView} onOpenChange={setShowTemplateView}>
        <DialogContent className="w-[98vw] max-w-[98vw] sm:max-w-[95vw] lg:max-w-[1200px] xl:max-w-[1400px] h-[95vh] flex flex-col bg-white border border-gray-200 shadow-lg overflow-hidden">
          <DialogHeader>
            <DialogTitle className="text-gray-900 flex items-center gap-2">
              <FileText className="h-5 w-5" />
              {isEditingTemplate ? 'Edit Template' : selectedTemplate?.name}
            </DialogTitle>
          </DialogHeader>
          {selectedTemplate && (
            <div className="space-y-4 flex-1 overflow-y-auto min-h-0">
              {isEditingTemplate ? (
                // Edit Mode
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 xl:gap-6 h-full min-h-0">
                  {/* Left Column - Form */}
                  <div className="space-y-4 min-w-0 overflow-y-auto">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="edit-name">Template Name</Label>
                        <Input
                          id="edit-name"
                          value={editTemplateName}
                          onChange={(e) => setEditTemplateName(e.target.value)}
                          className="w-full"
                        />
                      </div>
                      <div>
                        <Label htmlFor="edit-subject">Email Subject</Label>
                        <Input
                          id="edit-subject"
                          value={editTemplateSubject}
                          onChange={(e) => setEditTemplateSubject(e.target.value)}
                          className="w-full"
                        />
                      </div>
                    </div>
                    
                    <div className="flex-1 min-h-0">
                      <Label htmlFor="edit-content">HTML Content</Label>
                      <Textarea
                        id="edit-content"
                        value={editTemplateContent}
                        onChange={(e) => setEditTemplateContent(e.target.value)}
                        className="font-mono text-sm w-full resize-none min-h-[400px] sm:min-h-[500px] lg:min-h-[600px] xl:min-h-[700px]"
                        placeholder="Enter HTML content with {{variable}} placeholders..."
                      />
                    </div>
                    
                    <div className="flex justify-end gap-2 pt-4">
                      <Button variant="outline" onClick={() => setIsEditingTemplate(false)}>
                        Cancel
                      </Button>
                      <Button onClick={handleTemplateUpdate} disabled={isSubmitting}>
                        {isSubmitting ? 'Saving...' : 'Save Changes'}
                      </Button>
                    </div>
                  </div>
                  
                  {/* Right Column - Preview */}
                  <div className="flex-1 min-w-0 overflow-y-auto">
                    <Label className="text-sm font-medium">Live Preview</Label>
                    <div className="border rounded p-4 bg-gray-50 h-[400px] sm:h-[500px] lg:h-[600px] xl:h-[700px] mt-2">
                      <iframe
                        srcDoc={editTemplateContent}
                        className="w-full h-full border rounded"
                        title="Email Template Preview"
                      />
                    </div>
                  </div>
                </div>
              ) : (
                // View Mode
                <>
                  <div className="grid grid-cols-1 gap-4">
                    <div>
                      <Label className="text-sm font-medium">Subject</Label>
                      <p className="text-sm text-gray-600 border rounded p-2">{selectedTemplate.subject}</p>
                    </div>
                  </div>
                  
                  {selectedTemplate.variables.length > 0 && (
                    <div>
                      <Label className="text-sm font-medium">Variables ({selectedTemplate.variables.length})</Label>
                      <div className="flex flex-wrap gap-2 mt-2">
                        {selectedTemplate.variables.map((variable) => (
                          <Badge key={variable} variant="outline">
                            &#123;&#123;{variable}&#125;&#125;
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="flex-1">
                      <Label className="text-sm font-medium">HTML Preview</Label>
                      <div className="border rounded p-4 bg-gray-50 h-[400px] mt-2">
                        <iframe
                          srcDoc={selectedTemplate.html_content}
                          className="w-full h-full border rounded"
                          title="Email Template Preview"
                        />
                      </div>
                    </div>
                    
                    <div className="flex-1">
                      <Label className="text-sm font-medium">HTML Source</Label>
                      <pre className="text-xs bg-gray-100 p-4 rounded border overflow-auto h-[400px] mt-2">
                        {selectedTemplate.html_content}
                      </pre>
                    </div>
                  </div>
                  
                  <div className="flex justify-between gap-2">
                    <Button variant="outline" onClick={() => startEditingTemplate(selectedTemplate)}>
                      <Edit className="h-4 w-4 mr-2" />
                      Edit Template
                    </Button>
                    <Button variant="outline" onClick={() => setShowTemplateView(false)}>
                      Close
                    </Button>
                  </div>
                </>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}