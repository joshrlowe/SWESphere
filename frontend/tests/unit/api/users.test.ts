import { describe, it, expect, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../../mocks/server';
import {
	getUser,
	getUserByUsername,
	updateProfile,
	uploadAvatar,
	deleteAvatar,
	followUser,
	unfollowUser,
	isFollowing,
	getFollowers,
	getFollowing,
	searchUsers,
	getSuggestedUsers,
	autocompleteUsers
} from '$lib/api/users';
import { setTokens } from '$lib/api/client';

describe('Users API', () => {
	beforeEach(() => {
		setTokens({
			access_token: 'test-access-token',
			refresh_token: 'test-refresh-token',
			token_type: 'bearer'
		});
	});

	describe('getUser', () => {
		it('should get user by ID', async () => {
			const user = await getUser(1);

			expect(user.id).toBe(1);
			expect(user.username).toBeDefined();
		});
	});

	describe('getUserByUsername', () => {
		it('should get user by username', async () => {
			const user = await getUserByUsername('testuser');

			expect(user.username).toBe('testuser');
		});

		it('should throw on non-existent user', async () => {
			await expect(getUserByUsername('notfound')).rejects.toThrow();
		});
	});

	describe('updateProfile', () => {
		it('should update profile', async () => {
			const user = await updateProfile({
				display_name: 'New Name',
				bio: 'New bio'
			});

			expect(user.display_name).toBe('New Name');
			expect(user.bio).toBe('New bio');
		});
	});

	describe('uploadAvatar', () => {
		it('should upload avatar and return URL', async () => {
			const file = new File(['test'], 'avatar.jpg', { type: 'image/jpeg' });
			const result = await uploadAvatar(file);

			expect(result.avatar_url).toBeDefined();
		});
	});

	describe('deleteAvatar', () => {
		it('should delete avatar', async () => {
			await expect(deleteAvatar()).resolves.not.toThrow();
		});
	});

	describe('followUser', () => {
		it('should follow a user', async () => {
			const result = await followUser(2);

			expect(result.message).toBe('Followed successfully');
		});
	});

	describe('unfollowUser', () => {
		it('should unfollow a user', async () => {
			const result = await unfollowUser(2);

			expect(result.message).toBe('Unfollowed successfully');
		});
	});

	describe('isFollowing', () => {
		it('should check following status', async () => {
			const following = await isFollowing(2);

			expect(typeof following).toBe('boolean');
		});
	});

	describe('getFollowers', () => {
		it('should get user followers', async () => {
			const followers = await getFollowers(1);

			expect(followers.items).toBeDefined();
			expect(followers.total).toBeDefined();
		});
	});

	describe('getFollowing', () => {
		it('should get users being followed', async () => {
			const following = await getFollowing(1);

			expect(following).toBeDefined();
		});
	});

	describe('searchUsers', () => {
		it('should search users by query', async () => {
			const results = await searchUsers('test');

			expect(results).toBeDefined();
		});
	});

	describe('getSuggestedUsers', () => {
		it('should get suggested users', async () => {
			const suggestions = await getSuggestedUsers(5);

			expect(suggestions).toBeDefined();
		});
	});

	describe('autocompleteUsers', () => {
		it('should autocomplete users by prefix', async () => {
			const results = await autocompleteUsers('te', 10);

			expect(results).toBeDefined();
		});
	});
});

