import { AuthTokens } from '@/contexts/AuthContext'

export interface UsageStats {
  period: string
  start_date: string
  end_date: string
  total_tokens: number
  total_tts_words: number
  total_stt_words: number
  total_cost_cents: number
}

export interface SystemMetric {
  id: string
  metric_type: string
  value: number
  additional_data: any
  created_at: string
  tenant_id?: string
}

export interface TenantStat {
  tenant_id: string
  name: string
  subdomain: string
  user_count: number
  conversation_count: number
}

export interface UsageRecord {
  id: string
  tenant_id: string
  user_id?: string
  usage_type: string
  amount: number
  conversation_id?: string
  service_provider?: string
  model_name?: string
  cost_cents: number
  additional_data: any
  created_at: string
}

export interface OrganizationUsage {
  tenant_id: string
  tenant_name: string
  subdomain: string
  total_tokens: number
  total_tts_words: number
  total_stt_words: number
  total_cost_cents: number
  record_count: number
}

export interface AdminDashboard {
  total_users: number
  total_conversations: number
  active_ws_connections: number
  db_connection_pool_size: number
  recent_usage: UsageRecord[]
  system_metrics: SystemMetric[]
  tenant_stats: TenantStat[]
  overall_usage_stats?: UsageStats
  usage_by_organization?: OrganizationUsage[]
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface User {
  id: string
  email: string
  username: string
  first_name?: string
  last_name?: string
  role: string
  is_active: boolean
  is_verified: boolean
  tenant_id: string
  created_at: string
}

class AdminService {
  private baseURL = '/api/admin'

  private getHeaders(tokens: AuthTokens, organization: string) {
    return {
      'Authorization': `Bearer ${tokens.access_token}`,
      'X-Tenant-ID': organization,
      'Content-Type': 'application/json'
    }
  }

  async getDashboard(tokens: AuthTokens, organization: string): Promise<AdminDashboard> {
    const response = await fetch(`${this.baseURL}/dashboard`, {
      headers: this.getHeaders(tokens, organization)
    })

    if (!response.ok) {
      throw new Error('Failed to fetch dashboard data')
    }

    return response.json()
  }

  async getUsageStats(
    tokens: AuthTokens, 
    organization: string,
    params: {
      tenant_id?: string
      user_id?: string
      period?: 'day' | 'week' | 'month'
      start_date?: string
      end_date?: string
    } = {}
  ): Promise<UsageStats> {
    const searchParams = new URLSearchParams()
    
    Object.entries(params).forEach(([key, value]) => {
      if (value) searchParams.append(key, value)
    })

    const response = await fetch(`${this.baseURL}/usage/stats?${searchParams}`, {
      headers: this.getHeaders(tokens, organization)
    })

    if (!response.ok) {
      throw new Error('Failed to fetch usage statistics')
    }

    return response.json()
  }

  async getUsageRecords(
    tokens: AuthTokens,
    organization: string,
    params: {
      page?: number
      page_size?: number
      tenant_id?: string
      user_id?: string
      usage_type?: string
      service_provider?: string
      start_date?: string
      end_date?: string
    } = {}
  ): Promise<PaginatedResponse<UsageRecord>> {
    const searchParams = new URLSearchParams()
    
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) searchParams.append(key, value.toString())
    })

    const response = await fetch(`${this.baseURL}/usage/records?${searchParams}`, {
      headers: this.getHeaders(tokens, organization)
    })

    if (!response.ok) {
      throw new Error('Failed to fetch usage records')
    }

    return response.json()
  }

  async getSystemMetrics(
    tokens: AuthTokens,
    organization: string,
    params: {
      metric_type?: string
      hours?: number
    } = {}
  ): Promise<SystemMetric[]> {
    const searchParams = new URLSearchParams()
    
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) searchParams.append(key, value.toString())
    })

    const response = await fetch(`${this.baseURL}/system/metrics?${searchParams}`, {
      headers: this.getHeaders(tokens, organization)
    })

    if (!response.ok) {
      throw new Error('Failed to fetch system metrics')
    }

    return response.json()
  }

  async getUsers(
    tokens: AuthTokens,
    organization: string,
    params: {
      page?: number
      page_size?: number
      tenant_id?: string
      role?: string
      is_active?: boolean
    } = {}
  ): Promise<PaginatedResponse<User>> {
    const searchParams = new URLSearchParams()
    
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) searchParams.append(key, value.toString())
    })

    const response = await fetch(`${this.baseURL}/users?${searchParams}`, {
      headers: this.getHeaders(tokens, organization)
    })

    if (!response.ok) {
      throw new Error('Failed to fetch users')
    }

    return response.json()
  }

  async updateUser(
    tokens: AuthTokens,
    organization: string,
    userId: string,
    updates: {
      role?: string
      is_active?: boolean
      is_verified?: boolean
    }
  ): Promise<User> {
    const response = await fetch(`${this.baseURL}/users/${userId}`, {
      method: 'PATCH',
      headers: this.getHeaders(tokens, organization),
      body: JSON.stringify(updates)
    })

    if (!response.ok) {
      throw new Error('Failed to update user')
    }

    return response.json()
  }

  async getTenants(tokens: AuthTokens, organization: string) {
    const response = await fetch(`${this.baseURL}/tenants`, {
      headers: this.getHeaders(tokens, organization)
    })

    if (!response.ok) {
      throw new Error('Failed to fetch tenants')
    }

    return response.json()
  }

  async recordSystemMetric(
    tokens: AuthTokens,
    organization: string,
    metricType: string,
    value: number,
    tenantId?: string,
    additionalData?: any
  ): Promise<{ message: string; id: string }> {
    const response = await fetch(`${this.baseURL}/system/metrics`, {
      method: 'POST',
      headers: this.getHeaders(tokens, organization),
      body: JSON.stringify({
        metric_type: metricType,
        value,
        tenant_id: tenantId,
        additional_data: additionalData
      })
    })

    if (!response.ok) {
      throw new Error('Failed to record system metric')
    }

    return response.json()
  }
}

export const adminService = new AdminService()