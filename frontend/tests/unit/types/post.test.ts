import { describe, it, expect } from 'vitest';
import {
	PostSchema,
	PostAuthorSchema,
	PostCreateSchema,
	formatEngagementCount,
	getPostUrl,
	isThread
} from '$lib/types/post';

describe('PostAuthorSchema', () => {
	it('should validate author object', () => {
		const author = {
			id: 1,
			username: 'testuser',
			display_name: 'Test User',
			avatar_url: 'https://example.com/avatar.jpg',
			is_verified: true
		};

		const result = PostAuthorSchema.safeParse(author);
		expect(result.success).toBe(true);
	});

	it('should allow null display_name and avatar_url', () => {
		const author = {
			id: 1,
			username: 'testuser',
			display_name: null,
			avatar_url: null
		};

		const result = PostAuthorSchema.safeParse(author);
		expect(result.success).toBe(true);
		if (result.success) {
			expect(result.data.is_verified).toBe(false);
		}
	});
});

describe('PostSchema', () => {
	it('should validate a complete post object', () => {
		const post = {
			id: 1,
			body: 'This is a test post',
			media_url: 'https://example.com/image.jpg',
			media_type: 'image/jpeg',
			user_id: 1,
			reply_to_id: null,
			repost_of_id: null,
			likes_count: 10,
			comments_count: 5,
			reposts_count: 2,
			replies_count: 3,
			is_reply: false,
			is_repost: false,
			is_liked: true,
			created_at: '2024-01-01T12:00:00Z',
			updated_at: '2024-01-02T12:00:00Z',
			author: {
				id: 1,
				username: 'testuser',
				display_name: 'Test User',
				avatar_url: null,
				is_verified: false
			}
		};

		const result = PostSchema.safeParse(post);
		expect(result.success).toBe(true);
		if (result.success) {
			expect(result.data.body).toBe('This is a test post');
			expect(result.data.is_liked).toBe(true);
		}
	});

	it('should validate minimal post', () => {
		const post = {
			id: 1,
			body: 'Test',
			media_url: null,
			media_type: null,
			user_id: 1,
			reply_to_id: null,
			repost_of_id: null,
			created_at: '2024-01-01T12:00:00Z',
			updated_at: null
		};

		const result = PostSchema.safeParse(post);
		expect(result.success).toBe(true);
		if (result.success) {
			expect(result.data.likes_count).toBe(0);
			expect(result.data.is_liked).toBe(false);
		}
	});

	it('should allow null for optional fields', () => {
		const post = {
			id: 1,
			body: 'Test',
			media_url: null,
			media_type: null,
			user_id: 1,
			reply_to_id: null,
			repost_of_id: null,
			created_at: '2024-01-01T12:00:00Z',
			updated_at: null
		};

		const result = PostSchema.safeParse(post);
		expect(result.success).toBe(true);
	});
});

describe('PostCreateSchema', () => {
	it('should validate post creation data', () => {
		const data = {
			body: 'This is a new post'
		};

		const result = PostCreateSchema.safeParse(data);
		expect(result.success).toBe(true);
	});

	it('should reject empty body', () => {
		const data = {
			body: ''
		};

		const result = PostCreateSchema.safeParse(data);
		expect(result.success).toBe(false);
	});

	it('should reject body over 280 characters', () => {
		const data = {
			body: 'a'.repeat(281)
		};

		const result = PostCreateSchema.safeParse(data);
		expect(result.success).toBe(false);
	});

	it('should accept max 280 characters', () => {
		const data = {
			body: 'a'.repeat(280)
		};

		const result = PostCreateSchema.safeParse(data);
		expect(result.success).toBe(true);
	});

	it('should validate with reply_to_id', () => {
		const data = {
			body: 'This is a reply',
			reply_to_id: 123
		};

		const result = PostCreateSchema.safeParse(data);
		expect(result.success).toBe(true);
		if (result.success) {
			expect(result.data.reply_to_id).toBe(123);
		}
	});

	it('should validate media_url', () => {
		const data = {
			body: 'Post with image',
			media_url: 'https://example.com/image.jpg'
		};

		const result = PostCreateSchema.safeParse(data);
		expect(result.success).toBe(true);
	});

	it('should reject invalid media_url', () => {
		const data = {
			body: 'Post with image',
			media_url: 'not-a-url'
		};

		const result = PostCreateSchema.safeParse(data);
		expect(result.success).toBe(false);
	});
});

describe('formatEngagementCount', () => {
	it('should return empty string for 0', () => {
		expect(formatEngagementCount(0)).toBe('');
	});

	it('should return number as string for small counts', () => {
		expect(formatEngagementCount(1)).toBe('1');
		expect(formatEngagementCount(999)).toBe('999');
	});

	it('should format thousands', () => {
		expect(formatEngagementCount(1000)).toBe('1.0K');
		expect(formatEngagementCount(1234)).toBe('1.2K');
		expect(formatEngagementCount(99999)).toBe('100.0K');
	});

	it('should format millions', () => {
		expect(formatEngagementCount(1000000)).toBe('1.0M');
		expect(formatEngagementCount(1234567)).toBe('1.2M');
	});
});

describe('getPostUrl', () => {
	it('should return URL with author username', () => {
		const post = {
			id: 123,
			body: 'Test',
			user_id: 1,
			created_at: '2024-01-01T12:00:00Z',
			author: {
				id: 1,
				username: 'testuser',
				display_name: null,
				avatar_url: null,
				is_verified: false
			}
		};

		// @ts-expect-error - partial post for testing
		expect(getPostUrl(post)).toBe('/testuser/status/123');
	});

	it('should return fallback URL without author', () => {
		const post = {
			id: 123,
			body: 'Test',
			user_id: 1,
			created_at: '2024-01-01T12:00:00Z'
		};

		// @ts-expect-error - partial post for testing
		expect(getPostUrl(post)).toBe('/post/123');
	});
});

describe('isThread', () => {
	it('should return true for post with replies', () => {
		const post = {
			id: 1,
			body: 'Test',
			user_id: 1,
			replies_count: 5,
			is_reply: false,
			created_at: '2024-01-01T12:00:00Z'
		};

		// @ts-expect-error - partial post for testing
		expect(isThread(post)).toBe(true);
	});

	it('should return true for reply post', () => {
		const post = {
			id: 1,
			body: 'Test',
			user_id: 1,
			replies_count: 0,
			is_reply: true,
			created_at: '2024-01-01T12:00:00Z'
		};

		// @ts-expect-error - partial post for testing
		expect(isThread(post)).toBe(true);
	});

	it('should return false for standalone post', () => {
		const post = {
			id: 1,
			body: 'Test',
			user_id: 1,
			replies_count: 0,
			is_reply: false,
			created_at: '2024-01-01T12:00:00Z'
		};

		// @ts-expect-error - partial post for testing
		expect(isThread(post)).toBe(false);
	});
});

