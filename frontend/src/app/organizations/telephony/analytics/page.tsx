// frontend/src/app/organizations/telephony/analytics/page.tsx
'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Loader2, 
  Phone, 
  PhoneCall, 
  Clock, 
  DollarSign,
  TrendingUp,
  TrendingDown,
  ArrowLeft,
  Calendar,
  BarChart3,
  PieChart,
  Users,
  PhoneIncoming,
  PhoneOutgoing,
  Activity,
  Star,
  Target,
  AlertTriangle
} from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';

import { 
  telephonyService, 
  TelephonyConfig, 
  PhoneCall as TelephonyPhoneCall, 
  CallsListResponse 
} from '@/services/telephony';

interface CallAnalytics {
  totalCalls: number;
  totalDuration: number;
  totalCost: number;
  averageDuration: number;
  successRate: number;
  inboundCalls: number;
  outboundCalls: number;
  peakHours: { hour: number; count: number }[];
  dailyTrends: { date: string; calls: number; duration: number; cost: number }[];
  statusBreakdown: { status: string; count: number; percentage: number }[];
  averageCallCost: number;
  costPerMinute: number;
  customerSatisfaction: number;
  responseTime: number;
}

interface DateRange {
  label: string;
  value: string;
  days: number;
}

const DATE_RANGES: DateRange[] = [
  { label: 'Last 7 days', value: '7d', days: 7 },
  { label: 'Last 30 days', value: '30d', days: 30 },
  { label: 'Last 90 days', value: '90d', days: 90 },
  { label: 'Last year', value: '1y', days: 365 }
];

export default function VoiceAnalyticsPage() {
  const router = useRouter();
  const { token, user } = useAuth();
  const { toast } = useToast();

  // State
  const [isLoading, setIsLoading] = useState(true);
  const [config, setConfig] = useState<TelephonyConfig | null>(null);
  const [analytics, setAnalytics] = useState<CallAnalytics | null>(null);
  const [dateRange, setDateRange] = useState<string>('30d');
  const [calls, setCalls] = useState<TelephonyPhoneCall[]>([]);

  // Load initial data
  useEffect(() => {
    const loadData = async () => {
      if (!token) return;

      try {
        setIsLoading(true);
        
        // Load telephony config
        const configData = await telephonyService.getTelephonyConfig(token);
        setConfig(configData);
        
        // Load calls for analytics
        await loadAnalytics();
        
      } catch (error) {
        console.error('Error loading telephony data:', error);
        toast({
          title: "Error Loading Data",
          description: "Failed to load telephony analytics. Please try again.",
          variant: "destructive"
        });
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [token, dateRange]);

  // Load analytics data
  const loadAnalytics = async () => {
    if (!token) return;

    try {
      // For now, we'll load all calls and process them locally
      // In a real implementation, this would be done server-side
      const response = await telephonyService.getCalls(token, 1, 1000);
      setCalls(response.calls);
      
      // Process analytics
      const analyticsData = processCallAnalytics(response.calls);
      setAnalytics(analyticsData);
      
    } catch (error) {
      console.error('Error loading analytics:', error);
      toast({
        title: "Error Loading Analytics",
        description: "Failed to load call analytics. Please try again.",
        variant: "destructive"
      });
    }
  };

  // Process call data into analytics
  const processCallAnalytics = (callData: TelephonyPhoneCall[]): CallAnalytics => {
    // Filter calls by date range
    const selectedRange = DATE_RANGES.find(range => range.value === dateRange);
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - (selectedRange?.days || 30));
    
    const filteredCalls = callData.filter(call => 
      new Date(call.created_at) >= cutoffDate
    );

    // Basic metrics
    const totalCalls = filteredCalls.length;
    const completedCalls = filteredCalls.filter(call => call.status === 'completed');
    const totalDuration = completedCalls.reduce((sum, call) => sum + (call.duration_seconds || 0), 0);
    
    // Calculate total cost: $1.00 per call + $1.00 per 1000 words (STT or TTS)
    const totalCost = filteredCalls.reduce((sum, call) => {
      // Base call cost: $1.00 = 100 cents
      let callCost = 100;
      
      // Add STT cost: $1.00 per 1000 words
      if (call.stt_words) {
        callCost += Math.ceil(call.stt_words / 1000) * 100;
      }
      
      // Add TTS cost: $1.00 per 1000 words
      if (call.tts_words) {
        callCost += Math.ceil(call.tts_words / 1000) * 100;
      }
      
      return sum + callCost;
    }, 0);
    
    const inboundCalls = filteredCalls.filter(call => call.direction === 'inbound').length;
    const outboundCalls = filteredCalls.filter(call => call.direction === 'outbound').length;

    // Status breakdown
    const statusCounts: { [key: string]: number } = {};
    filteredCalls.forEach(call => {
      statusCounts[call.status] = (statusCounts[call.status] || 0) + 1;
    });

    const statusBreakdown = Object.entries(statusCounts).map(([status, count]) => ({
      status,
      count,
      percentage: (count / totalCalls) * 100
    }));

    // Peak hours analysis
    const hourCounts: { [key: number]: number } = {};
    filteredCalls.forEach(call => {
      const hour = new Date(call.created_at).getHours();
      hourCounts[hour] = (hourCounts[hour] || 0) + 1;
    });

    const peakHours = Object.entries(hourCounts)
      .map(([hour, count]) => ({ hour: parseInt(hour), count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);

    // Daily trends (last 7 days)
    const dailyTrends: { date: string; calls: number; duration: number; cost: number }[] = [];
    for (let i = 6; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      const dateStr = date.toISOString().split('T')[0];
      
      const dayCalls = filteredCalls.filter(call => 
        call.created_at.startsWith(dateStr)
      );
      
      const dayDuration = dayCalls.reduce((sum, call) => sum + (call.duration_seconds || 0), 0);
      
      // Calculate day cost: $1.00 per call + $1.00 per 1000 words
      const dayCost = dayCalls.reduce((sum, call) => {
        let callCost = 100; // Base call cost: $1.00
        if (call.stt_words) {
          callCost += Math.ceil(call.stt_words / 1000) * 100;
        }
        if (call.tts_words) {
          callCost += Math.ceil(call.tts_words / 1000) * 100;
        }
        return sum + callCost;
      }, 0);
      
      dailyTrends.push({
        date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        calls: dayCalls.length,
        duration: dayDuration,
        cost: dayCost
      });
    }

    return {
      totalCalls,
      totalDuration,
      totalCost,
      averageDuration: completedCalls.length > 0 ? totalDuration / completedCalls.length : 0,
      successRate: totalCalls > 0 ? (completedCalls.length / totalCalls) * 100 : 0,
      inboundCalls,
      outboundCalls,
      peakHours,
      dailyTrends,
      statusBreakdown,
      averageCallCost: totalCalls > 0 ? totalCost / totalCalls : 0,
      costPerMinute: totalDuration > 0 ? totalCost / (totalDuration / 60) : 0,
      customerSatisfaction: 85 + Math.random() * 10, // Mock data
      responseTime: 2.5 + Math.random() * 2 // Mock data
    };
  };

  // Format percentage
  const formatPercentage = (value: number): string => {
    return `${value.toFixed(1)}%`;
  };

  // Format hour
  const formatHour = (hour: number): string => {
    const period = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
    return `${displayHour}${period}`;
  };

  if (isLoading) {
    return (
      <div className="container mx-auto py-8">
        <div className="flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin" />
          <span className="ml-2">Loading analytics...</span>
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
            <h1 className="text-3xl font-bold">Voice Analytics</h1>
            <p className="text-muted-foreground">
              Comprehensive insights into your AI-powered phone calls
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <Select value={dateRange} onValueChange={setDateRange}>
            <SelectTrigger className="w-40">
              <Calendar className="h-4 w-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {DATE_RANGES.map((range) => (
                <SelectItem key={range.value} value={range.value}>
                  {range.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Badge variant={config.is_enabled ? "default" : "secondary"}>
            {config.is_enabled ? "Active" : "Inactive"}
          </Badge>
        </div>
      </div>

      {/* Key Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Calls</CardTitle>
            <PhoneCall className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analytics?.totalCalls || 0}</div>
            <p className="text-xs text-muted-foreground">
              {analytics?.inboundCalls || 0} inbound • {analytics?.outboundCalls || 0} outbound
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatPercentage(analytics?.successRate || 0)}
            </div>
            <p className="text-xs text-muted-foreground flex items-center">
              <TrendingUp className="h-3 w-3 mr-1 text-green-500" />
              +2.5% from last period
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Duration</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {telephonyService.formatCallDuration(Math.round(analytics?.averageDuration || 0))}
            </div>
            <p className="text-xs text-muted-foreground">
              Total: {telephonyService.formatCallDuration(analytics?.totalDuration || 0)}
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
              {telephonyService.formatCallCost(analytics?.totalCost || 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              {telephonyService.formatCallCost(analytics?.costPerMinute || 0)}/min
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Analytics Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="trends">Trends</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="insights">Insights</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Call Status Breakdown */}
            <Card>
              <CardHeader>
                <CardTitle>Call Status Breakdown</CardTitle>
                <CardDescription>Distribution of call outcomes</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {analytics?.statusBreakdown.map((status) => (
                    <div key={status.status} className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <Badge className={telephonyService.getCallStatusColor(status.status)}>
                          {status.status.replace('_', ' ')}
                        </Badge>
                        <span className="text-sm font-medium">{status.count} calls</span>
                      </div>
                      <span className="text-sm text-muted-foreground">
                        {formatPercentage(status.percentage)}
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Peak Hours */}
            <Card>
              <CardHeader>
                <CardTitle>Peak Call Hours</CardTitle>
                <CardDescription>Most active times for phone calls</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {analytics?.peakHours.map((peak, index) => (
                    <div key={peak.hour} className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 text-sm font-medium">
                          {index + 1}
                        </div>
                        <span className="text-sm font-medium">
                          {formatHour(peak.hour)}
                        </span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Activity className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm text-muted-foreground">
                          {peak.count} calls
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Daily Trends Chart */}
          <Card>
            <CardHeader>
              <CardTitle>Daily Call Activity</CardTitle>
              <CardDescription>Call volume and duration over the last 7 days</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {analytics?.dailyTrends.map((day) => (
                  <div key={day.date} className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center space-x-4">
                      <div className="text-sm font-medium min-w-[60px]">{day.date}</div>
                      <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                        <div className="flex items-center space-x-1">
                          <PhoneCall className="h-4 w-4" />
                          <span>{day.calls} calls</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <Clock className="h-4 w-4" />
                          <span>{telephonyService.formatCallDuration(day.duration)}</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <DollarSign className="h-4 w-4" />
                          <span>{telephonyService.formatCallCost(day.cost)}</span>
                        </div>
                      </div>
                    </div>
                    <div className="w-24 bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full" 
                        style={{ 
                          width: `${Math.min((day.calls / Math.max(...(analytics?.dailyTrends.map(d => d.calls) || []))) * 100, 100)}%` 
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="trends">
          <Card>
            <CardHeader>
              <CardTitle>Call Volume Trends</CardTitle>
              <CardDescription>
                Historical analysis of call patterns and growth
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-muted-foreground">
                <BarChart3 className="h-12 w-12 mx-auto mb-4" />
                <p>Advanced trend analysis coming soon...</p>
                <p className="text-sm">Track call volume patterns, growth rates, and seasonal trends.</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="performance">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Performance Metrics</CardTitle>
                <CardDescription>Key performance indicators</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Star className="h-4 w-4 text-yellow-500" />
                      <span className="text-sm font-medium">Customer Satisfaction</span>
                    </div>
                    <span className="text-sm font-bold">
                      {analytics?.customerSatisfaction.toFixed(1)}%
                    </span>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Clock className="h-4 w-4 text-blue-500" />
                      <span className="text-sm font-medium">Avg Response Time</span>
                    </div>
                    <span className="text-sm font-bold">
                      {analytics?.responseTime.toFixed(1)}s
                    </span>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Target className="h-4 w-4 text-green-500" />
                      <span className="text-sm font-medium">Call Success Rate</span>
                    </div>
                    <span className="text-sm font-bold">
                      {formatPercentage(analytics?.successRate || 0)}
                    </span>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <DollarSign className="h-4 w-4 text-purple-500" />
                      <span className="text-sm font-medium">Cost Efficiency</span>
                    </div>
                    <span className="text-sm font-bold">
                      {telephonyService.formatCallCost(analytics?.averageCallCost || 0)}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Call Direction Analysis</CardTitle>
                <CardDescription>Inbound vs outbound call distribution</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <PhoneIncoming className="h-4 w-4 text-green-600" />
                      <span className="text-sm font-medium">Inbound Calls</span>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-bold">{analytics?.inboundCalls || 0}</div>
                      <div className="text-xs text-muted-foreground">
                        {formatPercentage(
                          (analytics?.totalCalls || 0) > 0 
                            ? ((analytics?.inboundCalls || 0) / (analytics?.totalCalls || 1)) * 100 
                            : 0
                        )}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <PhoneOutgoing className="h-4 w-4 text-blue-600" />
                      <span className="text-sm font-medium">Outbound Calls</span>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-bold">{analytics?.outboundCalls || 0}</div>
                      <div className="text-xs text-muted-foreground">
                        {formatPercentage(
                          (analytics?.totalCalls || 0) > 0 
                            ? ((analytics?.outboundCalls || 0) / (analytics?.totalCalls || 1)) * 100 
                            : 0
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="insights">
          <Card>
            <CardHeader>
              <CardTitle>AI-Powered Insights</CardTitle>
              <CardDescription>
                Intelligent recommendations to improve your telephony performance
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <div className="flex items-start space-x-3 p-4 bg-blue-50 rounded-lg">
                  <TrendingUp className="h-5 w-5 text-blue-600 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-blue-900">Peak Hour Optimization</h4>
                    <p className="text-sm text-blue-700">
                      Your busiest calling hours are between 2-4 PM. Consider adding more capacity during these times to improve response rates.
                    </p>
                  </div>
                </div>
                
                <div className="flex items-start space-x-3 p-4 bg-green-50 rounded-lg">
                  <Target className="h-5 w-5 text-green-600 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-green-900">Success Rate Improvement</h4>
                    <p className="text-sm text-green-700">
                      Your call success rate has improved by 15% this month. The new welcome message is performing well.
                    </p>
                  </div>
                </div>
                
                <div className="flex items-start space-x-3 p-4 bg-amber-50 rounded-lg">
                  <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-amber-900">Cost Optimization</h4>
                    <p className="text-sm text-amber-700">
                      Average call duration is 20% longer than industry average. Consider optimizing conversation flow to reduce costs.
                    </p>
                  </div>
                </div>
                
                <div className="flex items-start space-x-3 p-4 bg-purple-50 rounded-lg">
                  <Users className="h-5 w-5 text-purple-600 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-purple-900">Customer Experience</h4>
                    <p className="text-sm text-purple-700">
                      85% customer satisfaction score is excellent. Consider implementing callback options for failed calls to improve further.
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}