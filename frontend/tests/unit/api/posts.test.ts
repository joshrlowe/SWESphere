import { describe, it, expect, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../../mocks/server';
import {
	createPost,
	getPost,
	deletePost,
	getHomeFeed,
	getExploreFeed,
	getUserPosts,
	searchPosts,
	getPostReplies,
	likePost,
	unlikePost,
	isPostLiked,
	repost,
	unrepost
} from '$lib/api/posts';
import { setTokens } from '$lib/api/client';

describe('Posts API', () => {
	beforeEach(() => {
		setTokens({
			access_token: 'test-access-token',
			refresh_token: 'test-refresh-token',
			token_type: 'bearer'
		});
	});

	describe('createPost', () => {
		it('should create a new post', async () => {
			const post = await createPost({ body: 'Hello world!' });

			expect(post.body).toBe('Hello world!');
			expect(post.id).toBeDefined();
		});

		it('should create a reply', async () => {
			const reply = await createPost({
				body: 'This is a reply',
				reply_to_id: 1
			});

			expect(reply.body).toBe('This is a reply');
		});
	});

	describe('getPost', () => {
		it('should get a post by ID', async () => {
			const post = await getPost(1);

			expect(post.id).toBe(1);
			expect(post.body).toBeDefined();
		});

		it('should throw on non-existent post', async () => {
			await expect(getPost(999)).rejects.toThrow();
		});
	});

	describe('deletePost', () => {
		it('should delete a post', async () => {
			await expect(deletePost(1)).resolves.not.toThrow();
		});
	});

	describe('getHomeFeed', () => {
		it('should get home feed', async () => {
			const feed = await getHomeFeed(1, 20);

			expect(feed).toBeDefined();
		});

		it('should paginate correctly', async () => {
			const page1 = await getHomeFeed(1, 20);
			const page2 = await getHomeFeed(2, 20);

			expect(page1).toBeDefined();
			expect(page2).toBeDefined();
		});
	});

	describe('getExploreFeed', () => {
		it('should get explore feed', async () => {
			const feed = await getExploreFeed(1, 20);

			expect(feed).toBeDefined();
		});
	});

	describe('getUserPosts', () => {
		it('should get user posts by ID', async () => {
			const posts = await getUserPosts(1);

			expect(posts.items).toBeDefined();
			expect(posts.items.length).toBeGreaterThan(0);
		});
	});

	describe('searchPosts', () => {
		it('should search posts by query', async () => {
			const results = await searchPosts('test');

			expect(results).toBeDefined();
		});
	});

	describe('getPostReplies', () => {
		it('should get replies to a post', async () => {
			const replies = await getPostReplies(1);

			expect(replies.items).toBeDefined();
			expect(replies.items[0].is_reply).toBe(true);
		});
	});

	describe('likePost', () => {
		it('should like a post', async () => {
			const result = await likePost(1);

			expect(result.likes_count).toBe(11);
		});
	});

	describe('unlikePost', () => {
		it('should unlike a post', async () => {
			const result = await unlikePost(1);

			expect(result.likes_count).toBe(9);
		});
	});

	describe('isPostLiked', () => {
		it('should check if post is liked', async () => {
			const liked = await isPostLiked(1);

			expect(typeof liked).toBe('boolean');
		});
	});

	describe('repost', () => {
		it('should repost a post', async () => {
			const reposted = await repost(1);

			expect(reposted.is_repost).toBe(true);
			expect(reposted.repost_of_id).toBe(1);
		});

		it('should repost with quote', async () => {
			const reposted = await repost(1, 'My thoughts on this');

			expect(reposted.is_repost).toBe(true);
		});
	});

	describe('unrepost', () => {
		it('should unrepost a post', async () => {
			await expect(unrepost(1)).resolves.not.toThrow();
		});
	});
});

