import { writable, derived } from 'svelte/store';
import type { User, UserProfile } from '$lib/types';
import { getUserByUsername, followUser, unfollowUser } from '$lib/api/users';

// =============================================================================
// Profile View State
// =============================================================================

interface ProfileState {
	profile: UserProfile | null;
	isLoading: boolean;
	error: string | null;
}

const initialState: ProfileState = {
	profile: null,
	isLoading: false,
	error: null
};

function createProfileStore() {
	const { subscribe, set, update } = writable<ProfileState>(initialState);

	return {
		subscribe,

		/**
		 * Load user profile by username
		 */
		async load(username: string): Promise<void> {
			update((s) => ({ ...s, isLoading: true, error: null }));

			try {
				const profile = await getUserByUsername(username);
				update((s) => ({ ...s, profile, isLoading: false }));
			} catch (error) {
				const message = error instanceof Error ? error.message : 'Failed to load profile';
				update((s) => ({ ...s, profile: null, isLoading: false, error: message }));
			}
		},

		/**
		 * Follow the current profile user
		 */
		async follow(): Promise<void> {
			let profileId: number | null = null;

			update((s) => {
				if (!s.profile) return s;
				profileId = s.profile.id;
				return {
					...s,
					profile: {
						...s.profile,
						is_following: true,
						followers_count: s.profile.followers_count + 1
					}
				};
			});

			if (profileId) {
				try {
					await followUser(profileId);
				} catch (error) {
					// Revert on error
					update((s) => {
						if (!s.profile) return s;
						return {
							...s,
							profile: {
								...s.profile,
								is_following: false,
								followers_count: Math.max(0, s.profile.followers_count - 1)
							}
						};
					});
				}
			}
		},

		/**
		 * Unfollow the current profile user
		 */
		async unfollow(): Promise<void> {
			let profileId: number | null = null;

			update((s) => {
				if (!s.profile) return s;
				profileId = s.profile.id;
				return {
					...s,
					profile: {
						...s.profile,
						is_following: false,
						followers_count: Math.max(0, s.profile.followers_count - 1)
					}
				};
			});

			if (profileId) {
				try {
					await unfollowUser(profileId);
				} catch (error) {
					// Revert on error
					update((s) => {
						if (!s.profile) return s;
						return {
							...s,
							profile: {
								...s.profile,
								is_following: true,
								followers_count: s.profile.followers_count + 1
							}
						};
					});
				}
			}
		},

		/**
		 * Clear profile state
		 */
		clear(): void {
			set(initialState);
		}
	};
}

export const profile = createProfileStore();

// =============================================================================
// Derived Stores
// =============================================================================

export const profileUser = derived(profile, ($profile) => $profile.profile);

export const isProfileLoading = derived(profile, ($profile) => $profile.isLoading);

export const profileError = derived(profile, ($profile) => $profile.error);

// =============================================================================
// Follow State Cache
// =============================================================================

interface FollowState {
	[userId: number]: boolean;
}

function createFollowStore() {
	const { subscribe, update } = writable<FollowState>({});

	return {
		subscribe,

		/**
		 * Set follow state for a user
		 */
		set(userId: number, isFollowing: boolean): void {
			update((s) => ({ ...s, [userId]: isFollowing }));
		},

		/**
		 * Toggle follow state
		 */
		async toggle(userId: number, currentlyFollowing: boolean): Promise<boolean> {
			const newState = !currentlyFollowing;

			// Optimistic update
			update((s) => ({ ...s, [userId]: newState }));

			try {
				if (newState) {
					await followUser(userId);
				} else {
					await unfollowUser(userId);
				}
				return newState;
			} catch (error) {
				// Revert on error
				update((s) => ({ ...s, [userId]: currentlyFollowing }));
				throw error;
			}
		}
	};
}

export const followState = createFollowStore();

