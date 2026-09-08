import type { AuthTokens } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: Error | null, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

export class ApiClient {
  static getAccessToken(): string | null {
    return localStorage.getItem('access_token');
  }

  static getRefreshToken(): string | null {
    return localStorage.getItem('refresh_token');
  }

  static setTokens(tokens: AuthTokens) {
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
  }

  static clearTokens() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }

  static async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
    const headers = new Headers(options.headers || {});

    // Ensure JSON content type by default if not FormData
    if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    const token = ApiClient.getAccessToken();
    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    let response: Response;
    try {
      response = await fetch(url, { ...options, headers });
    } catch (networkError) {
      throw new Error(`Network request failed: ${networkError}`);
    }

    // 401 Unauthorized -> Attempt Transparent Refresh Token Rotation (RTR)
    if (response.status === 401 && !endpoint.includes('/auth/login') && !endpoint.includes('/auth/refresh')) {
      const refreshToken = ApiClient.getRefreshToken();
      if (!refreshToken) {
        ApiClient.clearTokens();
        window.dispatchEvent(new Event('auth:unauthorized'));
        throw new Error('Unauthorized');
      }

      if (isRefreshing) {
        // Queue concurrent requests
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((newToken) => {
          headers.set('Authorization', `Bearer ${newToken}`);
          return ApiClient.request<T>(endpoint, { ...options, headers });
        });
      }

      isRefreshing = true;

      try {
        const refreshResp = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (!refreshResp.ok) {
          throw new Error('Refresh token invalid or revoked');
        }

        const newTokens: AuthTokens = await refreshResp.json();
        ApiClient.setTokens(newTokens);
        processQueue(null, newTokens.access_token);

        // Retry initial request with new access token
        headers.set('Authorization', `Bearer ${newTokens.access_token}`);
        return ApiClient.request<T>(endpoint, { ...options, headers });
      } catch (refreshErr) {
        processQueue(refreshErr as Error, null);
        ApiClient.clearTokens();
        window.dispatchEvent(new Event('auth:unauthorized'));
        throw refreshErr;
      } finally {
        isRefreshing = false;
      }
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const message = errorData.message || errorData.detail || `HTTP error ${response.status}`;
      throw new Error(message);
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  static get<T>(endpoint: string) {
    return ApiClient.request<T>(endpoint, { method: 'GET' });
  }

  static post<T>(endpoint: string, body?: unknown) {
    return ApiClient.request<T>(endpoint, {
      method: 'POST',
      body: body instanceof FormData ? body : JSON.stringify(body),
    });
  }

  static patch<T>(endpoint: string, body?: unknown) {
    return ApiClient.request<T>(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(body),
    });
  }

  static delete<T>(endpoint: string) {
    return ApiClient.request<T>(endpoint, { method: 'DELETE' });
  }
}
