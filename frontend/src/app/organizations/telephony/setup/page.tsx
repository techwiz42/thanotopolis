// frontend/src/app/organizations/telephony/setup/page.tsx
'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Phone, CheckCircle, AlertCircle, ArrowLeft } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

import { telephonyService, TelephonyConfig, BusinessHours } from '@/services/telephony';
import { BusinessHoursEditor } from '../components/BusinessHoursEditor';
import { PhoneVerificationModal } from '../components/PhoneVerificationModal';
import { ForwardingInstructionsModal } from '../components/ForwardingInstructionsModal';

export default function TelephonySetupPage() {
  const router = useRouter();
  const { token, user } = useAuth();
  const { toast } = useToast();

  // State
  const [isLoading, setIsLoading] = useState(false);
  const [isCheckingExisting, setIsCheckingExisting] = useState(true);
  const [existingConfig, setExistingConfig] = useState<TelephonyConfig | null>(null);
  const [showVerificationModal, setShowVerificationModal] = useState(false);

  // Form state
  const [phoneNumber, setPhoneNumber] = useState('');
  const [welcomeMessage, setWelcomeMessage] = useState(
    'Hello! Thank you for calling. How can our AI assistant help you today?'
  );
  const [businessHours, setBusinessHours] = useState<BusinessHours>(
    telephonyService.getDefaultBusinessHours()
  );
  const [maxConcurrentCalls, setMaxConcurrentCalls] = useState(5);
  const [recordCalls, setRecordCalls] = useState(true);
  const [transcriptCalls, setTranscriptCalls] = useState(true);

  // Verification state
  const [phoneNumberError, setPhoneNumberError] = useState('');
  const [showForwardingInstructions, setShowForwardingInstructions] = useState(false);
  const [forwardingInstructions, setForwardingInstructions] = useState('');

  // Check for existing configuration
  useEffect(() => {
    const checkExistingConfig = async () => {
      if (!token) return;

      try {
        const config = await telephonyService.getTelephonyConfig(token);
        setExistingConfig(config);
        
        // Populate form with existing values
        setPhoneNumber(config.organization_phone_number);
        setWelcomeMessage(config.welcome_message || '');
        setBusinessHours(config.business_hours || telephonyService.getDefaultBusinessHours());
        setMaxConcurrentCalls(config.max_concurrent_calls);
        setRecordCalls(config.record_calls);
        setTranscriptCalls(config.transcript_calls);
        
        // Load forwarding instructions if setup is incomplete
        if (!telephonyService.isSetupComplete(config)) {
          try {
            const instructionsResponse = await telephonyService.getForwardingInstructions(token);
            setForwardingInstructions(instructionsResponse.instructions);
          } catch (error) {
            console.error('Error loading forwarding instructions:', error);
          }
        }
      } catch (error) {
        // No existing config found, which is fine
        console.log('No existing telephony config found');
      } finally {
        setIsCheckingExisting(false);
      }
    };

    checkExistingConfig();
  }, [token]);

  // Validate phone number
  const validatePhoneNumber = (number: string) => {
    if (!number.trim()) {
      setPhoneNumberError('Phone number is required');
      return false;
    }

    if (!telephonyService.validatePhoneNumber(number)) {
      setPhoneNumberError('Please enter a valid US phone number');
      return false;
    }

    setPhoneNumberError('');
    return true;
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!token) {
      toast({
        title: "Authentication Required",
        description: "Please log in to set up telephony",
        variant: "destructive"
      });
      return;
    }

    if (!validatePhoneNumber(phoneNumber)) {
      return;
    }

    setIsLoading(true);

    try {
      const setupData = {
        organization_phone_number: phoneNumber,
        welcome_message: welcomeMessage,
        business_hours: businessHours,
        max_concurrent_calls: maxConcurrentCalls
      };

      const config = await telephonyService.setupTelephony(setupData, token);
      
      toast({
        title: "Telephony Setup Successful",
        description: "Your phone number has been configured. Next, verify it and set up call forwarding.",
      });

      setExistingConfig(config);
      
      // Load forwarding instructions
      try {
        const instructionsResponse = await telephonyService.getForwardingInstructions(token);
        setForwardingInstructions(instructionsResponse.instructions);
      } catch (error) {
        console.error('Error loading forwarding instructions:', error);
      }
      
      // Show verification modal if not already verified
      if (config.verification_status !== 'verified') {
        setShowVerificationModal(true);
      }

    } catch (error: any) {
      console.error('Error setting up telephony:', error);
      
      let errorMessage = 'Failed to set up telephony';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }

      toast({
        title: "Setup Failed",
        description: errorMessage,
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Handle verification success
  const handleVerificationSuccess = () => {
    setShowVerificationModal(false);
    toast({
      title: "Phone Verified Successfully",
      description: "Your phone number is now verified and ready to receive calls.",
    });
    
    // Refresh the config
    if (token) {
      telephonyService.getTelephonyConfig(token)
        .then((config) => {
          setExistingConfig(config);
        })
        .catch(console.error);
    }
  };

  if (isCheckingExisting) {
    return (
      <div className="container mx-auto py-8">
        <div className="flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin" />
          <span className="ml-2">Checking existing configuration...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 max-w-4xl">
      {/* Header */}
      <div className="flex items-center mb-8">
        <Button
          variant="ghost"
          onClick={() => router.back()}
          className="mr-4"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
        <div>
          <h1 className="text-3xl font-bold">Telephony Setup</h1>
          <p className="text-muted-foreground">
            Configure AI-powered phone support for your organization
          </p>
        </div>
      </div>

      {/* Existing Configuration Alert */}
      {existingConfig && (
        <Alert className="mb-6">
          <Phone className="h-4 w-4" />
          <AlertDescription>
            <div className="flex items-center justify-between">
                <div>
                  <strong>Your Business Number:</strong> {telephonyService.getDisplayPhoneNumber(existingConfig)}
                  <br />
                  <strong>Platform Number:</strong> {telephonyService.getPlatformPhoneNumber(existingConfig)}
                  <div className="flex items-center mt-2 space-x-2">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      telephonyService.getVerificationStatusColor(existingConfig.verification_status)
                    }`}>
                      {existingConfig.verification_status === 'verified' ? (
                        <CheckCircle className="w-3 h-3 mr-1" />
                      ) : (
                        <AlertCircle className="w-3 h-3 mr-1" />
                      )}
                      {existingConfig.verification_status}
                    </span>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      existingConfig.call_forwarding_enabled ? 'bg-green-100 text-green-800' : 'bg-orange-100 text-orange-800'
                    }`}>
                      {existingConfig.call_forwarding_enabled ? 'Forwarding Active' : 'Forwarding Setup Required'}
                    </span>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      existingConfig.is_enabled ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {existingConfig.is_enabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => router.push('/organizations/telephony/calls')}
                  >
                    View Calls
                  </Button>
                  {existingConfig.verification_status !== 'verified' && (
                    <Button
                      size="sm"
                      onClick={() => setShowVerificationModal(true)}
                    >
                      Verify Number
                    </Button>
                  )}
                  {existingConfig.verification_status === 'verified' && !existingConfig.call_forwarding_enabled && (
                    <Button
                      size="sm"
                      onClick={() => setShowForwardingInstructions(true)}
                    >
                      Setup Forwarding
                    </Button>
                  )}
                </div>
              </div>
              
              {/* Setup Status */}
              <div className="mt-2 text-sm text-muted-foreground">
                <strong>Status:</strong> {telephonyService.getSetupStatus(existingConfig)}
              </div>
          </AlertDescription>
        </Alert>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Configuration */}
        <Card>
          <CardHeader>
            <CardTitle>Business Phone Number</CardTitle>
            <CardDescription>
              Enter your organization's existing phone number that customers currently call
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="phoneNumber">Your Business Phone Number</Label>
              <Input
                id="phoneNumber"
                type="tel"
                placeholder="(555) 123-4567"
                value={phoneNumber}
                onChange={(e) => {
                  setPhoneNumber(e.target.value);
                  setPhoneNumberError('');
                }}
                className={phoneNumberError ? 'border-red-500' : ''}
              />
              {phoneNumberError && (
                <p className="text-sm text-red-500">{phoneNumberError}</p>
              )}
              <div className="p-3 bg-blue-50 rounded-lg">
                <p className="text-sm text-blue-700">
                  <strong>How it works:</strong>
                </p>
                <ul className="text-sm text-blue-600 mt-1 space-y-1">
                  <li>• Keep your existing phone number</li>
                  <li>• We'll verify you own this number</li>
                  <li>• We'll provide a platform number for call forwarding</li>
                  <li>• Customers still dial your familiar business number</li>
                </ul>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="welcomeMessage">AI Welcome Message</Label>
              <Textarea
                id="welcomeMessage"
                placeholder="Hello! Thank you for calling..."
                value={welcomeMessage}
                onChange={(e) => setWelcomeMessage(e.target.value)}
                rows={3}
              />
              <p className="text-sm text-muted-foreground">
                This message will be spoken by the AI when customers call your number.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Business Hours */}
        <Card>
          <CardHeader>
            <CardTitle>Business Hours</CardTitle>
            <CardDescription>
              Configure when your AI phone support is available
            </CardDescription>
          </CardHeader>
          <CardContent>
            <BusinessHoursEditor
              businessHours={businessHours}
              onChange={setBusinessHours}
            />
          </CardContent>
        </Card>

        {/* Advanced Settings */}
        <Card>
          <CardHeader>
            <CardTitle>Advanced Settings</CardTitle>
            <CardDescription>
              Configure call handling and recording preferences
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="maxCalls">Maximum Concurrent Calls</Label>
              <Input
                id="maxCalls"
                type="number"
                min="1"
                max="50"
                value={maxConcurrentCalls}
                onChange={(e) => setMaxConcurrentCalls(parseInt(e.target.value) || 5)}
              />
              <p className="text-sm text-muted-foreground">
                Maximum number of calls that can be handled simultaneously.
              </p>
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Record Calls</Label>
                <p className="text-sm text-muted-foreground">
                  Record all phone calls for quality assurance
                </p>
              </div>
              <Switch
                checked={recordCalls}
                onCheckedChange={setRecordCalls}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Transcript Calls</Label>
                <p className="text-sm text-muted-foreground">
                  Generate text transcripts of all calls
                </p>
              </div>
              <Switch
                checked={transcriptCalls}
                onCheckedChange={setTranscriptCalls}
              />
            </div>
          </CardContent>
        </Card>

        {/* Call Forwarding Setup */}
        {existingConfig && existingConfig.verification_status === 'verified' && !existingConfig.call_forwarding_enabled && (
          <Card>
            <CardHeader>
              <CardTitle>Call Forwarding Setup</CardTitle>
              <CardDescription>
                Set up call forwarding to activate AI phone support
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    <strong>Next Step:</strong> Set up call forwarding from your business phone to our platform number.
                  </AlertDescription>
                </Alert>
                
                <div className="flex items-center justify-between p-4 border rounded-lg">
                  <div>
                    <p className="font-medium">Your Platform Number</p>
                    <p className="text-2xl font-bold text-blue-600">
                      {telephonyService.getPlatformPhoneNumber(existingConfig)}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Forward calls from {telephonyService.getDisplayPhoneNumber(existingConfig)} to this number
                    </p>
                  </div>
                  <Button onClick={() => setShowForwardingInstructions(true)}>
                    View Instructions
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Success Status */}
        {existingConfig && telephonyService.isSetupComplete(existingConfig) && (
          <Card>
            <CardHeader>
              <CardTitle className="text-green-700">✅ AI Phone Support Active</CardTitle>
              <CardDescription>
                Your phone system is configured and ready to handle calls
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium">Business Number</p>
                  <p className="text-lg">{telephonyService.getDisplayPhoneNumber(existingConfig)}</p>
                </div>
                <div>
                  <p className="text-sm font-medium">Platform Number</p>
                  <p className="text-lg">{telephonyService.getPlatformPhoneNumber(existingConfig)}</p>
                </div>
              </div>
              <div className="mt-4 flex gap-2">
                <Button 
                  variant="outline"
                  onClick={() => router.push('/organizations/telephony/calls')}
                >
                  View Call Dashboard
                </Button>
                <Button 
                  variant="outline"
                  onClick={() => setShowForwardingInstructions(true)}
                >
                  View Setup Instructions
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Submit Button */}
        <div className="flex justify-end">
          <Button type="submit" disabled={isLoading}>
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {existingConfig ? 'Update Configuration' : 'Set Up Telephony'}
          </Button>
        </div>
      </form>

      {/* Verification Modal */}
      {showVerificationModal && existingConfig && (
        <PhoneVerificationModal
          isOpen={showVerificationModal}
          onClose={() => setShowVerificationModal(false)}
          onSuccess={handleVerificationSuccess}
          phoneNumber={telephonyService.getDisplayPhoneNumber(existingConfig)}
        />
      )}

      {/* Forwarding Instructions Modal */}
      {showForwardingInstructions && (
        <ForwardingInstructionsModal
          isOpen={showForwardingInstructions}
          onClose={() => setShowForwardingInstructions(false)}
          instructions={forwardingInstructions}
          organizationNumber={existingConfig ? telephonyService.getDisplayPhoneNumber(existingConfig) : ''}
          platformNumber={existingConfig ? telephonyService.getPlatformPhoneNumber(existingConfig) : ''}
        />
      )}
    </div>
  );
}
