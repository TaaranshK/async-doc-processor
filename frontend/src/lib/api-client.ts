/**
 * API Client Utility
 * Handles all communication with the backend API
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_V1 = `${API_BASE_URL}/api/v1`;

interface RequestOptions extends RequestInit {
  headers?: Record<string, string>;
}

/**
 * Make an API request with proper error handling
 */
export async function apiCall<T = unknown>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const url = endpoint.startsWith('http') ? endpoint : `${API_V1}${endpoint}`;

  const defaultHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  const headers = {
    ...defaultHeaders,
    ...options.headers,
  };

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        message: response.statusText,
      }));
      throw new Error(error.message || `HTTP ${response.status}`);
    }

    // Handle empty responses
    const data = await response.text();
    if (!data) return {} as T;

    return JSON.parse(data) as T;
  } catch (error) {
    console.error(`API Error [${options.method || 'GET'} ${url}]:`, error);
    throw error;
  }
}

/**
 * GET request
 */
export async function get<T = unknown>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  return apiCall<T>(endpoint, {
    ...options,
    method: 'GET',
  });
}

/**
 * POST request
 */
export async function post<T = unknown>(
  endpoint: string,
  data?: unknown,
  options: RequestOptions = {}
): Promise<T> {
  return apiCall<T>(endpoint, {
    ...options,
    method: 'POST',
    body: data ? JSON.stringify(data) : undefined,
  });
}

/**
 * PUT request
 */
export async function put<T = unknown>(
  endpoint: string,
  data?: unknown,
  options: RequestOptions = {}
): Promise<T> {
  return apiCall<T>(endpoint, {
    ...options,
    method: 'PUT',
    body: data ? JSON.stringify(data) : undefined,
  });
}

/**
 * PATCH request
 */
export async function patch<T = unknown>(
  endpoint: string,
  data?: unknown,
  options: RequestOptions = {}
): Promise<T> {
  return apiCall<T>(endpoint, {
    ...options,
    method: 'PATCH',
    body: data ? JSON.stringify(data) : undefined,
  });
}

/**
 * DELETE request
 */
export async function deleteRequest<T = unknown>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  return apiCall<T>(endpoint, {
    ...options,
    method: 'DELETE',
  });
}
