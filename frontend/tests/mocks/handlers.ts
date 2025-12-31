import { http, HttpResponse } from 'msw';

const API_BASE = '/api/v1';

// =============================================================================
// Test Data Factories
// =============================================================================

export const createMockUser = (overrides = {}) => ({
	id: 1,
	username: 'testuser',
	email: 'test@example.com',
	display_name: 'Test User',
	bio: 'This is a test bio',
	avatar_url: 'https://example.com/avatar.jpg',
	location: 'San Francisco, CA',
	website: 'https://example.com',
	followers_count: 100,
	following_count: 50,
	posts_count: 25,
	is_verified: false,
	is_following: false,
	created_at: '2024-01-01T00:00:00Z',
	...overrides
});

export const createMockPost = (overrides = {}) => ({
	id: 1,
	body: 'This is a test post',
	media_url: null,
	media_type: null,
	user_id: 1,
	reply_to_id: null,
	repost_of_id: null,
	likes_count: 10,
	comments_count: 5,
	reposts_count: 2,
	replies_count: 3,
	is_reply: false,
	is_repost: false,
	is_liked: false,
	created_at: '2024-01-01T12:00:00Z',
	updated_at: null,
	author: {
		id: 1,
		username: 'testuser',
		display_name: 'Test User',
		avatar_url: 'https://example.com/avatar.jpg',
		is_verified: false
	},
	...overrides
});

export const createMockNotification = (overrides = {}) => ({
	id: 1,
	type: 'new_follower',
	message: 'Test User followed you',
	data: {},
	read: false,
	user_id: 1,
	actor_id: 2,
	created_at: '2024-01-01T12:00:00Z',
	actor: {
		id: 2,
		username: 'otheruser',
		display_name: 'Other User',
		avatar_url: null,
		is_verified: false
	},
	...overrides
});

// =============================================================================
// Auth Handlers
// =============================================================================

export const authHandlers = [
	// Login - accepts JSON body with { username, password }
	http.post(`${API_BASE}/auth/login`, async ({ request }) => {
		const data = (await request.json()) as { username: string; password: string };

		if (data.username === 'test@example.com' && data.password === 'password123') {
			// Backend returns nested tokens structure
			return HttpResponse.json({
				user: createMockUser(),
				tokens: {
				access_token: 'test-access-token',
				refresh_token: 'test-refresh-token',
					token_type: 'bearer'
				}
			});
		}

		return HttpResponse.json({ detail: 'Invalid credentials' }, { status: 401 });
	}),

	// Register
	http.post(`${API_BASE}/auth/register`, async ({ request }) => {
		const data = await request.json() as { username: string; email: string; password: string };

		if (data.username === 'existing') {
			return HttpResponse.json({ detail: 'Username already exists' }, { status: 400 });
		}

		return HttpResponse.json({
			user: createMockUser({ username: data.username, email: data.email }),
			message: 'User registered successfully'
		});
	}),

	// Logout
	http.post(`${API_BASE}/auth/logout`, () => {
		return HttpResponse.json({ message: 'Logged out' });
	}),

	// Refresh token
	http.post(`${API_BASE}/auth/refresh`, async ({ request }) => {
		const data = await request.json() as { refresh_token: string };

		if (data.refresh_token === 'test-refresh-token') {
			return HttpResponse.json({
				access_token: 'new-access-token',
				refresh_token: 'new-refresh-token',
				token_type: 'bearer'
			});
		}

		return HttpResponse.json({ detail: 'Invalid refresh token' }, { status: 401 });
	}),

	// Password reset request
	http.post(`${API_BASE}/auth/password-reset/request`, () => {
		return HttpResponse.json({ message: 'Password reset email sent' });
	}),

	// Password reset
	http.post(`${API_BASE}/auth/password-reset`, () => {
		return HttpResponse.json({ message: 'Password reset successful' });
	})
];

// =============================================================================
// Users Handlers
// =============================================================================

export const usersHandlers = [
	// Get current user
	http.get(`${API_BASE}/users/me`, ({ request }) => {
		const auth = request.headers.get('Authorization');
		if (!auth?.includes('Bearer')) {
			return HttpResponse.json({ detail: 'Not authenticated' }, { status: 401 });
		}
		return HttpResponse.json(createMockUser());
	}),

	// Update profile
	http.patch(`${API_BASE}/users/me`, async ({ request }) => {
		const data = await request.json() as Partial<ReturnType<typeof createMockUser>>;
		return HttpResponse.json(createMockUser(data));
	}),

	// Upload avatar
	http.post(`${API_BASE}/users/me/avatar`, () => {
		return HttpResponse.json({ url: 'https://example.com/new-avatar.jpg' });
	}),

	// Delete avatar
	http.delete(`${API_BASE}/users/me/avatar`, () => {
		return new HttpResponse(null, { status: 204 });
	}),

	// Get user by ID
	http.get(`${API_BASE}/users/:id`, ({ params }) => {
		const id = Number(params.id);
		return HttpResponse.json(createMockUser({ id }));
	}),

	// Get user by username
	http.get(`${API_BASE}/users/username/:username`, ({ params }) => {
		const { username } = params;
		if (username === 'notfound') {
			return HttpResponse.json({ detail: 'User not found' }, { status: 404 });
		}
		return HttpResponse.json(createMockUser({ username: username as string }));
	}),

	// Follow user
	http.post(`${API_BASE}/users/:id/follow`, () => {
		return HttpResponse.json({ message: 'Followed successfully' });
	}),

	// Unfollow user
	http.delete(`${API_BASE}/users/:id/follow`, () => {
		return HttpResponse.json({ message: 'Unfollowed successfully' });
	}),

	// Check following status
	http.get(`${API_BASE}/users/:id/following`, () => {
		return HttpResponse.json({ is_following: false });
	}),

	// Get followers
	http.get(`${API_BASE}/users/:id/followers`, () => {
		return HttpResponse.json({
			items: [createMockUser({ id: 2, username: 'follower1' })],
			total: 1,
			page: 1,
			per_page: 20,
			total_pages: 1,
			has_next: false,
			has_prev: false
		});
	}),

	// Get following
	http.get(`${API_BASE}/users/:id/following`, () => {
		return HttpResponse.json({
			items: [createMockUser({ id: 3, username: 'following1' })],
			total: 1,
			page: 1,
			per_page: 20,
			total_pages: 1,
			has_next: false,
			has_prev: false
		});
	}),

	// Search users
	http.get(`${API_BASE}/users/search`, ({ request }) => {
		const url = new URL(request.url);
		const query = url.searchParams.get('q') || '';
		return HttpResponse.json({
			items: [createMockUser({ username: query })],
			total: 1,
			page: 1,
			per_page: 20,
			total_pages: 1,
			has_next: false,
			has_prev: false
		});
	}),

	// Suggested users
	http.get(`${API_BASE}/users/suggestions`, () => {
		return HttpResponse.json([
			createMockUser({ id: 2, username: 'suggested1' }),
			createMockUser({ id: 3, username: 'suggested2' })
		]);
	}),

	// Autocomplete users
	http.get(`${API_BASE}/users/autocomplete`, ({ request }) => {
		const url = new URL(request.url);
		const prefix = url.searchParams.get('prefix') || '';
		return HttpResponse.json([
			{ id: 1, username: `${prefix}user`, display_name: 'User', avatar_url: null }
		]);
	})
];

// =============================================================================
// Posts Handlers
// =============================================================================

export const postsHandlers = [
	// Create post
	http.post(`${API_BASE}/posts`, async ({ request }) => {
		const data = await request.json() as { body: string };
		return HttpResponse.json(createMockPost({ body: data.body }));
	}),

	// Get post by ID
	http.get(`${API_BASE}/posts/:id`, ({ params }) => {
		const id = Number(params.id);
		if (id === 999) {
			return HttpResponse.json({ detail: 'Post not found' }, { status: 404 });
		}
		return HttpResponse.json(createMockPost({ id }));
	}),

	// Delete post
	http.delete(`${API_BASE}/posts/:id`, () => {
		return new HttpResponse(null, { status: 204 });
	}),

	// Get home feed
	http.get(`${API_BASE}/posts/feed`, ({ request }) => {
		const url = new URL(request.url);
		const page = Number(url.searchParams.get('page') || 1);
		const perPage = Number(url.searchParams.get('per_page') || 20);

		const posts = Array.from({ length: perPage }, (_, i) =>
			createMockPost({ id: (page - 1) * perPage + i + 1 })
		);

		return HttpResponse.json({
			items: posts,
			total: 50,
			page,
			per_page: perPage,
			total_pages: 3,
			has_next: page < 3,
			has_prev: page > 1
		});
	}),

	// Get explore feed
	http.get(`${API_BASE}/posts/explore`, ({ request }) => {
		const url = new URL(request.url);
		const page = Number(url.searchParams.get('page') || 1);
		const perPage = Number(url.searchParams.get('per_page') || 20);

		const posts = Array.from({ length: perPage }, (_, i) =>
			createMockPost({ id: 100 + (page - 1) * perPage + i })
		);

		return HttpResponse.json({
			items: posts,
			total: 100,
			page,
			per_page: perPage,
			total_pages: 5,
			has_next: page < 5,
			has_prev: page > 1
		});
	}),

	// Get user posts
	http.get(`${API_BASE}/users/:username/posts`, ({ params, request }) => {
		const url = new URL(request.url);
		const page = Number(url.searchParams.get('page') || 1);

		return HttpResponse.json({
			items: [
				createMockPost({ id: 1, author: { ...createMockPost().author, username: params.username as string } })
			],
			total: 1,
			page,
			per_page: 20,
			total_pages: 1,
			has_next: false,
			has_prev: false
		});
	}),

	// Search posts
	http.get(`${API_BASE}/posts/search`, ({ request }) => {
		const url = new URL(request.url);
		const query = url.searchParams.get('q') || '';

		return HttpResponse.json({
			items: [createMockPost({ body: `Post about ${query}` })],
			total: 1,
			page: 1,
			per_page: 20,
			total_pages: 1,
			has_next: false,
			has_prev: false
		});
	}),

	// Get post replies
	http.get(`${API_BASE}/posts/:id/replies`, () => {
		return HttpResponse.json({
			items: [createMockPost({ id: 2, is_reply: true })],
			total: 1,
			page: 1,
			per_page: 20,
			total_pages: 1,
			has_next: false,
			has_prev: false
		});
	}),

	// Like post
	http.post(`${API_BASE}/posts/:id/like`, () => {
		return HttpResponse.json({ likes_count: 11 });
	}),

	// Unlike post
	http.delete(`${API_BASE}/posts/:id/like`, () => {
		return HttpResponse.json({ likes_count: 9 });
	}),

	// Check like status
	http.get(`${API_BASE}/posts/:id/like`, () => {
		return HttpResponse.json({ is_liked: false });
	}),

	// Repost
	http.post(`${API_BASE}/posts/:id/repost`, ({ params }) => {
		return HttpResponse.json(createMockPost({ id: 200, repost_of_id: Number(params.id), is_repost: true }));
	}),

	// Un-repost
	http.delete(`${API_BASE}/posts/:id/repost`, () => {
		return new HttpResponse(null, { status: 204 });
	})
];

// =============================================================================
// Notifications Handlers
// =============================================================================

export const notificationsHandlers = [
	http.get(`${API_BASE}/notifications`, () => {
		return HttpResponse.json({
			items: [
				createMockNotification({ id: 1 }),
				createMockNotification({ id: 2, type: 'post_liked', message: 'User liked your post', read: true })
			],
			total: 2,
			unread_count: 1
		});
	})
];

// =============================================================================
// All Handlers
// =============================================================================

export const handlers = [
	...authHandlers,
	...usersHandlers,
	...postsHandlers,
	...notificationsHandlers
];

