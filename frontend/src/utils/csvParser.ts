export interface CSVParseResult {
  headers: string[]
  data: string[][]
  preview: Record<string, string>[]
}

export const CRM_FIELDS = {
  business_name: { label: 'Business Name', required: true },
  contact_name: { label: 'Contact Name', required: true },
  contact_email: { label: 'Email', required: false },
  contact_role: { label: 'Role', required: false },
  phone: { label: 'Phone', required: false },
  city: { label: 'City', required: false },
  state: { label: 'State', required: false },
  website: { label: 'Website', required: false },
  address: { label: 'Address', required: false },
  status: { label: 'Status', required: false },
  notes: { label: 'Notes', required: false }
} as const

export type CRMFieldKey = keyof typeof CRM_FIELDS

export interface FieldMapping {
  csvHeader: string
  crmField: CRMFieldKey | null
  isRequired: boolean
}

export function parseCSV(csvText: string): CSVParseResult {
  const lines = csvText.trim().split('\n')
  if (lines.length < 2) {
    throw new Error('CSV must contain at least a header row and one data row')
  }

  // Parse headers (first row)
  const headers = parseCSVLine(lines[0])
  
  // Parse data rows
  const data: string[][] = []
  const preview: Record<string, string>[] = []
  
  for (let i = 1; i < Math.min(lines.length, 6); i++) { // Preview first 5 data rows
    const row = parseCSVLine(lines[i])
    data.push(row)
    
    // Create preview object
    const previewRow: Record<string, string> = {}
    headers.forEach((header, index) => {
      previewRow[header] = row[index] || ''
    })
    preview.push(previewRow)
  }

  return { headers, data, preview }
}

function parseCSVLine(line: string): string[] {
  const result: string[] = []
  let current = ''
  let inQuotes = false
  let i = 0

  while (i < line.length) {
    const char = line[i]
    const nextChar = line[i + 1]

    if (char === '"') {
      if (inQuotes && nextChar === '"') {
        // Escaped quote
        current += '"'
        i += 2
      } else {
        // Toggle quote state
        inQuotes = !inQuotes
        i++
      }
    } else if (char === ',' && !inQuotes) {
      // Field separator
      result.push(current.trim())
      current = ''
      i++
    } else {
      current += char
      i++
    }
  }

  result.push(current.trim())
  return result
}

export function createInitialMapping(headers: string[]): FieldMapping[] {
  return headers.map(header => ({
    csvHeader: header,
    crmField: autoMapField(header),
    isRequired: false
  }))
}

function autoMapField(header: string): CRMFieldKey | null {
  const normalizedHeader = header.toLowerCase().replace(/[^a-z0-9]/g, '')
  
  // Direct matches
  const directMatches: Record<string, CRMFieldKey> = {
    'businessname': 'business_name',
    'companyname': 'business_name',
    'company': 'business_name',
    'organization': 'business_name',
    'contactname': 'contact_name',
    'name': 'contact_name',
    'fullname': 'contact_name',
    'firstname': 'contact_name',
    'email': 'contact_email',
    'emailaddress': 'contact_email',
    'contactemail': 'contact_email',
    'phone': 'phone',
    'phonenumber': 'phone',
    'telephone': 'phone',
    'mobile': 'phone',
    'city': 'city',
    'state': 'state',
    'province': 'state',
    'region': 'state',
    'website': 'website',
    'url': 'website',
    'address': 'address',
    'streetaddress': 'address',
    'status': 'status',
    'notes': 'notes',
    'comments': 'notes',
    'description': 'notes',
    'role': 'contact_role',
    'title': 'contact_role',
    'position': 'contact_role',
    'jobtitle': 'contact_role'
  }

  // Check for direct match
  if (directMatches[normalizedHeader]) {
    return directMatches[normalizedHeader]
  }

  // Check for partial matches
  for (const [pattern, field] of Object.entries(directMatches)) {
    if (normalizedHeader.includes(pattern) || pattern.includes(normalizedHeader)) {
      return field
    }
  }

  return null
}

export function validateMapping(mappings: FieldMapping[]): { isValid: boolean; errors: string[] } {
  const errors: string[] = []
  const mappedFields = new Set<string>()

  // Check for required fields
  const requiredFields = Object.entries(CRM_FIELDS)
    .filter(([_, config]) => config.required)
    .map(([key, _]) => key)

  for (const requiredField of requiredFields) {
    const hasMappedField = mappings.some(m => m.crmField === requiredField)
    if (!hasMappedField) {
      errors.push(`Required field "${CRM_FIELDS[requiredField as CRMFieldKey].label}" is not mapped`)
    }
  }

  // Check for duplicate mappings
  for (const mapping of mappings) {
    if (mapping.crmField) {
      if (mappedFields.has(mapping.crmField)) {
        errors.push(`Field "${CRM_FIELDS[mapping.crmField as CRMFieldKey].label}" is mapped multiple times`)
      }
      mappedFields.add(mapping.crmField)
    }
  }

  return {
    isValid: errors.length === 0,
    errors
  }
}

export function generateFieldMappingJSON(mappings: FieldMapping[]): string {
  const mapping: Record<string, string> = {}
  
  for (const map of mappings) {
    if (map.crmField) {
      mapping[map.csvHeader] = map.crmField
    }
  }
  
  return JSON.stringify(mapping)
}