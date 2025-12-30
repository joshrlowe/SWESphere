import { api, uploadFile } from './client';
import type { User, UserProfile, UserUpdate, PaginatedResponse } from '$lib/types';

// =============================================================================
// Users API
// =============================================================================

/**
 * Get user by ID
 */
export async function getUser(userId: number): Promise<UserProfile> {
	return api.get<UserProfile>(`/users/${userId}`);
}

/**
 * Get user by username
 */
export async function getUserByUsername(username: string): Promise<UserProfile> {
	return api.get<UserProfile>(`/users/username/${username}`);
}

/**
 * Update current user profile
 */
export async function updateProfile(data: UserUpdate): Promise<User> {
	return api.patch<User>('/users/me', data);
}

/**
 * Upload avatar
 */
export async function uploadAvatar(file: File): Promise<{ avatar_url: string }> {
	const result = await uploadFile('/users/me/avatar', file);
	return { avatar_url: result.url };
}

/**
 * Delete avatar
 */
export async function deleteAvatar(): Promise<void> {
	await api.delete('/users/me/avatar');
}

// =============================================================================
// Follow Operations
// =============================================================================

/**
 * Follow a user
 */
export async function followUser(userId: number): Promise<{ message: string }> {
	return api.post<{ message: string }>(`/users/${userId}/follow`);
}

/**
 * Unfollow a user
 */
export async function unfollowUser(userId: number): Promise<{ message: string }> {
	return api.delete<{ message: string }>(`/users/${userId}/follow`);
}

/**
 * Check if following a user
 */
export async function isFollowing(userId: number): Promise<boolean> {
	const response = await api.get<{ is_following: boolean }>(`/users/${userId}/following`);
	return response.is_following;
}

/**
 * Get user's followers
 */
export async function getFollowers(
	userId: number,
	page: number = 1,
	perPage: number = 20
): Promise<PaginatedResponse<User>> {
	return api.get<PaginatedResponse<User>>(
		`/users/${userId}/followers?page=${page}&per_page=${perPage}`
	);
}

/**
 * Get users that user is following
 */
export async function getFollowing(
	userId: number,
	page: number = 1,
	perPage: number = 20
): Promise<PaginatedResponse<User>> {
	return api.get<PaginatedResponse<User>>(
		`/users/${userId}/following?page=${page}&per_page=${perPage}`
	);
}

// =============================================================================
// Discovery
// =============================================================================

/**
 * Search users
 */
export async function searchUsers(
	query: string,
	page: number = 1,
	perPage: number = 20
): Promise<PaginatedResponse<User>> {
	return api.get<PaginatedResponse<User>>(
		`/users/search?q=${encodeURIComponent(query)}&page=${page}&per_page=${perPage}`
	);
}

/**
 * Get suggested users to follow
 */
export async function getSuggestedUsers(limit: number = 5): Promise<User[]> {
	return api.get<User[]>(`/users/suggestions?limit=${limit}`);
}

/**
 * Autocomplete users for @mentions
 */
export async function autocompleteUsers(
	prefix: string,
	limit: number = 10
): Promise<{ id: number; username: string; display_name: string | null; avatar_url: string | null }[]> {
	return api.get(`/users/autocomplete?prefix=${encodeURIComponent(prefix)}&limit=${limit}`);
}

