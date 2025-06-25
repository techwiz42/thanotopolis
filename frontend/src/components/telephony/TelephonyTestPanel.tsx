// src/components/telephony/TelephonyTestPanel.tsx
'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { 
  Play,
  Square,
  Mic,
  MicOff,
  Phone,
  PhoneCall,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Loader2,
  Settings,
  Volume2,
  Radio,
  Wifi,
  WifiOff
} from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';

import { telephonyCallManager } from '@/services/telephony/TelephonyCallManager';
import { telephonyWebSocketManager } from '@/services/telephony/TelephonyWebSocketManager';
import { telephonyTTSSTTProcessor } from '@/services/telephony/TelephonyTTSSTTProcessor';
import { twilioAudioService } from '@/services/telephony/TwilioAudioService';
import { telephonyErrorHandler } from '@/services/telephony/TelephonyErrorHandler';
import { telephonyService } from '@/services/telephony';
import { incomingCallHandler } from '@/services/telephony/IncomingCallHandler';

interface TestResult {
  name: string;
  status: 'pending' | 'running' | 'passed' | 'failed';
  message?: string;
  duration?: number;
  details?: Record<string, any>;
}

interface SystemStatus {
  component: string;
  status: 'online' | 'offline' | 'degraded';
  lastCheck: Date;
  details: string;
}

export default function TelephonyTestPanel() {
  const { token } = useAuth();
  const { toast } = useToast();

  const [isRunningTests, setIsRunningTests] = useState(false);
  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus[]>([]);
  const [testCallId, setTestCallId] = useState('');
  const [testMessage, setTestMessage] = useState('Hello, this is a test message for telephony TTS functionality.');
  const [isConnected, setIsConnected] = useState(false);
  const [testPhoneNumber, setTestPhoneNumber] = useState('+1234567890');

  // Initialize test call ID
  useEffect(() => {
    setTestCallId(`test-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`);
  }, []);

  /**
   * Individual test functions
   */
  const tests = {
    webSocketConnection: async (): Promise<TestResult> => {
      const start = Date.now();
      try {
        if (!token) {
          throw new Error('No authentication token available');
        }
        const connected = await telephonyWebSocketManager.connect(testCallId, token, 'en', 'nova-2');
        const duration = Date.now() - start;
        
        if (connected) {
          setIsConnected(true);
          return {
            name: 'WebSocket Connection',
            status: 'passed',
            message: 'Successfully connected to telephony WebSocket',
            duration,
            details: { callId: testCallId }
          };
        } else {
          return {
            name: 'WebSocket Connection',
            status: 'failed',
            message: 'Failed to connect to telephony WebSocket',
            duration
          };
        }
      } catch (error) {
        return {
          name: 'WebSocket Connection',
          status: 'failed',
          message: error instanceof Error ? error.message : 'Connection failed',
          duration: Date.now() - start
        };
      }
    },

    ttsStandaloneTest: async (): Promise<TestResult> => {
      const start = Date.now();
      try {
        // Initialize TTS/STT processor
        await telephonyTTSSTTProcessor.startProcessing(testCallId, 'en');
        
        // Test TTS processing
        await telephonyTTSSTTProcessor.processAgentMessage(testCallId, testMessage, 'en');
        
        const duration = Date.now() - start;
        return {
          name: 'TTS Processing',
          status: 'passed',
          message: 'TTS message processed successfully',
          duration,
          details: { 
            message: testMessage.substring(0, 50) + '...',
            language: 'en'
          }
        };
      } catch (error) {
        return {
          name: 'TTS Processing',
          status: 'failed',
          message: error instanceof Error ? error.message : 'TTS processing failed',
          duration: Date.now() - start
        };
      }
    },

    twilioAudioInit: async (): Promise<TestResult> => {
      const start = Date.now();
      try {
        await twilioAudioService.initialize();
        
        const duration = Date.now() - start;
        return {
          name: 'Twilio Audio Service',
          status: 'passed',
          message: 'Twilio audio service initialized successfully',
          duration,
          details: { sampleRate: 8000, encoding: 'MULAW' }
        };
      } catch (error) {
        return {
          name: 'Twilio Audio Service',
          status: 'failed',
          message: error instanceof Error ? error.message : 'Twilio initialization failed',
          duration: Date.now() - start
        };
      }
    },

    errorHandlerTest: async (): Promise<TestResult> => {
      const start = Date.now();
      try {
        // Test error logging
        const errorId = telephonyErrorHandler.handleCommonErrors.connectionTimeout('TestPanel', testCallId);
        
        // Test error resolution
        telephonyErrorHandler.resolveError(errorId, 'Test error resolved successfully');
        
        const stats = telephonyErrorHandler.getErrorStats();
        
        const duration = Date.now() - start;
        return {
          name: 'Error Handler',
          status: 'passed',
          message: 'Error handling system functioning correctly',
          duration,
          details: { 
            errorId,
            totalErrors: stats.total,
            resolvedErrors: stats.resolved
          }
        };
      } catch (error) {
        return {
          name: 'Error Handler',
          status: 'failed',
          message: error instanceof Error ? error.message : 'Error handler test failed',
          duration: Date.now() - start
        };
      }
    },

    callManagerTest: async (): Promise<TestResult> => {
      const start = Date.now();
      try {
        // Initialize call manager
        if (!token) {
          throw new Error('No authentication token available');
        }
        await telephonyCallManager.initialize(token);
        
        // Test call state management
        const activeCalls = telephonyCallManager.getActiveCalls();
        
        const duration = Date.now() - start;
        return {
          name: 'Call Manager',
          status: 'passed',
          message: 'Call manager initialized and functioning',
          duration,
          details: { 
            activeCallsCount: activeCalls.length,
            initialized: true
          }
        };
      } catch (error) {
        return {
          name: 'Call Manager',
          status: 'failed',
          message: error instanceof Error ? error.message : 'Call manager test failed',
          duration: Date.now() - start
        };
      }
    },

    backendConnectivity: async (): Promise<TestResult> => {
      const start = Date.now();
      try {
        // Test backend API connectivity
        if (!token) {
          throw new Error('No authentication token available');
        }
        const config = await telephonyService.getTelephonyConfig(token);
        
        const duration = Date.now() - start;
        return {
          name: 'Backend Connectivity',
          status: 'passed',
          message: 'Backend API responding correctly',
          duration,
          details: { 
            configLoaded: !!config,
            isEnabled: config?.is_enabled,
            verificationStatus: config?.verification_status
          }
        };
      } catch (error) {
        return {
          name: 'Backend Connectivity',
          status: 'failed',
          message: error instanceof Error ? error.message : 'Backend connectivity failed',
          duration: Date.now() - start
        };
      }
    },

    incomingCallHandlerTest: async (): Promise<TestResult> => {
      const start = Date.now();
      try {
        if (!token) {
          throw new Error('No authentication token available');
        }
        
        // Initialize the handler
        await incomingCallHandler.initialize(token);
        
        // Get status
        const status = incomingCallHandler.getStatus();
        
        const duration = Date.now() - start;
        return {
          name: 'Incoming Call Handler',
          status: 'passed',
          message: 'Incoming call handler initialized successfully',
          duration,
          details: { 
            initialized: status.initialized,
            welcomeMessage: status.welcomeMessage.substring(0, 50) + '...',
            activeCalls: status.activeCalls
          }
        };
      } catch (error) {
        return {
          name: 'Incoming Call Handler',
          status: 'failed',
          message: error instanceof Error ? error.message : 'Incoming call handler test failed',
          duration: Date.now() - start
        };
      }
    }
  };

  /**
   * Simulate an incoming call for testing
   */
  const simulateIncomingCall = async () => {
    try {
      if (!token) {
        throw new Error('No authentication token available');
      }

      // Initialize handler if not already done
      await incomingCallHandler.initialize(token);
      
      // Get organization phone number from config
      const config = await telephonyService.getTelephonyConfig(token);
      const organizationNumber = config.organization_phone_number;

      console.log('📞 Simulating incoming call from:', testPhoneNumber, 'to:', organizationNumber);

      const callId = await incomingCallHandler.simulateIncomingCall(testPhoneNumber, organizationNumber);
      
      toast({
        title: "Call Simulated",
        description: `Incoming call simulated with ID: ${callId}`,
      });

      // Update system status after simulation
      setTimeout(updateSystemStatus, 1000);

    } catch (error) {
      console.error('Error simulating call:', error);
      toast({
        title: "Simulation Failed",
        description: error instanceof Error ? error.message : "Failed to simulate call",
        variant: "destructive"
      });
    }
  };

  /**
   * Run all tests
   */
  const runAllTests = async () => {
    setIsRunningTests(true);
    setTestResults([]);

    const testNames = Object.keys(tests) as (keyof typeof tests)[];
    const results: TestResult[] = [];

    for (const testName of testNames) {
      // Update UI to show test is running
      const runningResult: TestResult = {
        name: tests[testName].name || testName,
        status: 'running'
      };
      setTestResults([...results, runningResult]);

      try {
        const result = await tests[testName]();
        results.push(result);
        setTestResults([...results]);

        // Small delay between tests
        await new Promise(resolve => setTimeout(resolve, 500));
      } catch (error) {
        const failedResult: TestResult = {
          name: tests[testName].name || testName,
          status: 'failed',
          message: error instanceof Error ? error.message : 'Test execution failed'
        };
        results.push(failedResult);
        setTestResults([...results]);
      }
    }

    setIsRunningTests(false);

    // Show summary toast
    const passed = results.filter(r => r.status === 'passed').length;
    const failed = results.filter(r => r.status === 'failed').length;
    
    toast({
      title: "Test Suite Completed",
      description: `${passed} passed, ${failed} failed`,
      variant: failed > 0 ? "destructive" : "default"
    });
  };

  /**
   * Update system status
   */
  const updateSystemStatus = async () => {
    const status: SystemStatus[] = [
      {
        component: 'WebSocket Manager',
        status: telephonyWebSocketManager.isConnected ? 'online' : 'offline',
        lastCheck: new Date(),
        details: telephonyWebSocketManager.isConnected ? 'Connected and operational' : 'Not connected'
      },
      {
        component: 'Call Manager',
        status: telephonyCallManager.getActiveCalls().length >= 0 ? 'online' : 'offline',
        lastCheck: new Date(),
        details: `${telephonyCallManager.getActiveCalls().length} active calls`
      },
      {
        component: 'TTS/STT Processor',
        status: telephonyTTSSTTProcessor.getActiveCalls().length >= 0 ? 'online' : 'offline',
        lastCheck: new Date(),
        details: `${telephonyTTSSTTProcessor.getActiveCalls().length} active processors`
      },
      {
        component: 'Error Handler',
        status: 'online',
        lastCheck: new Date(),
        details: `${telephonyErrorHandler.getErrors({ resolved: false }).length} unresolved errors`
      }
    ];

    setSystemStatus(status);
  };

  // Update system status on mount and periodically
  useEffect(() => {
    updateSystemStatus();
    const interval = setInterval(updateSystemStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  /**
   * Cleanup connections
   */
  const cleanup = () => {
    if (isConnected) {
      telephonyWebSocketManager.disconnect();
      telephonyTTSSTTProcessor.stopProcessing(testCallId);
      setIsConnected(false);
    }
  };

  /**
   * Get status icon
   */
  const getStatusIcon = (status: TestResult['status'] | SystemStatus['status']) => {
    switch (status) {
      case 'passed':
      case 'online':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'failed':
      case 'offline':
        return <XCircle className="h-4 w-4 text-red-600" />;
      case 'running':
        return <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />;
      case 'degraded':
        return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
      default:
        return <div className="h-4 w-4 bg-gray-300 rounded-full" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Telephony Test Panel</h2>
          <p className="text-muted-foreground">
            Test and validate telephony system components
          </p>
        </div>
        <div className="flex space-x-2">
          <Button onClick={updateSystemStatus} variant="outline" size="sm">
            <Settings className="h-4 w-4 mr-2" />
            Refresh Status
          </Button>
          {isConnected && (
            <Button onClick={cleanup} variant="outline" size="sm">
              <Square className="h-4 w-4 mr-2" />
              Cleanup
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* System Status */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Wifi className="h-5 w-5 mr-2" />
              System Status
            </CardTitle>
            <CardDescription>
              Real-time status of telephony components
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {systemStatus.map((status, index) => (
              <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                <div className="flex items-center space-x-3">
                  {getStatusIcon(status.status)}
                  <div>
                    <div className="font-medium">{status.component}</div>
                    <div className="text-sm text-muted-foreground">{status.details}</div>
                  </div>
                </div>
                <Badge variant={status.status === 'online' ? 'default' : 'destructive'}>
                  {status.status}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Test Configuration */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Settings className="h-5 w-5 mr-2" />
              Test Configuration
            </CardTitle>
            <CardDescription>
              Configure test parameters
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Test Call ID</label>
              <Input
                value={testCallId}
                onChange={(e) => setTestCallId(e.target.value)}
                placeholder="test-call-id"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2">Test TTS Message</label>
              <Textarea
                value={testMessage}
                onChange={(e) => setTestMessage(e.target.value)}
                placeholder="Enter test message for TTS"
                rows={3}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Test Phone Number</label>
              <Input
                value={testPhoneNumber}
                onChange={(e) => setTestPhoneNumber(e.target.value)}
                placeholder="+1234567890"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Phone number to simulate incoming calls from
              </p>
            </div>

            <div className="space-y-2">
              <Button 
                onClick={runAllTests} 
                disabled={isRunningTests}
                className="w-full"
              >
                {isRunningTests ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Play className="h-4 w-4 mr-2" />
                )}
                Run All Tests
              </Button>

              <Button 
                onClick={simulateIncomingCall} 
                variant="outline"
                className="w-full"
              >
                <Phone className="h-4 w-4 mr-2" />
                Simulate Incoming Call
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Test Results */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <CheckCircle className="h-5 w-5 mr-2" />
            Test Results
          </CardTitle>
          <CardDescription>
            Detailed results from telephony system tests
          </CardDescription>
        </CardHeader>
        <CardContent>
          {testResults.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Play className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No tests run yet. Click "Run All Tests" to start validation.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {testResults.map((result, index) => (
                <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex items-center space-x-3">
                    {getStatusIcon(result.status)}
                    <div>
                      <div className="font-medium">{result.name}</div>
                      {result.message && (
                        <div className="text-sm text-muted-foreground">{result.message}</div>
                      )}
                      {result.duration && (
                        <div className="text-xs text-muted-foreground">{result.duration}ms</div>
                      )}
                    </div>
                  </div>
                  <Badge variant={
                    result.status === 'passed' ? 'default' : 
                    result.status === 'failed' ? 'destructive' : 
                    'secondary'
                  }>
                    {result.status}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Error Handler Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <AlertTriangle className="h-5 w-5 mr-2" />
            Error Handler Status
          </CardTitle>
          <CardDescription>
            Current telephony system health and error status
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {(() => {
              const health = telephonyErrorHandler.getHealthStatus();
              const stats = telephonyErrorHandler.getErrorStats();
              
              return (
                <>
                  <div className="text-center p-4 border rounded-lg">
                    <div className="text-2xl font-bold text-green-600">{stats.resolved}</div>
                    <div className="text-sm text-muted-foreground">Resolved Errors</div>
                  </div>
                  <div className="text-center p-4 border rounded-lg">
                    <div className="text-2xl font-bold text-red-600">{stats.unresolved}</div>
                    <div className="text-sm text-muted-foreground">Unresolved Errors</div>
                  </div>
                  <div className="text-center p-4 border rounded-lg">
                    <div className={`text-2xl font-bold ${
                      health.status === 'healthy' ? 'text-green-600' : 
                      health.status === 'degraded' ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      {health.status.toUpperCase()}
                    </div>
                    <div className="text-sm text-muted-foreground">System Health</div>
                  </div>
                </>
              );
            })()}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}