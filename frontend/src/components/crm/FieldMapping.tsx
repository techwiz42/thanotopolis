import React from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { AlertTriangle, CheckCircle2 } from 'lucide-react'
import { FieldMapping, CRM_FIELDS, CRMFieldKey } from '@/utils/csvParser'

interface FieldMappingProps {
  mappings: FieldMapping[]
  onMappingChange: (mappings: FieldMapping[]) => void
  validationErrors: string[]
}

export default function FieldMappingComponent({ mappings, onMappingChange, validationErrors }: FieldMappingProps) {
  const handleFieldChange = (csvHeader: string, crmField: string | null) => {
    const updatedMappings = mappings.map(mapping => 
      mapping.csvHeader === csvHeader 
        ? { ...mapping, crmField: crmField as CRMFieldKey | null }
        : mapping
    )
    onMappingChange(updatedMappings)
  }

  const getAvailableFields = (currentMapping: FieldMapping): CRMFieldKey[] => {
    const usedFields = mappings
      .filter(m => m.csvHeader !== currentMapping.csvHeader && m.crmField)
      .map(m => m.crmField!)
    
    return Object.keys(CRM_FIELDS).filter(field => 
      !usedFields.includes(field as CRMFieldKey)
    ) as CRMFieldKey[]
  }

  const getMappedFieldsCount = () => {
    return mappings.filter(m => m.crmField).length
  }

  const getRequiredFieldsCount = () => {
    const requiredFields = Object.entries(CRM_FIELDS)
      .filter(([_, config]) => config.required)
      .map(([key, _]) => key)
    
    return mappings.filter(m => m.crmField && requiredFields.includes(m.crmField)).length
  }

  const totalRequiredFields = Object.values(CRM_FIELDS).filter(config => config.required).length

  return (
    <div className="space-y-4">
      {/* Mapping Status */}
      <div className="bg-gray-50 rounded-lg p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-medium text-gray-900">Mapping Status</h3>
          <div className="flex items-center gap-2">
            {validationErrors.length === 0 ? (
              <Badge variant="default" className="bg-green-100 text-green-800">
                <CheckCircle2 className="h-3 w-3 mr-1" />
                Ready to Import
              </Badge>
            ) : (
              <Badge variant="destructive">
                <AlertTriangle className="h-3 w-3 mr-1" />
                {validationErrors.length} Error{validationErrors.length !== 1 ? 's' : ''}
              </Badge>
            )}
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-600">CSV Columns:</span>
            <span className="ml-2 font-medium">{mappings.length}</span>
          </div>
          <div>
            <span className="text-gray-600">Mapped Fields:</span>
            <span className="ml-2 font-medium">{getMappedFieldsCount()}</span>
          </div>
          <div>
            <span className="text-gray-600">Required Fields Mapped:</span>
            <span className="ml-2 font-medium">{getRequiredFieldsCount()}/{totalRequiredFields}</span>
          </div>
        </div>

        {validationErrors.length > 0 && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded">
            <h4 className="text-sm font-medium text-red-800 mb-1">Validation Errors:</h4>
            <ul className="text-sm text-red-700 space-y-1">
              {validationErrors.map((error, index) => (
                <li key={index}>• {error}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Field Mappings */}
      <div className="space-y-3">
        <h3 className="font-medium text-gray-900">Map CSV Columns to CRM Fields</h3>
        
        <div className="space-y-3 max-h-80 overflow-y-auto">
          {mappings.map((mapping, index) => {
            const availableFields = getAvailableFields(mapping)
            const isCurrentFieldUsed = mapping.crmField && mappings.some(m => 
              m.csvHeader !== mapping.csvHeader && m.crmField === mapping.crmField
            )
            
            return (
              <div key={mapping.csvHeader} className="grid grid-cols-2 gap-4 items-center p-3 border rounded-lg bg-white">
                <div>
                  <Label className="text-sm font-medium text-gray-900">
                    CSV Column: {mapping.csvHeader}
                  </Label>
                  {mapping.crmField && CRM_FIELDS[mapping.crmField]?.required && (
                    <Badge variant="outline" className="ml-2 text-xs">Required</Badge>
                  )}
                </div>
                
                <div>
                  <Select
                    value={mapping.crmField || 'none'}
                    onValueChange={(value) => handleFieldChange(mapping.csvHeader, value === 'none' ? null : value)}
                  >
                    <SelectTrigger className={isCurrentFieldUsed ? 'border-red-300' : ''}>
                      <SelectValue placeholder="Select CRM field..." />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">
                        <span className="text-gray-500">Don't import this column</span>
                      </SelectItem>
                      {availableFields.map(field => (
                        <SelectItem key={field} value={field}>
                          <div className="flex items-center gap-2">
                            <span>{CRM_FIELDS[field].label}</span>
                            {CRM_FIELDS[field].required && (
                              <Badge variant="outline" className="text-xs">Required</Badge>
                            )}
                          </div>
                        </SelectItem>
                      ))}
                      {mapping.crmField && !availableFields.includes(mapping.crmField) && (
                        <SelectItem value={mapping.crmField}>
                          <div className="flex items-center gap-2">
                            <span>{CRM_FIELDS[mapping.crmField].label}</span>
                            {CRM_FIELDS[mapping.crmField].required && (
                              <Badge variant="outline" className="text-xs">Required</Badge>
                            )}
                            {isCurrentFieldUsed && (
                              <Badge variant="destructive" className="text-xs">Duplicate</Badge>
                            )}
                          </div>
                        </SelectItem>
                      )}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Field Reference */}
      <div className="bg-blue-50 rounded-lg p-4">
        <h4 className="font-medium text-blue-900 mb-2">Available CRM Fields</h4>
        <div className="grid grid-cols-2 gap-2 text-sm">
          {Object.entries(CRM_FIELDS).map(([key, config]) => (
            <div key={key} className="flex items-center gap-2">
              <span className="text-blue-800">{config.label}</span>
              {config.required && (
                <Badge variant="outline" className="text-xs">Required</Badge>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}