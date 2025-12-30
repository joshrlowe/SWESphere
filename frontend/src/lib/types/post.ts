import { z } from 'zod';
import type { UserPreview } from './user';

// =============================================================================
// Post Schemas
// =============================================================================

export const PostAuthorSchema = z.object({
	id: z.number(),
	username: z.string(),
	display_name: z.string().nullable(),
	avatar_url: z.string().nullable(),
	is_verified: z.boolean().default(false)
});

export const PostSchema = z.object({
	id: z.number(),
	body: z.string(),
	media_url: z.string().nullable(),
	media_type: z.string().nullable(),
	user_id: z.number(),
	reply_to_id: z.number().nullable(),
	repost_of_id: z.number().nullable(),
	likes_count: z.number().default(0),
	comments_count: z.number().default(0),
	reposts_count: z.number().default(0),
	replies_count: z.number().default(0),
	is_reply: z.boolean().default(false),
	is_repost: z.boolean().default(false),
	is_liked: z.boolean().default(false),
	created_at: z.string(),
	updated_at: z.string().nullable(),
	author: PostAuthorSchema.optional()
});

export const PostCreateSchema = z.object({
	body: z.string().min(1).max(280),
	reply_to_id: z.number().optional(),
	media_url: z.string().url().optional()
});

// =============================================================================
// Types
// =============================================================================

export type Post = z.infer<typeof PostSchema>;
export type PostAuthor = z.infer<typeof PostAuthorSchema>;
export type PostCreate = z.infer<typeof PostCreateSchema>;

// =============================================================================
// Post with Author (for display)
// =============================================================================

export interface PostWithAuthor extends Post {
	author: UserPreview;
}

// =============================================================================
// Pagination
// =============================================================================

export interface PaginatedResponse<T> {
	items: T[];
	total: number;
	page: number;
	per_page: number;
	total_pages: number;
	has_next: boolean;
	has_prev: boolean;
}

export type PostsResponse = PaginatedResponse<Post>;

// =============================================================================
// Helper Functions
// =============================================================================

export function formatEngagementCount(count: number): string {
	if (count >= 1_000_000) {
		return `${(count / 1_000_000).toFixed(1)}M`;
	}
	if (count >= 1_000) {
		return `${(count / 1_000).toFixed(1)}K`;
	}
	if (count === 0) {
		return '';
	}
	return count.toString();
}

export function getPostUrl(post: Post): string {
	const author = post.author;
	if (author) {
		return `/${author.username}/status/${post.id}`;
	}
	return `/post/${post.id}`;
}

export function isThread(post: Post): boolean {
	return post.replies_count > 0 || post.is_reply;
}

