import { api, setTokens, clearTokens } from './client';
import type { AuthTokens, LoginCredentials, RegisterData, User } from '$lib/types';

// =============================================================================
// Auth API
// =============================================================================

export interface LoginResponse extends AuthTokens {
	user: User;
}

export interface RegisterResponse {
	user: User;
	message: string;
}

/**
 * Login with email and password
 */
export async function login(credentials: LoginCredentials): Promise<LoginResponse> {
	const response = await fetch('/api/v1/auth/login', {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			username: credentials.email,
			password: credentials.password
		})
	});

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Login failed');
	}

	const data = await response.json();
	
	// Backend returns { user, tokens: { access_token, refresh_token, token_type } }
	const tokens = data.tokens || data;
	setTokens({
		access_token: tokens.access_token,
		refresh_token: tokens.refresh_token,
		token_type: tokens.token_type
	});

	return {
		user: data.user,
		access_token: tokens.access_token,
		refresh_token: tokens.refresh_token,
		token_type: tokens.token_type
	} as LoginResponse;
}

/**
 * Register a new user
 */
export async function register(data: RegisterData): Promise<RegisterResponse> {
	return api.post<RegisterResponse>('/auth/register', data, { requiresAuth: false });
}

/**
 * Logout and clear tokens
 */
export async function logout(): Promise<void> {
	try {
		await api.post('/auth/logout', undefined, { skipRefresh: true });
	} catch {
		// Ignore errors, still clear tokens
	} finally {
		clearTokens();
	}
}

/**
 * Get current user profile
 */
export async function getCurrentUser(): Promise<User> {
	return api.get<User>('/users/me');
}

/**
 * Request password reset
 */
export async function requestPasswordReset(email: string): Promise<{ message: string }> {
	return api.post('/auth/password-reset/request', { email }, { requiresAuth: false });
}

/**
 * Reset password with token
 */
export async function resetPassword(
	token: string,
	newPassword: string
): Promise<{ message: string }> {
	return api.post('/auth/password-reset', { token, new_password: newPassword }, { requiresAuth: false });
}

/**
 * Change password (authenticated)
 */
export async function changePassword(
	currentPassword: string,
	newPassword: string
): Promise<{ message: string }> {
	return api.post('/users/me/password', {
		current_password: currentPassword,
		new_password: newPassword
	});
}

/**
 * Verify email
 */
export async function verifyEmail(token: string): Promise<{ message: string }> {
	return api.post('/auth/verify-email', { token }, { requiresAuth: false });
}

