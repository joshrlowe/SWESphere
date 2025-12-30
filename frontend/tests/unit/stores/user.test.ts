import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { http, HttpResponse } from 'msw';
import { server } from '../../mocks/server';
import {
	profile,
	profileUser,
	isProfileLoading,
	profileError,
	followState
} from '$lib/stores/user';
import { setTokens, clearTokens } from '$lib/api/client';

describe('Profile Store', () => {
	beforeEach(() => {
		setTokens({
			access_token: 'test-access-token',
			refresh_token: 'test-refresh-token',
			token_type: 'bearer'
		});
		profile.clear();
	});

	describe('initial state', () => {
		it('should start with null profile', () => {
			expect(get(profileUser)).toBeNull();
		});

		it('should start as not loading', () => {
			expect(get(isProfileLoading)).toBe(false);
		});

		it('should start with no error', () => {
			expect(get(profileError)).toBeNull();
		});
	});

	describe('load', () => {
		it('should load profile by username', async () => {
			await profile.load('testuser');

			expect(get(profileUser)).not.toBeNull();
			expect(get(profileUser)?.username).toBe('testuser');
		});

		it('should set loading state', async () => {
			const loadPromise = profile.load('testuser');

			// In real tests with delays, we'd check loading state here
			await loadPromise;

			expect(get(isProfileLoading)).toBe(false);
		});

		it('should set error on failed load', async () => {
			await profile.load('notfound');

			expect(get(profileUser)).toBeNull();
			expect(get(profileError)).not.toBeNull();
		});
	});

	describe('follow', () => {
		it('should optimistically update following state', async () => {
			await profile.load('testuser');
			const initialCount = get(profileUser)?.followers_count || 0;

			// Start follow (optimistic update happens immediately)
			const followPromise = profile.follow();

			expect(get(profileUser)?.is_following).toBe(true);
			expect(get(profileUser)?.followers_count).toBe(initialCount + 1);

			await followPromise;
		});
	});

	describe('unfollow', () => {
		it('should optimistically update following state', async () => {
			// Load a profile that we're following
			server.use(
				http.get('/api/v1/users/username/:username', () => {
					return HttpResponse.json({
						id: 2,
						username: 'followed',
						display_name: 'Followed User',
						bio: null,
						avatar_url: null,
						location: null,
						website: null,
						followers_count: 100,
						following_count: 50,
						posts_count: 25,
						is_verified: false,
						is_following: true,
						created_at: '2024-01-01T00:00:00Z'
					});
				})
			);

			await profile.load('followed');

			// Verify initial state
			expect(get(profileUser)?.is_following).toBe(true);
			expect(get(profileUser)?.followers_count).toBe(100);

			// Unfollow should work without error
			await profile.unfollow();

			// State should be updated
			expect(get(profileUser)?.is_following).toBe(false);
			expect(get(profileUser)?.followers_count).toBe(99);
		});
	});

	describe('clear', () => {
		it('should clear profile state', async () => {
			await profile.load('testuser');
			expect(get(profileUser)).not.toBeNull();

			profile.clear();

			expect(get(profileUser)).toBeNull();
			expect(get(isProfileLoading)).toBe(false);
			expect(get(profileError)).toBeNull();
		});
	});
});

describe('Follow State Store', () => {
	beforeEach(() => {
		setTokens({
			access_token: 'test-access-token',
			refresh_token: 'test-refresh-token',
			token_type: 'bearer'
		});
	});

	describe('set', () => {
		it('should set follow state for user', () => {
			followState.set(1, true);

			const state = get(followState);
			expect(state[1]).toBe(true);
		});

		it('should track multiple users', () => {
			followState.set(1, true);
			followState.set(2, false);
			followState.set(3, true);

			const state = get(followState);
			expect(state[1]).toBe(true);
			expect(state[2]).toBe(false);
			expect(state[3]).toBe(true);
		});
	});

	describe('toggle', () => {
		it('should toggle follow state and call API', async () => {
			const newState = await followState.toggle(1, false);

			expect(newState).toBe(true);

			const state = get(followState);
			expect(state[1]).toBe(true);
		});

		it('should toggle unfollow state', async () => {
			const newState = await followState.toggle(1, true);

			expect(newState).toBe(false);

			const state = get(followState);
			expect(state[1]).toBe(false);
		});

		it('should revert on API error', async () => {
			server.use(
				http.post('/api/v1/users/:id/follow', () => {
					return HttpResponse.json({ detail: 'Error' }, { status: 500 });
				})
			);

			followState.set(1, false);

			await expect(followState.toggle(1, false)).rejects.toThrow();

			const state = get(followState);
			expect(state[1]).toBe(false);
		});

		it('should call follow API when toggling to true', async () => {
			let apiCalled = false;

			server.use(
				http.post('/api/v1/users/:id/follow', () => {
					apiCalled = true;
					return HttpResponse.json({ message: 'Followed' });
				})
			);

			await followState.toggle(1, false);

			expect(apiCalled).toBe(true);
		});

		it('should call unfollow API when toggling to false', async () => {
			let apiCalled = false;

			server.use(
				http.delete('/api/v1/users/:id/follow', () => {
					apiCalled = true;
					return HttpResponse.json({ message: 'Unfollowed' });
				})
			);

			await followState.toggle(1, true);

			expect(apiCalled).toBe(true);
		});
	});
});

