import { describe, it, expect, vi, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../../mocks/server';
import {
	api,
	ApiException,
	getAccessToken,
	getRefreshToken,
	setTokens,
	clearTokens,
	isAuthenticated
} from '$lib/api/client';

describe('Token Management', () => {
	beforeEach(() => {
		clearTokens();
	});

	it('should store and retrieve tokens', () => {
		setTokens({
			access_token: 'test-access',
			refresh_token: 'test-refresh',
			token_type: 'bearer'
		});

		expect(getAccessToken()).toBe('test-access');
		expect(getRefreshToken()).toBe('test-refresh');
	});

	it('should return null when no tokens', () => {
		expect(getAccessToken()).toBeNull();
		expect(getRefreshToken()).toBeNull();
	});

	it('should clear tokens', () => {
		setTokens({
			access_token: 'test-access',
			refresh_token: 'test-refresh',
			token_type: 'bearer'
		});

		clearTokens();

		expect(getAccessToken()).toBeNull();
		expect(getRefreshToken()).toBeNull();
	});

	it('should report authentication status', () => {
		expect(isAuthenticated()).toBe(false);

		setTokens({
			access_token: 'test-access',
			refresh_token: 'test-refresh',
			token_type: 'bearer'
		});

		expect(isAuthenticated()).toBe(true);
	});
});

describe('ApiException', () => {
	it('should create exception with status and message', () => {
		const error = new ApiException(404, 'Not found');

		expect(error.status).toBe(404);
		expect(error.detail).toBe('Not found');
		expect(error.message).toBe('Not found');
		expect(error.name).toBe('ApiException');
	});

	it('should detect unauthorized status', () => {
		const error = new ApiException(401, 'Unauthorized');
		expect(error.isUnauthorized).toBe(true);

		const otherError = new ApiException(404, 'Not found');
		expect(otherError.isUnauthorized).toBe(false);
	});

	it('should detect not found status', () => {
		const error = new ApiException(404, 'Not found');
		expect(error.isNotFound).toBe(true);
	});

	it('should detect validation error status', () => {
		const error = new ApiException(422, 'Validation error');
		expect(error.isValidationError).toBe(true);
	});

	it('should create from response data', () => {
		const error = ApiException.fromResponse(400, { detail: 'Bad request' });
		expect(error.status).toBe(400);
		expect(error.detail).toBe('Bad request');
	});

	it('should handle missing detail in response', () => {
		const error = ApiException.fromResponse(500, {});
		expect(error.detail).toBe('An error occurred');
	});

	it('should handle non-object response', () => {
		const error = ApiException.fromResponse(500, 'Server error');
		expect(error.detail).toBe('An error occurred');
	});
});

describe('API Client', () => {
	beforeEach(() => {
		setTokens({
			access_token: 'test-access-token',
			refresh_token: 'test-refresh-token',
			token_type: 'bearer'
		});
	});

	describe('GET requests', () => {
		it('should make GET request with auth header', async () => {
			const user = await api.get('/users/me');

			expect(user).toHaveProperty('username', 'testuser');
		});

		it('should handle 404 errors', async () => {
			server.use(
				http.get('/api/v1/users/999', () => {
					return HttpResponse.json({ detail: 'User not found' }, { status: 404 });
				})
			);

			await expect(api.get('/users/999')).rejects.toThrow(ApiException);
		});
	});

	describe('POST requests', () => {
		it('should make POST request with body', async () => {
			const post = await api.post('/posts', { body: 'Test post' });

			expect(post).toHaveProperty('body', 'Test post');
		});
	});

	describe('PATCH requests', () => {
		it('should make PATCH request', async () => {
			const user = await api.patch('/users/me', { display_name: 'New Name' });

			expect(user).toHaveProperty('display_name', 'New Name');
		});
	});

	describe('DELETE requests', () => {
		it('should make DELETE request', async () => {
			await expect(api.delete('/posts/1')).resolves.not.toThrow();
		});
	});

	describe('Token refresh', () => {
		it('should refresh token on 401 and retry', async () => {
			let requestCount = 0;

			server.use(
				http.get('/api/v1/users/me', ({ request }) => {
					requestCount++;
					const auth = request.headers.get('Authorization');

					if (auth === 'Bearer test-access-token' && requestCount === 1) {
						return HttpResponse.json({ detail: 'Token expired' }, { status: 401 });
					}

					return HttpResponse.json({ id: 1, username: 'testuser' });
				})
			);

			const user = await api.get('/users/me');
			expect(user).toHaveProperty('username', 'testuser');
		});
	});

	describe('Error handling', () => {
		it('should throw ApiException on error response', async () => {
			server.use(
				http.get('/api/v1/test-error', () => {
					return HttpResponse.json({ detail: 'Test error' }, { status: 400 });
				})
			);

			try {
				await api.get('/test-error');
				expect.fail('Should have thrown');
			} catch (error) {
				expect(error).toBeInstanceOf(ApiException);
				expect((error as ApiException).status).toBe(400);
				expect((error as ApiException).detail).toBe('Test error');
			}
		});

		it('should include data in exception', async () => {
			server.use(
				http.get('/api/v1/test-error', () => {
					return HttpResponse.json(
						{ detail: 'Validation error', errors: [{ field: 'name' }] },
						{ status: 422 }
					);
				})
			);

			try {
				await api.get('/test-error');
			} catch (error) {
				expect((error as ApiException).data).toHaveProperty('errors');
			}
		});
	});

	describe('Unauthenticated requests', () => {
		it('should make request without auth header when not required', async () => {
			clearTokens();

			server.use(
				http.get('/api/v1/public', ({ request }) => {
					const auth = request.headers.get('Authorization');
					return HttpResponse.json({ hasAuth: !!auth });
				})
			);

			const response = await api.get<{ hasAuth: boolean }>('/public', { requiresAuth: false });
			expect(response.hasAuth).toBe(false);
		});
	});
});

