import { describe, it, expect } from 'vitest';
import {
	UserSchema,
	UserProfileSchema,
	UserUpdateSchema,
	getDisplayName,
	getAvatarUrl,
	formatFollowerCount
} from '$lib/types/user';

describe('UserSchema', () => {
	it('should validate a complete user object', () => {
		const user = {
			id: 1,
			username: 'testuser',
			email: 'test@example.com',
			display_name: 'Test User',
			bio: 'A test bio',
			avatar_url: 'https://example.com/avatar.jpg',
			location: 'New York',
			website: 'https://example.com',
			followers_count: 100,
			following_count: 50,
			posts_count: 25,
			is_verified: true,
			created_at: '2024-01-01T00:00:00Z'
		};

		const result = UserSchema.safeParse(user);
		expect(result.success).toBe(true);
		if (result.success) {
			expect(result.data.username).toBe('testuser');
		}
	});

	it('should validate with minimal required fields', () => {
		const user = {
			id: 1,
			username: 'testuser',
			display_name: null,
			bio: null,
			avatar_url: null,
			location: null,
			website: null,
			created_at: null
		};

		const result = UserSchema.safeParse(user);
		expect(result.success).toBe(true);
		if (result.success) {
			expect(result.data.followers_count).toBe(0);
			expect(result.data.is_verified).toBe(false);
		}
	});

	it('should reject invalid email', () => {
		const user = {
			id: 1,
			username: 'testuser',
			email: 'not-an-email'
		};

		const result = UserSchema.safeParse(user);
		expect(result.success).toBe(false);
	});

	it('should allow null for optional fields', () => {
		const user = {
			id: 1,
			username: 'testuser',
			display_name: null,
			bio: null,
			avatar_url: null,
			location: null,
			website: null,
			created_at: null
		};

		const result = UserSchema.safeParse(user);
		expect(result.success).toBe(true);
	});
});

describe('UserProfileSchema', () => {
	it('should extend UserSchema with following fields', () => {
		const profile = {
			id: 1,
			username: 'testuser',
			display_name: null,
			bio: null,
			avatar_url: null,
			location: null,
			website: null,
			created_at: null,
			is_following: true,
			is_followed_by: false
		};

		const result = UserProfileSchema.safeParse(profile);
		expect(result.success).toBe(true);
		if (result.success) {
			expect(result.data.is_following).toBe(true);
			expect(result.data.is_followed_by).toBe(false);
		}
	});
});

describe('UserUpdateSchema', () => {
	it('should validate update data', () => {
		const update = {
			display_name: 'New Name',
			bio: 'New bio'
		};

		const result = UserUpdateSchema.safeParse(update);
		expect(result.success).toBe(true);
	});

	it('should reject display_name that is too long', () => {
		const update = {
			display_name: 'a'.repeat(101)
		};

		const result = UserUpdateSchema.safeParse(update);
		expect(result.success).toBe(false);
	});

	it('should reject bio that is too long', () => {
		const update = {
			bio: 'a'.repeat(161)
		};

		const result = UserUpdateSchema.safeParse(update);
		expect(result.success).toBe(false);
	});

	it('should validate website URL', () => {
		const update = {
			website: 'https://example.com'
		};

		const result = UserUpdateSchema.safeParse(update);
		expect(result.success).toBe(true);
	});

	it('should reject invalid website URL', () => {
		const update = {
			website: 'not-a-url'
		};

		const result = UserUpdateSchema.safeParse(update);
		expect(result.success).toBe(false);
	});
});

describe('getDisplayName', () => {
	it('should return display_name if available', () => {
		const user = { id: 1, username: 'testuser', display_name: 'Test User', avatar_url: null, is_verified: false };
		expect(getDisplayName(user)).toBe('Test User');
	});

	it('should return @username if no display_name', () => {
		const user = { id: 1, username: 'testuser', display_name: null, avatar_url: null, is_verified: false };
		expect(getDisplayName(user)).toBe('@testuser');
	});
});

describe('getAvatarUrl', () => {
	it('should return user avatar_url if available', () => {
		const user = { id: 1, username: 'test', display_name: null, avatar_url: 'https://example.com/avatar.jpg', is_verified: false };
		expect(getAvatarUrl(user)).toBe('https://example.com/avatar.jpg');
	});

	it('should return dicebear fallback if no avatar_url', () => {
		const user = { id: 1, username: 'test', display_name: null, avatar_url: null, is_verified: false };
		const url = getAvatarUrl(user);
		expect(url).toContain('dicebear.com');
		expect(url).toContain('seed=1');
	});

	it('should include size parameter', () => {
		const user = { id: 1, username: 'test', display_name: null, avatar_url: null, is_verified: false };
		const url = getAvatarUrl(user, 256);
		expect(url).toContain('size=256');
	});
});

describe('formatFollowerCount', () => {
	it('should format counts under 1000', () => {
		expect(formatFollowerCount(0)).toBe('0');
		expect(formatFollowerCount(999)).toBe('999');
	});

	it('should format counts in thousands', () => {
		expect(formatFollowerCount(1000)).toBe('1.0K');
		expect(formatFollowerCount(1500)).toBe('1.5K');
		expect(formatFollowerCount(10000)).toBe('10.0K');
		expect(formatFollowerCount(999999)).toBe('1000.0K');
	});

	it('should format counts in millions', () => {
		expect(formatFollowerCount(1000000)).toBe('1.0M');
		expect(formatFollowerCount(1500000)).toBe('1.5M');
		expect(formatFollowerCount(10000000)).toBe('10.0M');
	});
});

