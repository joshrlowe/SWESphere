// Re-export all types
export * from './user';
export * from './post';

// =============================================================================
// Common Types
// =============================================================================

export interface ApiError {
	detail: string;
	status_code?: number;
}

export interface AuthTokens {
	access_token: string;
	refresh_token: string;
	token_type: string;
}

export interface LoginCredentials {
	email: string;
	password: string;
}

export interface RegisterData {
	username: string;
	email: string;
	password: string;
}

// =============================================================================
// Notification Types
// =============================================================================

export type NotificationType =
	| 'new_follower'
	| 'post_liked'
	| 'post_commented'
	| 'post_reposted'
	| 'mentioned'
	| 'reply'
	| 'system';

export interface Notification {
	id: number;
	type: NotificationType;
	message: string;
	data: Record<string, unknown>;
	read: boolean;
	user_id: number;
	actor_id: number | null;
	created_at: string;
	actor?: {
		id: number;
		username: string;
		display_name: string | null;
		avatar_url: string | null;
		is_verified: boolean;
	};
}

// =============================================================================
// Feed Types
// =============================================================================

export type FeedType = 'home' | 'explore' | 'user' | 'search';

export interface FeedParams {
	page?: number;
	per_page?: number;
	user_id?: number;
	query?: string;
}

