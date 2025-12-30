<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { goto } from '$app/navigation';
	import PostCard from './PostCard.svelte';
	import { Spinner } from '$lib/components/ui';
	import type { Post } from '$lib/types';
	import { likePost, unlikePost, deletePost } from '$lib/api/posts';
	import { toast } from 'svelte-sonner';

	export let posts: Post[] = [];
	export let isLoading: boolean = false;
	export let hasMore: boolean = false;
	export let emptyMessage: string = 'No posts yet';
	export let compact: boolean = false;

	const dispatch = createEventDispatcher<{
		loadMore: void;
		reply: { postId: number };
	}>();

	async function handleLike(event: CustomEvent<{ postId: number; isLiked: boolean }>) {
		const { postId, isLiked } = event.detail;
		const postIndex = posts.findIndex((p) => p.id === postId);
		if (postIndex === -1) return;

		// Optimistic update
		posts[postIndex] = {
			...posts[postIndex],
			is_liked: isLiked,
			likes_count: posts[postIndex].likes_count + (isLiked ? 1 : -1)
		};
		posts = posts;

		try {
			if (isLiked) {
				await likePost(postId);
			} else {
				await unlikePost(postId);
			}
		} catch (error) {
			// Revert on error
			posts[postIndex] = {
				...posts[postIndex],
				is_liked: !isLiked,
				likes_count: posts[postIndex].likes_count + (isLiked ? -1 : 1)
			};
			posts = posts;
			toast.error('Failed to update like');
		}
	}

	async function handleDelete(event: CustomEvent<{ postId: number }>) {
		const { postId } = event.detail;

		if (!confirm('Are you sure you want to delete this post?')) return;

		const postIndex = posts.findIndex((p) => p.id === postId);
		const deletedPost = posts[postIndex];

		// Optimistic delete
		posts = posts.filter((p) => p.id !== postId);

		try {
			await deletePost(postId);
			toast.success('Post deleted');
		} catch (error) {
			// Revert on error
			posts.splice(postIndex, 0, deletedPost);
			posts = posts;
			toast.error('Failed to delete post');
		}
	}

	function handleReply(event: CustomEvent<{ postId: number }>) {
		dispatch('reply', event.detail);
	}

	function handleRepost(event: CustomEvent<{ postId: number }>) {
		// TODO: Implement repost modal
		toast.info('Repost coming soon!');
	}

	function handlePostClick(event: CustomEvent<{ postId: number }>) {
		// Post detail page not implemented yet
		// const { postId } = event.detail;
		// const post = posts.find((p) => p.id === postId);
		// if (post?.author) {
		// 	goto(`/profile/${post.author.username}/post/${postId}`);
		// }
	}

	function handleLoadMore() {
		dispatch('loadMore');
	}
</script>

<div class="divide-y divide-border">
	{#each posts as post (post.id)}
		<PostCard
			{post}
			{compact}
			on:like={handleLike}
			on:reply={handleReply}
			on:repost={handleRepost}
			on:delete={handleDelete}
			on:click={handlePostClick}
		/>
	{/each}

	{#if isLoading}
		<div class="flex justify-center py-8">
			<Spinner size="md" />
		</div>
	{:else if posts.length === 0}
		<div class="flex flex-col items-center justify-center py-12 text-text-secondary">
			<p class="text-lg">{emptyMessage}</p>
		</div>
	{:else if hasMore}
		<button
			type="button"
			class="w-full py-4 text-primary hover:bg-surface-hover transition-colors"
			on:click={handleLoadMore}
		>
			Show more
		</button>
	{/if}
</div>

