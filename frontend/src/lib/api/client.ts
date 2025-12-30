import { browser } from '$app/environment';
import { goto } from '$app/navigation';
import type { ApiError, AuthTokens } from '$lib/types';

// =============================================================================
// Configuration
// =============================================================================

const API_BASE_URL = '/api/v1';
const TOKEN_KEY = 'auth_tokens';

// =============================================================================
// Error Classes
// =============================================================================

export class ApiException extends Error {
	constructor(
		public readonly status: number,
		public readonly detail: string,
		public readonly data?: unknown
	) {
		super(detail);
		this.name = 'ApiException';
	}

	static fromResponse(status: number, data: unknown): ApiException {
		const detail =
			typeof data === 'object' && data !== null && 'detail' in data
				? String((data as ApiError).detail)
				: 'An error occurred';
		return new ApiException(status, detail, data);
	}

	get isUnauthorized(): boolean {
		return this.status === 401;
	}

	get isNotFound(): boolean {
		return this.status === 404;
	}

	get isValidationError(): boolean {
		return this.status === 422;
	}
}

// =============================================================================
// Token Management
// =============================================================================

function getStoredTokens(): AuthTokens | null {
	if (!browser) return null;
	try {
		const stored = localStorage.getItem(TOKEN_KEY);
		return stored ? JSON.parse(stored) : null;
	} catch {
		return null;
	}
}

function setStoredTokens(tokens: AuthTokens): void {
	if (!browser) return;
	localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
}

function clearStoredTokens(): void {
	if (!browser) return;
	localStorage.removeItem(TOKEN_KEY);
}

export function getAccessToken(): string | null {
	return getStoredTokens()?.access_token ?? null;
}

export function getRefreshToken(): string | null {
	return getStoredTokens()?.refresh_token ?? null;
}

export function setTokens(tokens: AuthTokens): void {
	setStoredTokens(tokens);
}

export function clearTokens(): void {
	clearStoredTokens();
}

export function isAuthenticated(): boolean {
	return getAccessToken() !== null;
}

// =============================================================================
// Token Refresh
// =============================================================================

let refreshPromise: Promise<AuthTokens> | null = null;

async function refreshTokens(): Promise<AuthTokens> {
	// Deduplicate concurrent refresh calls
	if (refreshPromise) {
		return refreshPromise;
	}

	const refreshToken = getRefreshToken();
	if (!refreshToken) {
		throw new ApiException(401, 'No refresh token available');
	}

	refreshPromise = (async () => {
		try {
			const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ refresh_token: refreshToken })
			});

			if (!response.ok) {
				clearTokens();
				throw new ApiException(401, 'Token refresh failed');
			}

			const tokens: AuthTokens = await response.json();
			setTokens(tokens);
			return tokens;
		} finally {
			refreshPromise = null;
		}
	})();

	return refreshPromise;
}

// =============================================================================
// API Client
// =============================================================================

interface RequestOptions extends Omit<RequestInit, 'body'> {
	body?: unknown;
	requiresAuth?: boolean;
	skipRefresh?: boolean;
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
	const { body, requiresAuth = true, skipRefresh = false, ...fetchOptions } = options;

	const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;

	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
		...(options.headers as Record<string, string>)
	};

	// Add auth header if required
	if (requiresAuth) {
		const token = getAccessToken();
		if (token) {
			headers['Authorization'] = `Bearer ${token}`;
		}
	}

	const config: RequestInit = {
		...fetchOptions,
		headers,
		body: body ? JSON.stringify(body) : undefined
	};

	let response = await fetch(url, config);

	// Handle 401 with token refresh
	if (response.status === 401 && requiresAuth && !skipRefresh) {
		try {
			await refreshTokens();
			// Retry with new token
			const newToken = getAccessToken();
			if (newToken) {
				headers['Authorization'] = `Bearer ${newToken}`;
				config.headers = headers;
				response = await fetch(url, config);
			}
		} catch {
			// Refresh failed, redirect to login
			clearTokens();
			if (browser) {
				goto('/auth/login');
			}
			throw new ApiException(401, 'Session expired');
		}
	}

	// Parse response
	const contentType = response.headers.get('content-type');
	const isJson = contentType?.includes('application/json');
	const data = isJson ? await response.json() : await response.text();

	if (!response.ok) {
		throw ApiException.fromResponse(response.status, data);
	}

	return data as T;
}

// =============================================================================
// HTTP Methods
// =============================================================================

export const api = {
	get<T>(endpoint: string, options?: Omit<RequestOptions, 'method' | 'body'>): Promise<T> {
		return request<T>(endpoint, { ...options, method: 'GET' });
	},

	post<T>(endpoint: string, body?: unknown, options?: Omit<RequestOptions, 'method'>): Promise<T> {
		return request<T>(endpoint, { ...options, method: 'POST', body });
	},

	put<T>(endpoint: string, body?: unknown, options?: Omit<RequestOptions, 'method'>): Promise<T> {
		return request<T>(endpoint, { ...options, method: 'PUT', body });
	},

	patch<T>(
		endpoint: string,
		body?: unknown,
		options?: Omit<RequestOptions, 'method'>
	): Promise<T> {
		return request<T>(endpoint, { ...options, method: 'PATCH', body });
	},

	delete<T>(endpoint: string, options?: Omit<RequestOptions, 'method' | 'body'>): Promise<T> {
		return request<T>(endpoint, { ...options, method: 'DELETE' });
	}
};

// =============================================================================
// File Upload
// =============================================================================

export async function uploadFile(
	endpoint: string,
	file: File,
	fieldName: string = 'file'
): Promise<{ url: string }> {
	const formData = new FormData();
	formData.append(fieldName, file);

	const token = getAccessToken();
	const headers: Record<string, string> = {};
	if (token) {
		headers['Authorization'] = `Bearer ${token}`;
	}

	const response = await fetch(`${API_BASE_URL}${endpoint}`, {
		method: 'POST',
		headers,
		body: formData
	});

	if (!response.ok) {
		const data = await response.json();
		throw ApiException.fromResponse(response.status, data);
	}

	return response.json();
}

