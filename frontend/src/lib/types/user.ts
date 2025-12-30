import { z } from 'zod';

// =============================================================================
// User Schemas
// =============================================================================

export const UserSchema = z.object({
	id: z.number(),
	username: z.string(),
	email: z.string().email().optional(),
	display_name: z.string().nullable(),
	bio: z.string().nullable(),
	avatar_url: z.string().nullable(),
	location: z.string().nullable(),
	website: z.string().nullable(),
	followers_count: z.number().default(0),
	following_count: z.number().default(0),
	posts_count: z.number().default(0),
	is_verified: z.boolean().default(false),
	created_at: z.string().nullable()
});

export const UserProfileSchema = UserSchema.extend({
	is_following: z.boolean().optional(),
	is_followed_by: z.boolean().optional()
});

export const UserUpdateSchema = z.object({
	display_name: z.string().min(1).max(100).optional(),
	bio: z.string().max(160).optional(),
	location: z.string().max(100).optional(),
	website: z.string().url().max(255).optional()
});

// =============================================================================
// Types
// =============================================================================

export type User = z.infer<typeof UserSchema>;
export type UserProfile = z.infer<typeof UserProfileSchema>;
export type UserUpdate = z.infer<typeof UserUpdateSchema>;

// =============================================================================
// User Preview (minimal data for lists)
// =============================================================================

export interface UserPreview {
	id: number;
	username: string;
	display_name: string | null;
	avatar_url: string | null;
	is_verified: boolean;
}

// =============================================================================
// Helper Functions
// =============================================================================

export function getDisplayName(user: User | UserPreview): string {
	return user.display_name || `@${user.username}`;
}

export function getAvatarUrl(user: User | UserPreview, size: number = 128): string {
	if (user.avatar_url) {
		return user.avatar_url;
	}
	// Gravatar fallback (using id as seed for consistent placeholder)
	return `https://api.dicebear.com/7.x/identicon/svg?seed=${user.id}&size=${size}`;
}

export function formatFollowerCount(count: number): string {
	if (count >= 1_000_000) {
		return `${(count / 1_000_000).toFixed(1)}M`;
	}
	if (count >= 1_000) {
		return `${(count / 1_000).toFixed(1)}K`;
	}
	return count.toString();
}

