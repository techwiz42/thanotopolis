// src/services/api.ts

// Use the proxy through Next.js to avoid CORS issues
const API_BASE_URL = '';

interface RequestOptions extends RequestInit {
  params?: Record<string, string>;
  tenantId?: string; // Added for multi-tenant support
}

class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<{ data: T; headers: Headers }> {
    const { params, headers = {}, tenantId, ...fetchOptions } = options;
    
    let url = `${this.baseUrl}${endpoint}`;
    
    if (params) {
      const searchParams = new URLSearchParams(params);
      url += `?${searchParams.toString()}`;
    }

    // Get organization from localStorage if not provided
    const organization = tenantId || localStorage.getItem('organization') || '';

    const finalHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
      ...headers as Record<string, string>,
    };

    // Add tenant header if available
    if (organization) {
      finalHeaders['X-Tenant-ID'] = organization;
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

  async delete<T>(endpoint: string, options?: RequestOptions): Promise<{ data: T; headers: Headers }> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' });
  }
}

export const api = new ApiService();
