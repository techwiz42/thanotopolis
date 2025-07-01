// frontend/src/components/navigation/OrganizationNavigation.tsx
'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { 
  Building2, 
  Users, 
  MessageSquare, 
  Phone, 
  Settings, 
  BarChart3,
  PhoneCall,
  PhoneIncoming,
  Headphones,
  Radio,
  Activity,
  TestTube,
  UserCheck
} from 'lucide-react';

import { telephonyService, TelephonyConfig } from '@/services/telephony';
import { telephonyCallManager } from '@/services/telephony/TelephonyCallManager';

interface NavigationItem {
  name: string;
  href: string;
  icon: React.ElementType;
  badge?: string;
  description?: string;
  disabled?: boolean;
}

export default function OrganizationNavigation() {
  const pathname = usePathname();
  const { user, token } = useAuth();
  const [telephonyConfig, setTelephonyConfig] = useState<TelephonyConfig | null>(null);
  const [telephonyLoading, setTelephonyLoading] = useState(true);
  const [activeCallsCount, setActiveCallsCount] = useState(0);

  // Check telephony status
  useEffect(() => {
    const checkTelephonyStatus = async () => {
      if (!token) {
        setTelephonyLoading(false);
        return;
      }

      try {
        const config = await telephonyService.getTelephonyConfig(token);
        setTelephonyConfig(config);
      } catch (error) {
        // No telephony configured yet
        setTelephonyConfig(null);
      } finally {
        setTelephonyLoading(false);
      }
    };

    checkTelephonyStatus();
  }, [token]);

  // Monitor active calls count
  useEffect(() => {
    if (!telephonyConfig || !telephonyService.isSetupComplete(telephonyConfig)) {
      return;
    }

    const updateActiveCallsCount = () => {
      const activeCalls = telephonyCallManager.getActiveCalls();
      const count = activeCalls.filter(call => 
        call.status === 'incoming' || 
        call.status === 'ringing' || 
        call.status === 'answered' || 
        call.status === 'in_progress'
      ).length;
      setActiveCallsCount(count);
    };

    // Initial count
    updateActiveCallsCount();

    // Listen for call events
    const handleCallEvent = () => updateActiveCallsCount();
    
    telephonyCallManager.on('call_incoming', handleCallEvent);
    telephonyCallManager.on('call_answered', handleCallEvent);
    telephonyCallManager.on('call_ended', handleCallEvent);
    telephonyCallManager.on('call_status_update', handleCallEvent);

    // Update every 10 seconds as backup
    const interval = setInterval(updateActiveCallsCount, 10000);

    return () => {
      telephonyCallManager.off('call_incoming', handleCallEvent);
      telephonyCallManager.off('call_answered', handleCallEvent);
      telephonyCallManager.off('call_ended', handleCallEvent);
      telephonyCallManager.off('call_status_update', handleCallEvent);
      clearInterval(interval);
    };
  }, [telephonyConfig]);

  // Base navigation items
  const navigationItems: NavigationItem[] = [
    {
      name: 'Overview',
      href: '/organizations',
      icon: Building2,
      description: 'Organization dashboard and overview'
    },
    {
      name: 'Members',
      href: '/organizations/members',
      icon: Users,
      description: 'Manage organization members and roles'
    },
    {
      name: 'Conversations',
      href: '/conversations',
      icon: MessageSquare,
      description: 'AI-powered chat conversations'
    },
    {
      name: 'CRM',
      href: '/organizations/crm',
      icon: UserCheck,
      description: 'Contact management and customer relationships'
    }
  ];

  // Telephony navigation items
  const telephonyItems: NavigationItem[] = [
    {
      name: 'Phone Setup',
      href: '/organizations/telephony/setup',
      icon: Phone,
      badge: telephonyConfig ? 
        (telephonyService.isSetupComplete(telephonyConfig) ? 'Active' : 'Setup Required') : 
        'New',
      description: 'Configure AI-powered phone support'
    },
    {
      name: 'Active Calls',
      href: '/organizations/telephony/active-calls',
      icon: Radio,
      badge: activeCallsCount > 0 ? activeCallsCount.toString() : undefined,
      disabled: !telephonyConfig || !telephonyService.isSetupComplete(telephonyConfig),
      description: 'Monitor live phone calls and agent responses'
    },
    {
      name: 'Call History',
      href: '/organizations/telephony/calls',
      icon: PhoneCall,
      disabled: !telephonyConfig || !telephonyService.isSetupComplete(telephonyConfig),
      description: 'View completed calls and transcripts'
    },
    {
      name: 'Voice Analytics',
      href: '/organizations/telephony/analytics',
      icon: BarChart3,
      disabled: !telephonyConfig || telephonyConfig.verification_status !== 'verified',
      description: 'Call analytics and insights'
    }
  ];

  // Add test panel for admin users
  if (user?.role === 'admin' || user?.role === 'org_admin' || user?.role === 'super_admin') {
    telephonyItems.push({
      name: 'System Tests',
      href: '/organizations/telephony/test',
      icon: TestTube,
      badge: 'Admin',
      disabled: !telephonyConfig,
      description: 'Test and validate telephony components'
    });
  }

  // Admin navigation items
  const adminItems: NavigationItem[] = [
    {
      name: 'Organization Settings',
      href: '/organizations/edit',
      icon: Settings,
      description: 'Manage organization settings'
    }
  ];

  const isActive = (href: string) => {
    if (href === '/organizations') {
      return pathname === '/organizations';
    }
    return pathname.startsWith(href);
  };

  const getBadgeVariant = (badge: string) => {
    // Check if badge is a number (active calls count)
    if (/^\d+$/.test(badge)) {
      const count = parseInt(badge);
      if (count > 5) return 'destructive'; // High priority for many calls
      if (count > 2) return 'secondary'; // Medium priority
      return 'default'; // Normal priority
    }
    
    switch (badge.toLowerCase()) {
      case 'active':
        return 'default';
      case 'setup required':
        return 'destructive';
      case 'new':
        return 'secondary';
      default:
        return 'outline';
    }
  };

  return (
    <div className="space-y-6">
      {/* Main Navigation */}
      <Card>
        <CardContent className="p-6">
          <h3 className="font-semibold text-lg mb-4 flex items-center">
            <Building2 className="h-5 w-5 mr-2" />
            Organization
          </h3>
          <nav className="space-y-2">
            {navigationItems.map((item) => (
              <Link key={item.href} href={item.href}>
                <Button
                  variant={isActive(item.href) ? 'default' : 'ghost'}
                  className="w-full justify-start h-auto p-3"
                  disabled={item.disabled}
                >
                  <item.icon className="h-4 w-4 mr-3" />
                  <div className="flex-1 text-left">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{item.name}</span>
                      {item.badge && (
                        <Badge variant={getBadgeVariant(item.badge)} className="ml-2">
                          {item.badge}
                        </Badge>
                      )}
                    </div>
                    {item.description && (
                      <p className="text-xs text-muted-foreground mt-1">
                        {item.description}
                      </p>
                    )}
                  </div>
                </Button>
              </Link>
            ))}
          </nav>
        </CardContent>
      </Card>

      {/* Telephony Navigation */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-lg flex items-center">
              <Headphones className="h-5 w-5 mr-2" />
              Telephony
            </h3>
            {!telephonyLoading && (
              <Badge variant={telephonyConfig?.is_enabled ? 'default' : 'secondary'}>
                {telephonyConfig?.is_enabled ? 'Enabled' : 'Disabled'}
              </Badge>
            )}
          </div>
          
          {telephonyLoading ? (
            <div className="text-center py-4 text-muted-foreground">
              <div className="animate-pulse">Loading telephony status...</div>
            </div>
          ) : (
            <nav className="space-y-2">
              {telephonyItems.map((item) => (
                <Link key={item.href} href={item.href}>
                  <Button
                    variant={isActive(item.href) ? 'default' : 'ghost'}
                    className="w-full justify-start h-auto p-3"
                    disabled={item.disabled}
                  >
                    <item.icon className="h-4 w-4 mr-3" />
                    <div className="flex-1 text-left">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">{item.name}</span>
                        {item.badge && (
                          <Badge variant={getBadgeVariant(item.badge)} className="ml-2">
                            {item.badge}
                          </Badge>
                        )}
                      </div>
                      {item.description && (
                        <p className="text-xs text-muted-foreground mt-1">
                          {item.description}
                        </p>
                      )}
                    </div>
                  </Button>
                </Link>
              ))}
            </nav>
          )}
          
          {/* Quick Stats */}
          {telephonyConfig && telephonyService.isSetupComplete(telephonyConfig) && (
            <div className="mt-4 space-y-2">
              <div className="p-3 bg-muted rounded-lg">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center">
                    <PhoneIncoming className="h-4 w-4 mr-2 text-green-600" />
                    <span>AI Phone Support Active</span>
                  </div>
                  <Badge variant="outline" className="text-xs">
                    {telephonyService.getDisplayPhoneNumber(telephonyConfig)}
                  </Badge>
                </div>
              </div>
              
              {/* Active Calls Alert */}
              {activeCallsCount > 0 && (
                <div className="p-3 bg-orange-50 border border-orange-200 rounded-lg">
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center">
                      <Activity className="h-4 w-4 mr-2 text-orange-600 animate-pulse" />
                      <span className="text-orange-800 font-medium">
                        {activeCallsCount} Active Call{activeCallsCount > 1 ? 's' : ''}
                      </span>
                    </div>
                    <Link href="/organizations/telephony/active-calls">
                      <Badge variant="default" className="text-xs cursor-pointer hover:bg-primary/80">
                        View
                      </Badge>
                    </Link>
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Admin Navigation */}
      {(user?.role === 'org_admin' || user?.role === 'admin') && (
        <Card>
          <CardContent className="p-6">
            <h3 className="font-semibold text-lg mb-4 flex items-center">
              <Settings className="h-5 w-5 mr-2" />
              Administration
            </h3>
            <nav className="space-y-2">
              {adminItems.map((item) => (
                <Link key={item.href} href={item.href}>
                  <Button
                    variant={isActive(item.href) ? 'default' : 'ghost'}
                    className="w-full justify-start h-auto p-3"
                    disabled={item.disabled}
                  >
                    <item.icon className="h-4 w-4 mr-3" />
                    <div className="flex-1 text-left">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">{item.name}</span>
                        {item.badge && (
                          <Badge variant={getBadgeVariant(item.badge)} className="ml-2">
                            {item.badge}
                          </Badge>
                        )}
                      </div>
                      {item.description && (
                        <p className="text-xs text-muted-foreground mt-1">
                          {item.description}
                        </p>
                      )}
                    </div>
                  </Button>
                </Link>
              ))}
            </nav>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
