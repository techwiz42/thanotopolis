import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Eye, FileText } from 'lucide-react'

interface CSVPreviewProps {
  headers: string[]
  preview: Record<string, string>[]
  fileName?: string
}

export default function CSVPreview({ headers, preview, fileName }: CSVPreviewProps) {
  if (headers.length === 0 || preview.length === 0) {
    return null
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Eye className="h-5 w-5" />
          CSV Preview
          {fileName && (
            <Badge variant="outline" className="ml-2">
              <FileText className="h-3 w-3 mr-1" />
              {fileName}
            </Badge>
          )}
        </CardTitle>
        <p className="text-sm text-gray-600">
          Showing first {preview.length} rows of your CSV file
        </p>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse border border-gray-200 text-sm">
            <thead>
              <tr className="bg-gray-50">
                {headers.map((header, index) => (
                  <th 
                    key={index}
                    className="border border-gray-200 px-3 py-2 text-left font-medium text-gray-900"
                  >
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {preview.map((row, rowIndex) => (
                <tr key={rowIndex} className={rowIndex % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                  {headers.map((header, colIndex) => (
                    <td 
                      key={colIndex}
                      className="border border-gray-200 px-3 py-2 text-gray-700 max-w-xs truncate"
                      title={row[header] || ''}
                    >
                      {row[header] || (
                        <span className="text-gray-400 italic">empty</span>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {preview.length >= 5 && (
          <p className="text-xs text-gray-500 mt-2">
            ... and more rows in your CSV file
          </p>
        )}
      </CardContent>
    </Card>
  )
}