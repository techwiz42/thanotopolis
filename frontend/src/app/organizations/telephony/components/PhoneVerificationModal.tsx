// frontend/src/app/organizations/telephony/components/PhoneVerificationModal.tsx
'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Phone, MessageSquare, CheckCircle, AlertCircle } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';

import { telephonyService } from '@/services/telephony';

interface PhoneVerificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  phoneNumber: string;
}

export const PhoneVerificationModal: React.FC<PhoneVerificationModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  phoneNumber
}) => {
  const { token } = useAuth();
  const { toast } = useToast();

  // State
  const [step, setStep] = useState<'initiate' | 'verify'>('initiate');
  const [isLoading, setIsLoading] = useState(false);
  const [verificationCode, setVerificationCode] = useState('');
  const [error, setError] = useState('');
  const [countdown, setCountdown] = useState(0);
  const [canResend, setCanResend] = useState(true);

  // Countdown timer
  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    } else if (countdown === 0 && step === 'verify') {
      setCanResend(true);
    }
  }, [countdown, step]);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setStep('initiate');
      setVerificationCode('');
      setError('');
      setCountdown(0);
      setCanResend(true);
    }
  }, [isOpen]);

  // Initiate verification
  const handleInitiateVerification = async () => {
    if (!token) return;

    setIsLoading(true);
    setError('');

    try {
      const response = await telephonyService.initiateVerification(token);
      
      if (response.success) {
        setStep('verify');
        setCountdown(60); // 60 second cooldown
        setCanResend(false);
        
        toast({
          title: "Verification Code Sent",
          description: "Please check your phone for the verification code.",
        });
      } else {
        setError(response.message);
      }
    } catch (error: any) {
      console.error('Error initiating verification:', error);
      
      let errorMessage = 'Failed to send verification code';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Confirm verification
  const handleConfirmVerification = async () => {
    if (!token || !verificationCode.trim()) return;

    if (verificationCode.length !== 6) {
      setError('Please enter a 6-digit verification code');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const response = await telephonyService.confirmVerification(verificationCode, token);
      
      if (response.success) {
        toast({
          title: "Phone Verified Successfully",
          description: "Your phone number is now verified and ready to receive calls.",
        });
        
        onSuccess();
      } else {
        setError(response.message);
      }
    } catch (error: any) {
      console.error('Error confirming verification:', error);
      
      let errorMessage = 'Invalid verification code';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle verification code input
  const handleCodeInputChange = (value: string) => {
    // Only allow digits and limit to 6 characters
    const cleanValue = value.replace(/\D/g, '').slice(0, 6);
    setVerificationCode(cleanValue);
    setError('');
  };

  // Handle key press for automatic submission
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      if (step === 'initiate') {
        handleInitiateVerification();
      } else {
        handleConfirmVerification();
      }
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center">
            <Phone className="w-5 h-5 mr-2" />
            Verify Phone Number
          </DialogTitle>
          <DialogDescription>
            {step === 'initiate' 
              ? 'We need to verify that you own this phone number.'
              : 'Enter the 6-digit code we sent to your phone.'
            }
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Phone Number Display */}
          <div className="flex items-center justify-center p-4 bg-gray-50 rounded-lg">
            <Phone className="w-4 h-4 mr-2 text-muted-foreground" />
            <span className="font-medium">{phoneNumber}</span>
          </div>

          {step === 'initiate' ? (
            // Initiate Verification Step
            <div className="space-y-4">
              <div className="text-center space-y-2">
                <MessageSquare className="w-12 h-12 mx-auto text-blue-500" />
                <p className="text-sm text-muted-foreground">
                  We'll send a 6-digit verification code to your phone via SMS.
                </p>
              </div>

              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <div className="flex space-x-2">
                <Button variant="outline" onClick={onClose} className="flex-1">
                  Cancel
                </Button>
                <Button 
                  onClick={handleInitiateVerification} 
                  disabled={isLoading}
                  className="flex-1"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Sending...
                    </>
                  ) : (
                    'Send Code'
                  )}
                </Button>
              </div>
            </div>
          ) : (
            // Verify Code Step
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="verification-code">Verification Code</Label>
                <Input
                  id="verification-code"
                  type="text"
                  placeholder="000000"
                  value={verificationCode}
                  onChange={(e) => handleCodeInputChange(e.target.value)}
                  onKeyPress={handleKeyPress}
                  className="text-center text-lg tracking-widest"
                  maxLength={6}
                  autoFocus
                />
                <p className="text-xs text-muted-foreground text-center">
                  Enter the 6-digit code sent to your phone
                </p>
              </div>

              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {/* Resend Code */}
              <div className="text-center">
                {countdown > 0 ? (
                  <p className="text-sm text-muted-foreground">
                    Resend code in {countdown} seconds
                  </p>
                ) : (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleInitiateVerification}
                    disabled={isLoading || !canResend}
                  >
                    Resend Code
                  </Button>
                )}
              </div>

              <div className="flex space-x-2">
                <Button 
                  variant="outline" 
                  onClick={() => setStep('initiate')} 
                  className="flex-1"
                  disabled={isLoading}
                >
                  Back
                </Button>
                <Button 
                  onClick={handleConfirmVerification} 
                  disabled={isLoading || verificationCode.length !== 6}
                  className="flex-1"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Verifying...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-4 h-4 mr-2" />
                      Verify
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}

          {/* Help Text */}
          <div className="text-xs text-muted-foreground text-center space-y-1">
            <p>Having trouble? Make sure your phone can receive SMS messages.</p>
            <p>Standard messaging rates may apply.</p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
