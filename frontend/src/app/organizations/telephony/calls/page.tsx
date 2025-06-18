// frontend/src/app/organizations/telephony/calls/page.tsx
'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from '@/components/ui/select';
import { 
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Loader2, 
  Phone, 
  PhoneCall, 
  Clock, 
  DollarSign, 
  Download,
  Play,
  FileText,
  ArrowLeft,
  Search,
  Filter,
  Calendar,
  TrendingUp,
  Users,
  PhoneIncoming,
  PhoneOutgoing
} from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';

import { 
  telephonyService, 
  TelephonyConfig, 
  PhoneCall as TelephonyPhoneCall, 
  CallsListResponse 
} from '@/services/telephony';

interface CallStats {
  totalCalls: number;
  totalDuration: number;
  totalCost: number;
  averageDuration: number;
  successRate: number;
}

export default function CallManagementPage() {
  const router = useRouter();
  const { token, user } = useAuth();
  const { toast } = useToast();

  // State
  const [isLoading, setIsLoading] = useState(true);
  const [config, setConfig] = useState<TelephonyConfig | null>(null);
  const [calls, setCalls] = useState<TelephonyPhoneCall[]>([]);
  const [stats, setStats] = useState<CallStats>({
    totalCalls: 0,
    totalDuration: 0,
    totalCost: 0,
    averageDuration: 0,
    successRate: 0
  });

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCalls, setTotalCalls] = useState(0);
  const [perPage] = useState(20);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState('');
  const [dateFilter, setDateFilter] = useState<'today' | 'week' | 'month' | 'all'>('all');

  // Selected call for details
  const [selectedCall, setSelectedCall] = useState<TelephonyPhoneCall | null>(null);

  // Load initial data
  useEffect(() => {
    const loadData = async () => {
      if (!token) return;

      try {
        setIsLoading(true);
        
        // Load telephony config
        const configData = await telephonyService.getTelephonyConfig(token);
        setConfig(configData);
        
        // Load calls
        await loadCalls();
        
      } catch (error) {
        console.error('Error loading telephony data:', error);
        toast({
          title: "Error Loading Data",
          description: "Failed to load telephony information. Please try again.",
          variant: "destructive"
        });
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [token]);

  // Load calls with filters
  const loadCalls = async (page: number = 1) => {
    if (!token) return;

    try {
      const response = await telephonyService.getCalls(
        token,
        page,
        perPage,
        statusFilter || undefined
      );
      
      setCalls(response.calls);
      setCurrentPage(response.page);
      setTotalPages(Math.ceil(response.total / response.per_page));
      setTotalCalls(response.total);
      
      // Calculate stats
      calculateStats(response.calls);
      
    } catch (error) {
      console.error('Error loading calls:', error);
      toast({
        title: "Error Loading Calls",
        description: "Failed to load call history. Please try again.",
        variant: "destructive"
      });
    }
  };

  // Calculate call statistics
  const calculateStats = (callData: TelephonyPhoneCall[]) => {
    const completedCalls = callData.filter(call => call.status === 'completed');
    const totalDuration = completedCalls.reduce((sum, call) => sum + (call.duration_seconds || 0), 0);
    const totalCost = callData.reduce((sum, call) => sum + call.cost_cents, 0);
    const successRate = callData.length > 0 ? (completedCalls.length / callData.length) * 100 : 0;

    setStats({
      totalCalls: callData.length,
      totalDuration,
      totalCost,
      averageDuration: completedCalls.length > 0 ? totalDuration / completedCalls.length : 0,
      successRate
    });
  };

  // Filter calls based on search term
  const filteredCalls = calls.filter(call => {
    if (!searchTerm) return true;
    
    const searchLower = searchTerm.toLowerCase();
    return (
      call.customer_phone_number.includes(searchLower) ||
      call.organization_phone_number.includes(searchLower) ||
      call.call_sid.toLowerCase().includes(searchLower)
    );
  });

  // Handle filter changes
  useEffect(() => {
    loadCalls(1);
  }, [statusFilter]);

  // Format duration
  const formatDuration = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  // Format date
  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (isLoading) {
    return (
      <div className="container mx-auto py-8">
        <div className="flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin" />
          <span className="ml-2">Loading call data...</span>
        </div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="container mx-auto py-8">
        <Alert>
          <Phone className="h-4 w-4" />
          <AlertDescription>
            Telephony is not configured for your organization. 
            <Button 
              variant="link" 
              onClick={() => router.push('/organizations/telephony/setup')}
              className="ml-2 p-0 h-auto"
            >
              Set it up now
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 max-w-7xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center">
          <Button
            variant="ghost"
            onClick={() => router.back()}
            className="mr-4"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-3xl font-bold">Call Management</h1>
            <p className="text-muted-foreground">
              Monitor and manage your AI-powered phone calls
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant={config.is_enabled ? "default" : "secondary"}>
            {config.is_enabled ? "Active" : "Inactive"}
          </Badge>
          <Badge variant={config.verification_status === 'verified' ? "default" : "destructive"}>
            {config.verification_status}
          </Badge>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Calls</CardTitle>
            <PhoneCall className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalCalls}</div>
            <p className="text-xs text-muted-foreground">
              All time calls
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Duration</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {telephonyService.formatCallDuration(stats.totalDuration)}
            </div>
            <p className="text-xs text-muted-foreground">
              Average: {telephonyService.formatCallDuration(Math.round(stats.averageDuration))}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {telephonyService.formatCallCost(stats.totalCost)}
            </div>
            <p className="text-xs text-muted-foreground">
              This month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.successRate.toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">
              Completed calls
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs defaultValue="calls" className="space-y-4">
        <TabsList>
          <TabsTrigger value="calls">Call History</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="calls" className="space-y-4">
          {/* Filters */}
          <Card>
            <CardHeader>
              <CardTitle>Filter Calls</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-4">
                <div className="flex items-center space-x-2">
                  <Search className="h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search phone numbers or call IDs..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-64"
                  />
                </div>
                
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="All Statuses" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All Statuses</SelectItem>
                    <SelectItem value="completed">Completed</SelectItem>
                    <SelectItem value="in_progress">In Progress</SelectItem>
                    <SelectItem value="failed">Failed</SelectItem>
                    <SelectItem value="no_answer">No Answer</SelectItem>
                    <SelectItem value="busy">Busy</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Calls Table */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Calls</CardTitle>
              <CardDescription>
                {totalCalls} total calls • Page {currentPage} of {totalPages}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Direction</TableHead>
                    <TableHead>Phone Number</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead>Cost</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredCalls.map((call) => (
                    <TableRow key={call.id}>
                      <TableCell>
                        <div className="flex items-center">
                          {call.direction === 'inbound' ? (
                            <PhoneIncoming className="h-4 w-4 text-green-600" />
                          ) : (
                            <PhoneOutgoing className="h-4 w-4 text-blue-600" />
                          )}
                          <span className="ml-2 capitalize">{call.direction}</span>
                        </div>
                      </TableCell>
                      <TableCell className="font-medium">
                        {telephonyService.formatPhoneNumber(call.customer_phone_number)}
                      </TableCell>
                      <TableCell>
                        <Badge className={telephonyService.getCallStatusColor(call.status)}>
                          {call.status.replace('_', ' ')}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {call.duration_seconds 
                          ? telephonyService.formatCallDuration(call.duration_seconds)
                          : '-'
                        }
                      </TableCell>
                      <TableCell>
                        {telephonyService.formatCallCost(call.cost_cents, call.cost_currency)}
                      </TableCell>
                      <TableCell>{formatDate(call.created_at)}</TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-2">
                          {call.recording_url && (
                            <Button variant="ghost" size="sm">
                              <Play className="h-4 w-4" />
                            </Button>
                          )}
                          {call.transcript && (
                            <Button variant="ghost" size="sm">
                              <FileText className="h-4 w-4" />
                            </Button>
                          )}
                          <Button 
                            variant="ghost" 
                            size="sm"
                            onClick={() => setSelectedCall(call)}
                          >
                            View
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4">
                  <p className="text-sm text-muted-foreground">
                    Showing {((currentPage - 1) * perPage) + 1} to {Math.min(currentPage * perPage, totalCalls)} of {totalCalls} calls
                  </p>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => loadCalls(currentPage - 1)}
                      disabled={currentPage <= 1}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => loadCalls(currentPage + 1)}
                      disabled={currentPage >= totalPages}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analytics">
          <Card>
            <CardHeader>
              <CardTitle>Call Analytics</CardTitle>
              <CardDescription>
                Detailed analytics and insights about your phone calls
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-muted-foreground">
                <TrendingUp className="h-12 w-12 mx-auto mb-4" />
                <p>Call analytics dashboard coming soon...</p>
                <p className="text-sm">Track call volume, success rates, and customer satisfaction.</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="settings">
          <Card>
            <CardHeader>
              <CardTitle>Telephony Settings</CardTitle>
              <CardDescription>
                Manage your telephony configuration
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium">Phone Number</h4>
                    <p className="text-sm text-muted-foreground">
                      {config.formatted_phone_number || config.organization_phone_number}
                    </p>
                  </div>
                  <Button 
                    variant="outline"
                    onClick={() => router.push('/organizations/telephony/setup')}
                  >
                    Edit Configuration
                  </Button>
                </div>
                
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium">Status</h4>
                    <p className="text-sm text-muted-foreground">
                      {config.is_enabled ? 'Active' : 'Inactive'} • {config.verification_status}
                    </p>
                  </div>
                  <Badge variant={config.is_enabled ? "default" : "secondary"}>
                    {config.is_enabled ? "Enabled" : "Disabled"}
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
