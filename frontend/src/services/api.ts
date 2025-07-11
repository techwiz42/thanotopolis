// src/services/api.ts

// Use the proxy through Next.js to avoid CORS issues
const API_BASE_URL = '/api';

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number>;
  tenantId?: string; // Added for multi-tenant support
}

class ApiService {
  baseUrl: string;
  defaults: {
    baseURL: string;
  };

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
    this.defaults = {
      baseURL: baseUrl
    };
  }

  private async request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<{ data: T; headers: Headers }> {
    const { params, headers = {}, tenantId, ...fetchOptions } = options;
    
    let url = `${this.baseUrl}${endpoint}`;
    
    if (params) {
      // Convert params to string entries for URLSearchParams
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        searchParams.append(key, String(value));
      });
      url += `?${searchParams.toString()}`;
    }

    // Get organization from localStorage if not provided
    const organization = tenantId || (typeof localStorage !== 'undefined' ? localStorage.getItem('organization') : '') || '';

    const finalHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(headers as Record<string, string>),
    };

    // Add tenant header if available
    if (organization) {
      finalHeaders['X-Tenant-ID'] = organization;
    }

    // Add Authorization header if token is available
    if (typeof localStorage !== 'undefined') {
      const tokens = localStorage.getItem('tokens');
      if (tokens) {
        try {
          const parsedTokens = JSON.parse(tokens);
          if (parsedTokens.access_token) {
            finalHeaders['Authorization'] = `Bearer ${parsedTokens.access_token}`;
          }
        } catch (error) {
          console.warn('Failed to parse tokens from localStorage:', error);
        }
      }
    }

    console.log('API Request:', {
      url,
      method: fetchOptions.method || 'GET',
      headers: finalHeaders
    });
    
    // Debug authentication headers specifically
    if (finalHeaders['Authorization']) {
      console.log('✓ Authorization header present:', finalHeaders['Authorization'].substring(0, 20) + '...');
    } else {
      console.log('✗ Authorization header missing');
    }
    
    if (finalHeaders['X-Tenant-ID']) {
      console.log('✓ X-Tenant-ID header present:', finalHeaders['X-Tenant-ID']);
    } else {
      console.log('✗ X-Tenant-ID header missing');
    }

    const response = await fetch(url, {
      ...fetchOptions,
      headers: finalHeaders,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API error: ${response.status}`);
    }

    const data = await response.json();
    return { data, headers: response.headers };
  }

  async get<T>(endpoint: string, options?: RequestOptions): Promise<{ data: T; headers: Headers }> {
    return this.request<T>(endpoint, { ...options, method: 'GET' });
  }

  async post<T>(endpoint: string, data?: any, options?: RequestOptions): Promise<{ data: T; headers: Headers }> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: data instanceof FormData ? data : JSON.stringify(data),
      headers: data instanceof FormData 
        ? options?.headers 
        : { 'Content-Type': 'application/json', ...options?.headers },
    });
  }

  async put<T>(endpoint: string, data?: any, options?: RequestOptions): Promise<{ data: T; headers: Headers }> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }
  
  async patch<T>(endpoint: string, data?: any, options?: RequestOptions): Promise<{ data: T; headers: Headers }> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async delete<T>(endpoint: string, options?: RequestOptions): Promise<{ data: T; headers: Headers }> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' });
  }
}

export const api = new ApiService();
