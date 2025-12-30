import { api } from './client';
import type { Post, PostCreate, PostsResponse } from '$lib/types';

// =============================================================================
// Posts API
// =============================================================================

/**
 * Create a new post
 */
export async function createPost(data: PostCreate): Promise<Post> {
	return api.post<Post>('/posts', data);
}

/**
 * Get a single post by ID
 */
export async function getPost(postId: number): Promise<Post> {
	return api.get<Post>(`/posts/${postId}`);
}

/**
 * Delete a post
 */
export async function deletePost(postId: number): Promise<void> {
	await api.delete(`/posts/${postId}`);
}

/**
 * Get home feed (posts from followed users)
 */
export async function getHomeFeed(page: number = 1, perPage: number = 20): Promise<PostsResponse> {
	return api.get<PostsResponse>(`/posts/feed?page=${page}&per_page=${perPage}`);
}

/**
 * Get explore feed (trending/recent posts)
 */
export async function getExploreFeed(
	page: number = 1,
	perPage: number = 20
): Promise<PostsResponse> {
	return api.get<PostsResponse>(`/posts/explore?page=${page}&per_page=${perPage}`);
}

/**
 * Get posts by a specific user
 */
export async function getUserPosts(
	userId: number,
	page: number = 1,
	perPage: number = 20
): Promise<PostsResponse> {
	return api.get<PostsResponse>(`/users/${userId}/posts?page=${page}&per_page=${perPage}`);
}

/**
 * Get posts by username
 */
export async function getUserPostsByUsername(
	username: string,
	page: number = 1,
	perPage: number = 20
): Promise<PostsResponse> {
	return api.get<PostsResponse>(`/users/${username}/posts?page=${page}&per_page=${perPage}`);
}

/**
 * Search posts
 */
export async function searchPosts(
	query: string,
	page: number = 1,
	perPage: number = 20
): Promise<PostsResponse> {
	return api.get<PostsResponse>(
		`/posts/search?q=${encodeURIComponent(query)}&page=${page}&per_page=${perPage}`
	);
}

/**
 * Get replies to a post
 */
export async function getPostReplies(
	postId: number,
	page: number = 1,
	perPage: number = 20
): Promise<PostsResponse> {
	return api.get<PostsResponse>(`/posts/${postId}/replies?page=${page}&per_page=${perPage}`);
}

// =============================================================================
// Like Operations
// =============================================================================

/**
 * Like a post
 */
export async function likePost(postId: number): Promise<{ likes_count: number }> {
	return api.post<{ likes_count: number }>(`/posts/${postId}/like`);
}

/**
 * Unlike a post
 */
export async function unlikePost(postId: number): Promise<{ likes_count: number }> {
	return api.delete<{ likes_count: number }>(`/posts/${postId}/like`);
}

/**
 * Check if current user liked a post
 */
export async function isPostLiked(postId: number): Promise<boolean> {
	const response = await api.get<{ is_liked: boolean }>(`/posts/${postId}/like`);
	return response.is_liked;
}

// =============================================================================
// Repost Operations
// =============================================================================

/**
 * Repost a post
 */
export async function repost(postId: number, body?: string): Promise<Post> {
	return api.post<Post>(`/posts/${postId}/repost`, body ? { body } : undefined);
}

/**
 * Undo repost
 */
export async function unrepost(postId: number): Promise<void> {
	await api.delete(`/posts/${postId}/repost`);
}

