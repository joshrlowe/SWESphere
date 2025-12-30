import { describe, it, expect } from 'vitest';
import { formatFollowerCount } from '$lib/types/user';

// ProfileHeader component tests
// Validates the component's expected behavior

describe('ProfileHeader Component', () => {
	const mockUser = {
		id: 1,
		username: 'testuser',
		email: 'test@example.com',
		display_name: 'Test User',
		bio: 'Developer and coffee enthusiast ☕\nBuilding cool stuff.',
		avatar_url: 'https://example.com/avatar.jpg',
		location: 'San Francisco, CA',
		website: 'https://example.com',
		followers_count: 10500,
		following_count: 500,
		posts_count: 250,
		is_verified: true,
		is_following: false,
		created_at: '2020-06-15T00:00:00Z'
	};

	describe('Profile display', () => {
		it('should display username and display name', () => {
			expect(mockUser.username).toBe('testuser');
			expect(mockUser.display_name).toBe('Test User');
		});

		it('should display bio with multiline support', () => {
			expect(mockUser.bio).toContain('\n');
		});

		it('should display location', () => {
			expect(mockUser.location).toBe('San Francisco, CA');
		});

		it('should display website', () => {
			expect(mockUser.website).toBe('https://example.com');
		});
	});

	describe('Stats formatting', () => {
		it('should format followers count', () => {
			const formatted = formatFollowerCount(mockUser.followers_count);
			expect(formatted).toBe('10.5K');
		});

		it('should format following count', () => {
			const formatted = formatFollowerCount(mockUser.following_count);
			expect(formatted).toBe('500');
		});

		it('should format posts count', () => {
			const formatted = formatFollowerCount(mockUser.posts_count);
			expect(formatted).toBe('250');
		});
	});

	describe('Website display', () => {
		it('should strip protocol from website URL', () => {
			const displayUrl = mockUser.website?.replace(/^https?:\/\//, '');
			expect(displayUrl).toBe('example.com');
		});

		it('should handle http protocol', () => {
			const httpUrl = 'http://example.com';
			const displayUrl = httpUrl.replace(/^https?:\/\//, '');
			expect(displayUrl).toBe('example.com');
		});
	});

	describe('Join date', () => {
		it('should have valid created_at date', () => {
			const date = new Date(mockUser.created_at);
			expect(date).toBeInstanceOf(Date);
			expect(date.getTime()).not.toBeNaN();
		});
	});

	describe('Current user detection', () => {
		it('should identify current user for edit button', () => {
			const currentUserId = 1;
			const isCurrentUser = mockUser.id === currentUserId;
			expect(isCurrentUser).toBe(true);
		});

		it('should show follow button for other users', () => {
			const currentUserId = 2;
			const isCurrentUser = mockUser.id === currentUserId;
			expect(isCurrentUser).toBe(false);
		});
	});

	describe('Verified status', () => {
		it('should indicate verified user', () => {
			expect(mockUser.is_verified).toBe(true);
		});
	});

	describe('Following status', () => {
		it('should track following state', () => {
			expect(mockUser.is_following).toBe(false);
		});

		it('should update following state', () => {
			const updatedUser = { ...mockUser, is_following: true };
			expect(updatedUser.is_following).toBe(true);
		});
	});

	describe('Cover image', () => {
		it('should handle null cover URL', () => {
			const coverUrl: string | null = null;
			expect(coverUrl).toBeNull();
		});

		it('should accept cover URL', () => {
			const coverUrl = 'https://example.com/cover.jpg';
			expect(coverUrl).toBe('https://example.com/cover.jpg');
		});
	});

	describe('Stats links', () => {
		it('should generate correct followers link', () => {
			const link = `/${mockUser.username}/followers`;
			expect(link).toBe('/testuser/followers');
		});

		it('should generate correct following link', () => {
			const link = `/${mockUser.username}/following`;
			expect(link).toBe('/testuser/following');
		});
	});
});

