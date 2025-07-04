'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { ArrowLeft, Upload, Eye, Save } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';

export default function CreateTemplatePage() {
  const router = useRouter();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    subject: '',
    html_content: '',
    text_content: ''
  });

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (file.type !== 'text/html' && !file.name.endsWith('.html')) {
      toast({
        title: "Invalid file type",
        description: "Please upload an HTML file",
        variant: "destructive"
      });
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      setFormData(prev => ({
        ...prev,
        html_content: content,
        name: prev.name || file.name.replace('.html', '')
      }));
    };
    reader.readAsText(file);
  };

  const extractVariables = (htmlContent: string): string[] => {
    const variableRegex = /\{\{\s*([^}]+)\s*\}\}/g;
    const variables = new Set<string>();
    let match;
    
    while ((match = variableRegex.exec(htmlContent)) !== null) {
      variables.add(match[1].trim());
    }
    
    return Array.from(variables);
  };

  const handleSave = async () => {
    if (!formData.name.trim()) {
      toast({
        title: "Validation Error",
        description: "Template name is required",
        variant: "destructive"
      });
      return;
    }

    if (!formData.subject.trim()) {
      toast({
        title: "Validation Error",
        description: "Email subject is required",
        variant: "destructive"
      });
      return;
    }

    if (!formData.html_content.trim()) {
      toast({
        title: "Validation Error",
        description: "HTML content is required",
        variant: "destructive"
      });
      return;
    }

    setIsLoading(true);

    try {
      const variables = extractVariables(formData.html_content);
      
      const response = await fetch('/api/crm/email-templates', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...formData,
          variables
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create template');
      }

      toast({
        title: "Success",
        description: "Email template created successfully",
      });

      router.push('/organizations/crm?tab=templates');
    } catch (error) {
      console.error('Error creating template:', error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to create template",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const detectedVariables = extractVariables(formData.html_content);

  return (
    <div className="container mx-auto p-4 sm:p-6 max-w-none lg:max-w-7xl xl:max-w-8xl">
      <div className="mb-6">
        <Button
          variant="ghost"
          onClick={() => router.back()}
          className="mb-4"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to CRM
        </Button>
        <h1 className="text-2xl sm:text-3xl font-bold">Create Email Template</h1>
        <p className="text-sm sm:text-base text-gray-600 mt-2">
          Create a new email template for bulk email campaigns
        </p>
      </div>

      <div className={`grid grid-cols-1 gap-4 sm:gap-6 ${showPreview ? 'lg:grid-cols-2' : ''}`}>
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Template Details</CardTitle>
              <CardDescription className="text-sm">
                Enter the basic information for your email template
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 sm:space-y-4">
              <div>
                <Label htmlFor="name">Template Name *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                  placeholder="Welcome Email"
                  maxLength={100}
                />
              </div>

              <div>
                <Label htmlFor="subject">Email Subject *</Label>
                <Input
                  id="subject"
                  value={formData.subject}
                  onChange={(e) => handleInputChange('subject', e.target.value)}
                  placeholder="Welcome to {{organization_name}}"
                  maxLength={255}
                />
              </div>

              <div>
                <Label htmlFor="html_content">HTML Content *</Label>
                <Textarea
                  id="html_content"
                  value={formData.html_content}
                  onChange={(e) => handleInputChange('html_content', e.target.value)}
                  placeholder="Enter your HTML email template here..."
                  rows={12}
                  className="font-mono text-sm w-full min-h-[300px] sm:min-h-[400px] lg:min-h-[500px] resize-y"
                />
              </div>

              <div>
                <Label htmlFor="text_content">Text Content (Optional)</Label>
                <Textarea
                  id="text_content"
                  value={formData.text_content}
                  onChange={(e) => handleInputChange('text_content', e.target.value)}
                  placeholder="Plain text version of your email..."
                  rows={6}
                  className="w-full min-h-[150px] sm:min-h-[200px] resize-y"
                />
              </div>

              <div className="flex items-center gap-2 pt-4 border-t">
                <input
                  type="file"
                  accept=".html"
                  onChange={handleFileUpload}
                  className="hidden"
                  id="file-upload"
                />
                <Button
                  variant="outline"
                  onClick={() => document.getElementById('file-upload')?.click()}
                  className="flex-1 text-sm sm:text-base"
                >
                  <Upload className="h-4 w-4 mr-2" />
                  Upload HTML File
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setShowPreview(!showPreview)}
                  className="flex-1 text-sm sm:text-base"
                >
                  <Eye className="h-4 w-4 mr-2" />
                  {showPreview ? 'Hide' : 'Show'} Preview
                </Button>
              </div>
            </CardContent>
          </Card>

          {detectedVariables.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Detected Variables</CardTitle>
                <CardDescription>
                  These variables will be replaced with actual values when sending emails
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {detectedVariables.map((variable, index) => (
                    <span
                      key={index}
                      className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm"
                    >
                      {`{{${variable}}}`}
                    </span>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {showPreview && (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Email Preview</CardTitle>
                <CardDescription>
                  Preview of how your email will look
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="border rounded-lg p-4 bg-white">
                  <div className="border-b pb-2 mb-4">
                    <div className="text-sm text-gray-600">Subject:</div>
                    <div className="font-medium">{formData.subject || 'No subject'}</div>
                  </div>
                  <div 
                    className="prose max-w-none"
                    dangerouslySetInnerHTML={{ 
                      __html: formData.html_content || '<p class="text-gray-500">No content to preview</p>' 
                    }}
                  />
                </div>
              </CardContent>
            </Card>

            {formData.text_content && (
              <Card>
                <CardHeader>
                  <CardTitle>Text Version</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="border rounded-lg p-4 bg-gray-50">
                    <pre className="whitespace-pre-wrap text-sm">
                      {formData.text_content}
                    </pre>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>

      <div className="mt-6 sm:mt-8 flex flex-col sm:flex-row justify-end gap-3 sm:gap-4">
        <Button
          variant="outline"
          onClick={() => router.back()}
          disabled={isLoading}
        >
          Cancel
        </Button>
        <Button
          onClick={handleSave}
          disabled={isLoading}
        >
          <Save className="h-4 w-4 mr-2" />
          {isLoading ? 'Saving...' : 'Save Template'}
        </Button>
      </div>
    </div>
  );
}