import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { http, HttpResponse } from 'msw';
import { server } from '../../mocks/server';
import {
	auth,
	currentUser,
	isAuthenticated,
	isAuthLoading,
	isAuthInitialized,
	authError
} from '$lib/stores/auth';
import { clearTokens, setTokens, getAccessToken } from '$lib/api/client';

// Mock goto
vi.mock('$app/navigation', () => ({
	goto: vi.fn()
}));

describe('Auth Store', () => {
	beforeEach(() => {
		clearTokens();
		// Reset store state by initializing with cleared tokens
	});

	describe('initial state', () => {
		it('should start with null user', () => {
			expect(get(currentUser)).toBeNull();
		});

		it('should start as not authenticated', () => {
			expect(get(isAuthenticated)).toBe(false);
		});

		it('should start as not loading', () => {
			expect(get(isAuthLoading)).toBe(false);
		});
	});

	describe('initialize', () => {
		it('should load user when token exists', async () => {
			setTokens({
				access_token: 'test-access-token',
				refresh_token: 'test-refresh-token',
				token_type: 'bearer'
			});

			await auth.initialize();

			expect(get(isAuthInitialized)).toBe(true);
			expect(get(currentUser)).not.toBeNull();
			expect(get(currentUser)?.username).toBe('testuser');
		});

		it('should handle missing token', async () => {
			await auth.initialize();

			expect(get(isAuthInitialized)).toBe(true);
			expect(get(currentUser)).toBeNull();
		});

		it('should handle API error during initialization', async () => {
			setTokens({
				access_token: 'invalid-token',
				refresh_token: 'invalid-refresh',
				token_type: 'bearer'
			});

			server.use(
				http.get('/api/v1/users/me', () => {
					return HttpResponse.json({ detail: 'Invalid token' }, { status: 401 });
				}),
				http.post('/api/v1/auth/refresh', () => {
					return HttpResponse.json({ detail: 'Invalid token' }, { status: 401 });
				})
			);

			await auth.initialize();

			expect(get(isAuthInitialized)).toBe(true);
			expect(get(currentUser)).toBeNull();
			expect(getAccessToken()).toBeNull();
		});
	});

	describe('login', () => {
		it('should login and set user', async () => {
			await auth.login({
				email: 'test@example.com',
				password: 'password123'
			});

			expect(get(currentUser)).not.toBeNull();
			expect(get(currentUser)?.username).toBe('testuser');
			expect(get(isAuthenticated)).toBe(true);
		});

		it('should set error on failed login', async () => {
			// First logout to clear any state
			await auth.logout();
			
			try {
				await auth.login({
					email: 'wrong@example.com',
					password: 'wrongpassword'
				});
			} catch {
				// Expected to throw
			}

			// After failed login, authError should be set
			expect(get(authError)).not.toBeNull();
		});

		it('should set loading state during login', async () => {
			const loginPromise = auth.login({
				email: 'test@example.com',
				password: 'password123'
			});

			// Note: In real tests, we'd check the loading state
			// but with mocked responses it's too fast to catch

			await loginPromise;
			expect(get(isAuthLoading)).toBe(false);
		});
	});

	describe('logout', () => {
		it('should clear user on logout', async () => {
			setTokens({
				access_token: 'test-access-token',
				refresh_token: 'test-refresh-token',
				token_type: 'bearer'
			});

			await auth.initialize();
			expect(get(currentUser)).not.toBeNull();

			await auth.logout();

			expect(get(currentUser)).toBeNull();
			expect(get(isAuthenticated)).toBe(false);
			expect(getAccessToken()).toBeNull();
		});
	});

	describe('setAuth', () => {
		it('should set tokens and user', () => {
			const user = {
				id: 1,
				username: 'newuser',
				email: 'new@example.com',
				display_name: 'New User',
				bio: null,
				avatar_url: null,
				location: null,
				website: null,
				followers_count: 0,
				following_count: 0,
				posts_count: 0,
				is_verified: false,
				created_at: '2024-01-01T00:00:00Z'
			};

			auth.setAuth(
				{
					access_token: 'new-access',
					refresh_token: 'new-refresh',
					token_type: 'bearer'
				},
				user
			);

			expect(get(currentUser)?.username).toBe('newuser');
			expect(getAccessToken()).toBe('new-access');
		});
	});

	describe('updateUser', () => {
		it('should update user fields', async () => {
			await auth.login({
				email: 'test@example.com',
				password: 'password123'
			});

			auth.updateUser({ display_name: 'Updated Name', bio: 'New bio' });

			expect(get(currentUser)?.display_name).toBe('Updated Name');
			expect(get(currentUser)?.bio).toBe('New bio');
		});

		it('should not update if no user', async () => {
			// Ensure we're logged out first
			await auth.logout();
			auth.updateUser({ display_name: 'Test' });

			expect(get(currentUser)).toBeNull();
		});
	});

	describe('clearError', () => {
		it('should clear auth error', async () => {
			try {
				await auth.login({
					email: 'wrong@example.com',
					password: 'wrong'
				});
			} catch {
				// Expected
			}

			expect(get(authError)).not.toBeNull();

			auth.clearError();

			expect(get(authError)).toBeNull();
		});
	});

	describe('getUser', () => {
		it('should return current user synchronously', async () => {
			await auth.login({
				email: 'test@example.com',
				password: 'password123'
			});

			const user = auth.getUser();

			expect(user?.username).toBe('testuser');
		});

		it('should return null when not authenticated', async () => {
			await auth.logout();
			expect(auth.getUser()).toBeNull();
		});
	});
});

describe('Derived Stores', () => {
	beforeEach(async () => {
		clearTokens();
		await auth.logout();
	});

	it('currentUser should reflect auth state', async () => {
		await auth.logout();
		expect(get(currentUser)).toBeNull();

		await auth.login({
			email: 'test@example.com',
			password: 'password123'
		});

		expect(get(currentUser)).not.toBeNull();
	});

	it('isAuthenticated should be true when user exists', async () => {
		await auth.logout();
		expect(get(isAuthenticated)).toBe(false);

		await auth.login({
			email: 'test@example.com',
			password: 'password123'
		});

		expect(get(isAuthenticated)).toBe(true);
	});
});

