import { v4 as uuidv4 } from 'uuid';

// CSRF token management for double-submit cookie pattern
export class CSRFProtection {
  private static TOKEN_KEY = 'csrf-token';
  private static TOKEN_HEADER = 'X-CSRF-Token';
  private static TOKEN_COOKIE_NAME = 'csrf-token';

  // Generate a new CSRF token
  static generateToken(): string {
    return uuidv4();
  }

  // Get or create CSRF token
  static getToken(): string {
    if (typeof window === 'undefined') {
      return '';
    }

    let token = localStorage.getItem(this.TOKEN_KEY);
    
    if (!token) {
      token = this.generateToken();
      localStorage.setItem(this.TOKEN_KEY, token);
      this.setTokenCookie(token);
    }

    return token;
  }

  // Set CSRF token as cookie (for double-submit pattern)
  private static setTokenCookie(token: string): void {
    if (typeof document === 'undefined') return;

    // Set cookie with SameSite=Strict for CSRF protection
    document.cookie = `${this.TOKEN_COOKIE_NAME}=${token}; path=/; SameSite=Strict; Secure`;
  }

  // Add CSRF token to request headers
  static addTokenToHeaders(headers: HeadersInit = {}): HeadersInit {
    const token = this.getToken();
    
    if (token) {
      return {
        ...headers,
        [this.TOKEN_HEADER]: token,
      };
    }

    return headers;
  }

  // Verify CSRF token (for server-side validation)
  static verifyToken(headerToken: string | null, cookieToken: string | null): boolean {
    if (!headerToken || !cookieToken) {
      return false;
    }

    return headerToken === cookieToken;
  }

  // Clear CSRF token (on logout)
  static clearToken(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem(this.TOKEN_KEY);
    }

    if (typeof document !== 'undefined') {
      // Clear cookie
      document.cookie = `${this.TOKEN_COOKIE_NAME}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
    }
  }
}

// Custom fetch wrapper with CSRF protection
export async function fetchWithCSRF(url: string, options: RequestInit = {}): Promise<Response> {
  // Only add CSRF token for state-changing methods
  const method = options.method?.toUpperCase() || 'GET';
  const requiresCSRF = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method);

  if (requiresCSRF) {
    options.headers = CSRFProtection.addTokenToHeaders(options.headers);
  }

  return fetch(url, options);
}