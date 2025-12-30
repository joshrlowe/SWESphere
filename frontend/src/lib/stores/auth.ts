import { writable, derived, get } from 'svelte/store';
import { browser } from '$app/environment';
import { goto } from '$app/navigation';
import {
	isAuthenticated as checkAuth,
	setTokens as saveTokens,
	clearTokens
} from '$lib/api/client';
import { login as apiLogin, logout as apiLogout, getCurrentUser } from '$lib/api/auth';
import type { User, LoginCredentials, AuthTokens } from '$lib/types';

// =============================================================================
// Auth State
// =============================================================================

interface AuthState {
	user: User | null;
	isLoading: boolean;
	isInitialized: boolean;
	error: string | null;
}

const initialState: AuthState = {
	user: null,
	isLoading: false,
	isInitialized: false,
	error: null
};

function createAuthStore() {
	const { subscribe, set, update } = writable<AuthState>(initialState);

	return {
		subscribe,

		/**
		 * Initialize auth state on app load
		 */
		async initialize(): Promise<void> {
			if (!browser) return;

			update((s) => ({ ...s, isLoading: true }));

			try {
				if (checkAuth()) {
					const user = await getCurrentUser();
					update((s) => ({
						...s,
						user,
						isLoading: false,
						isInitialized: true,
						error: null
					}));
				} else {
					update((s) => ({
						...s,
						user: null,
						isLoading: false,
						isInitialized: true,
						error: null
					}));
				}
			} catch (error) {
				clearTokens();
				update((s) => ({
					...s,
					user: null,
					isLoading: false,
					isInitialized: true,
					error: null
				}));
			}
		},

		/**
		 * Login with credentials
		 */
		async login(credentials: LoginCredentials): Promise<void> {
			update((s) => ({ ...s, isLoading: true, error: null }));

			try {
				const response = await apiLogin(credentials);
				update((s) => ({
					...s,
					user: response.user,
					isLoading: false,
					error: null
				}));
				goto('/feed');
			} catch (error) {
				const message = error instanceof Error ? error.message : 'Login failed';
				update((s) => ({ ...s, isLoading: false, error: message }));
				throw error;
			}
		},

		/**
		 * Set tokens and user after registration
		 */
		setAuth(tokens: AuthTokens, user: User): void {
			saveTokens(tokens);
			update((s) => ({ ...s, user, error: null }));
		},

		/**
		 * Logout
		 */
		async logout(): Promise<void> {
			update((s) => ({ ...s, isLoading: true }));

			try {
				await apiLogout();
			} finally {
				set({ ...initialState, isInitialized: true });
				goto('/auth/login');
			}
		},

		/**
		 * Update user profile in store
		 */
		updateUser(updates: Partial<User>): void {
			update((s) => ({
				...s,
				user: s.user ? { ...s.user, ...updates } : null
			}));
		},

		/**
		 * Clear any error
		 */
		clearError(): void {
			update((s) => ({ ...s, error: null }));
		},

		/**
		 * Get current user synchronously
		 */
		getUser(): User | null {
			return get({ subscribe }).user;
		}
	};
}

export const auth = createAuthStore();

// =============================================================================
// Derived Stores
// =============================================================================

export const currentUser = derived(auth, ($auth) => $auth.user);

export const isAuthenticated = derived(auth, ($auth) => $auth.user !== null);

export const isAuthLoading = derived(auth, ($auth) => $auth.isLoading);

export const isAuthInitialized = derived(auth, ($auth) => $auth.isInitialized);

export const authError = derived(auth, ($auth) => $auth.error);

