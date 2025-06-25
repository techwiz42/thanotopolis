// src/components/telephony/TelephonySystemInitializer.tsx
'use client';

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { telephonyService } from '@/services/telephony';
import { incomingCallHandler } from '@/services/telephony/IncomingCallHandler';
import { telephonyErrorHandler } from '@/services/telephony/TelephonyErrorHandler';

/**
 * Component that initializes the telephony system when conditions are met
 * Should be included in the organization layout to handle incoming calls automatically
 */
export default function TelephonySystemInitializer() {
  const { token, user } = useAuth();
  const [isInitialized, setIsInitialized] = useState(false);
  const [initializationError, setInitializationError] = useState<string | null>(null);

  useEffect(() => {
    const initializeTelephonySystem = async () => {
      if (!token || !user || isInitialized) {
        return;
      }

      try {
        console.log('📞 TelephonySystemInitializer: Checking telephony configuration...');
        
        // Check if telephony is configured and enabled
        const config = await telephonyService.getTelephonyConfig(token);
        
        if (!config || !config.is_enabled) {
          console.log('📞 TelephonySystemInitializer: Telephony not enabled, skipping initialization');
          return;
        }

        if (!telephonyService.isSetupComplete(config)) {
          console.log('📞 TelephonySystemInitializer: Telephony setup not complete, skipping initialization');
          return;
        }

        console.log('📞 TelephonySystemInitializer: Initializing telephony system...');

        // Initialize the incoming call handler
        await incomingCallHandler.initialize(token);

        setIsInitialized(true);
        setInitializationError(null);
        
        console.log('📞 TelephonySystemInitializer: Telephony system initialized successfully');

      } catch (error) {
        console.error('📞 TelephonySystemInitializer: Initialization failed:', error);
        setInitializationError(error instanceof Error ? error.message : 'Unknown error');
        
        telephonyErrorHandler.logError(
          'configuration' as any,
          'Telephony system initialization failed',
          'TelephonySystemInitializer',
          {
            severity: 'high' as any,
            error: error as Error,
            details: { userId: user.id }
          }
        );
      }
    };

    initializeTelephonySystem();

    // Cleanup on unmount
    return () => {
      if (isInitialized) {
        console.log('📞 TelephonySystemInitializer: Cleaning up telephony system...');
        incomingCallHandler.destroy();
      }
    };
  }, [token, user, isInitialized]);

  // This component doesn't render anything visible
  return null;
}

/**
 * Hook for components that need telephony system status
 */
export function useTelephonySystemStatus() {
  const [status, setStatus] = useState<{
    initialized: boolean;
    welcomeMessage: string;
    activeCalls: number;
  } | null>(null);

  useEffect(() => {
    const updateStatus = () => {
      try {
        const currentStatus = incomingCallHandler.getStatus();
        setStatus(currentStatus);
      } catch (error) {
        console.warn('📞 Error getting telephony status:', error);
        setStatus(null);
      }
    };

    // Initial status
    updateStatus();

    // Update every 5 seconds
    const interval = setInterval(updateStatus, 5000);

    return () => clearInterval(interval);
  }, []);

  return status;
}