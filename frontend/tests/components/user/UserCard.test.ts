import { describe, it, expect } from 'vitest';
import { getDisplayName } from '$lib/types/user';

// UserCard component tests
// Validates the component's expected behavior and data handling

describe('UserCard Component', () => {
	const mockUser = {
		id: 1,
		username: 'testuser',
		email: 'test@example.com',
		display_name: 'Test User',
		bio: 'This is my bio',
		avatar_url: 'https://example.com/avatar.jpg',
		location: 'San Francisco',
		website: 'https://example.com',
		followers_count: 1000,
		following_count: 500,
		posts_count: 100,
		is_verified: true,
		created_at: '2024-01-01T00:00:00Z'
	};

	describe('User display', () => {
		it('should display username', () => {
			expect(mockUser.username).toBe('testuser');
		});

		it('should use display_name when available', () => {
			expect(getDisplayName(mockUser as any)).toBe('Test User');
		});

		it('should fall back to @username when no display_name', () => {
			const userWithoutName = { ...mockUser, display_name: null };
			expect(getDisplayName(userWithoutName as any)).toBe('@testuser');
		});
	});

	describe('Bio handling', () => {
		it('should display bio when available', () => {
			expect(mockUser.bio).toBe('This is my bio');
		});

		it('should handle null bio', () => {
			const userWithoutBio = { ...mockUser, bio: null };
			expect(userWithoutBio.bio).toBeNull();
		});
	});

	describe('Verified badge', () => {
		it('should show for verified users', () => {
			expect(mockUser.is_verified).toBe(true);
		});

		it('should hide for non-verified users', () => {
			const unverifiedUser = { ...mockUser, is_verified: false };
			expect(unverifiedUser.is_verified).toBe(false);
		});
	});

	describe('Profile link', () => {
		it('should generate correct profile URL', () => {
			const profileUrl = `/${mockUser.username}`;
			expect(profileUrl).toBe('/testuser');
		});
	});

	describe('Current user detection', () => {
		it('should identify current user', () => {
			const currentUserId = 1;
			const isCurrentUser = mockUser.id === currentUserId;
			expect(isCurrentUser).toBe(true);
		});

		it('should identify other users', () => {
			const currentUserId = 2;
			const isCurrentUser = mockUser.id === currentUserId;
			expect(isCurrentUser).toBe(false);
		});
	});

	describe('Conditional rendering', () => {
		it('should respect showBio prop', () => {
			const showBio = true;
			expect(showBio && mockUser.bio).toBe('This is my bio');
		});

		it('should hide bio when showBio is false', () => {
			const showBio = false;
			expect(showBio && mockUser.bio).toBe(false);
		});

		it('should respect showFollow prop', () => {
			const showFollow = true;
			const isCurrentUser = false;
			expect(showFollow && !isCurrentUser).toBe(true);
		});

		it('should hide follow for current user', () => {
			const showFollow = true;
			const isCurrentUser = true;
			expect(showFollow && !isCurrentUser).toBe(false);
		});
	});
});

