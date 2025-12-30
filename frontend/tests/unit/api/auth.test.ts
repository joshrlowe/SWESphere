import { describe, it, expect, vi, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../../mocks/server';
import {
	login,
	register,
	logout,
	getCurrentUser,
	requestPasswordReset,
	resetPassword,
	changePassword
} from '$lib/api/auth';
import { clearTokens, setTokens, getAccessToken } from '$lib/api/client';

describe('Auth API', () => {
	beforeEach(() => {
		clearTokens();
	});

	describe('login', () => {
		it('should login with valid credentials', async () => {
			const response = await login({
				email: 'test@example.com',
				password: 'password123'
			});

			expect(response.user.username).toBe('testuser');
			expect(response.access_token).toBe('test-access-token');
			expect(getAccessToken()).toBe('test-access-token');
		});

		it('should throw on invalid credentials', async () => {
			await expect(
				login({ email: 'wrong@example.com', password: 'wrong' })
			).rejects.toThrow('Invalid credentials');
		});

		it('should store tokens after login', async () => {
			await login({
				email: 'test@example.com',
				password: 'password123'
			});

			expect(getAccessToken()).toBe('test-access-token');
		});
	});

	describe('register', () => {
		it('should register new user', async () => {
			const response = await register({
				username: 'newuser',
				email: 'new@example.com',
				password: 'password123'
			});

			expect(response.user.username).toBe('newuser');
			expect(response.message).toBe('User registered successfully');
		});

		it('should throw on existing username', async () => {
			await expect(
				register({
					username: 'existing',
					email: 'test@example.com',
					password: 'password123'
				})
			).rejects.toThrow();
		});
	});

	describe('logout', () => {
		it('should clear tokens on logout', async () => {
			setTokens({
				access_token: 'test',
				refresh_token: 'test',
				token_type: 'bearer'
			});

			await logout();

			expect(getAccessToken()).toBeNull();
		});

		it('should clear tokens even if API call fails', async () => {
			server.use(
				http.post('/api/v1/auth/logout', () => {
					return HttpResponse.json({ detail: 'Error' }, { status: 500 });
				})
			);

			setTokens({
				access_token: 'test',
				refresh_token: 'test',
				token_type: 'bearer'
			});

			await logout();

			expect(getAccessToken()).toBeNull();
		});
	});

	describe('getCurrentUser', () => {
		it('should get current user when authenticated', async () => {
			setTokens({
				access_token: 'test-access-token',
				refresh_token: 'test-refresh-token',
				token_type: 'bearer'
			});

			const user = await getCurrentUser();

			expect(user.username).toBe('testuser');
		});

		it('should throw when not authenticated', async () => {
			await expect(getCurrentUser()).rejects.toThrow();
		});
	});

	describe('requestPasswordReset', () => {
		it('should request password reset', async () => {
			const response = await requestPasswordReset('test@example.com');

			expect(response.message).toBe('Password reset email sent');
		});
	});

	describe('resetPassword', () => {
		it('should reset password with token', async () => {
			const response = await resetPassword('reset-token', 'newpassword123');

			expect(response.message).toBe('Password reset successful');
		});
	});

	describe('changePassword', () => {
		it('should change password when authenticated', async () => {
			setTokens({
				access_token: 'test-access-token',
				refresh_token: 'test-refresh-token',
				token_type: 'bearer'
			});

			server.use(
				http.post('/api/v1/users/me/password', () => {
					return HttpResponse.json({ message: 'Password changed' });
				})
			);

			const response = await changePassword('oldpassword', 'newpassword');

			expect(response.message).toBe('Password changed');
		});
	});
});

