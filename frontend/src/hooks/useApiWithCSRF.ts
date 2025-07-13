import { useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { CSRFProtection, fetchWithCSRF } from '@/utils/csrf';

interface ApiOptions extends RequestInit {
  skipAuth?: boolean;
}

export function useApiWithCSRF() {
  const { token } = useAuth();

  const apiCall = useCallback(async (url: string, options: ApiOptions = {}) => {
    const { skipAuth = false, ...requestOptions } = options;

    // Prepare headers
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(requestOptions.headers as Record<string, string>),
    };

    // Add auth token if available and not skipped
    if (token && !skipAuth) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // Use fetchWithCSRF which automatically adds CSRF token for state-changing methods
    try {
      const response = await fetchWithCSRF(url, {
        ...requestOptions,
        headers,
      });

      // Handle unauthorized responses
      if (response.status === 401 && !skipAuth) {
        // Token might be expired, redirect to login
        window.location.href = '/login';
        throw new Error('Unauthorized');
      }

      return response;
    } catch (error) {
      console.error('API call failed:', error);
      throw error;
    }
  }, [token]);

  return { apiCall };
}

// Helper functions for common HTTP methods
export function useApi() {
  const { apiCall } = useApiWithCSRF();

  const get = useCallback((url: string, options?: ApiOptions) => {
    return apiCall(url, { ...options, method: 'GET' });
  }, [apiCall]);

  const post = useCallback((url: string, data?: any, options?: ApiOptions) => {
    return apiCall(url, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }, [apiCall]);

  const put = useCallback((url: string, data?: any, options?: ApiOptions) => {
    return apiCall(url, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }, [apiCall]);

  const patch = useCallback((url: string, data?: any, options?: ApiOptions) => {
    return apiCall(url, {
      ...options,
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    });
  }, [apiCall]);

  const del = useCallback((url: string, options?: ApiOptions) => {
    return apiCall(url, { ...options, method: 'DELETE' });
  }, [apiCall]);

  return { get, post, put, patch, delete: del, apiCall };
}