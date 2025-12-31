<script lang="ts">
	import { onMount } from 'svelte';
	import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
	import { fly, fade } from 'svelte/transition';
	import { RefreshCw } from 'lucide-svelte';
	import { PostComposer, PostCard } from '$lib/components/post';
	import { Spinner } from '$lib/components/ui';
	import { getHomeFeed, likePost, unlikePost, deletePost } from '$lib/api/posts';
	import { toast } from 'svelte-sonner';
	import type { PostsResponse } from '$lib/types';

	const queryClient = useQueryClient();

	// Infinite query for feed
	const feedQuery = createInfiniteQuery({
		queryKey: ['feed', 'home'],
		queryFn: async ({ pageParam = 1 }) => {
			return getHomeFeed(pageParam, 20);
		},
		getNextPageParam: (lastPage: PostsResponse) => {
			return lastPage.has_next ? lastPage.page + 1 : undefined;
		},
		initialPageParam: 1
	});

	// Derived state
	$: posts = $feedQuery.data?.pages.flatMap((page) => page.items) ?? [];
	$: hasMore = $feedQuery.hasNextPage ?? false;
	$: isLoading = $feedQuery.isLoading;
	$: isFetchingNextPage = $feedQuery.isFetchingNextPage;
	$: isRefetching = $feedQuery.isRefetching && !$feedQuery.isFetchingNextPage;

	// Pull to refresh state
	let pullDistance = 0;
	let isPulling = false;
	let startY = 0;
	const PULL_THRESHOLD = 80;

	// Infinite scroll observer
	let loadMoreTrigger: HTMLDivElement;
	let observer: IntersectionObserver;

	onMount(() => {
		// Set up IntersectionObserver for infinite scroll
		observer = new IntersectionObserver(
			(entries) => {
				const entry = entries[0];
				if (entry.isIntersecting && hasMore && !isFetchingNextPage) {
					$feedQuery.fetchNextPage();
				}
			},
			{
				rootMargin: '200px' // Load more before reaching the end
			}
		);

		if (loadMoreTrigger) {
			observer.observe(loadMoreTrigger);
		}

		return () => {
			observer?.disconnect();
		};
	});

	// Watch for loadMoreTrigger changes
	$: if (loadMoreTrigger && observer) {
		observer.observe(loadMoreTrigger);
	}

	// Pull to refresh handlers
	function handleTouchStart(event: TouchEvent) {
		if (window.scrollY === 0) {
			startY = event.touches[0].clientY;
			isPulling = true;
		}
	}

	function handleTouchMove(event: TouchEvent) {
		if (!isPulling || window.scrollY > 0) {
			pullDistance = 0;
			return;
		}

		const currentY = event.touches[0].clientY;
		pullDistance = Math.max(0, Math.min((currentY - startY) * 0.5, PULL_THRESHOLD * 1.5));
	}

	function handleTouchEnd() {
		if (pullDistance >= PULL_THRESHOLD) {
			handleRefresh();
		}
		pullDistance = 0;
		isPulling = false;
	}

	async function handleRefresh() {
		await $feedQuery.refetch();
	}

	function handlePostCreated() {
		$feedQuery.refetch();
	}

	async function handleLike(event: CustomEvent<{ postId: number; isLiked: boolean }>) {
		const { postId, isLiked } = event.detail;

		try {
			if (isLiked) {
				await likePost(postId);
			} else {
				await unlikePost(postId);
			}
		} catch (error) {
			toast.error('Failed to update like');
			// Refetch to restore correct state
			$feedQuery.refetch();
		}
	}

	async function handleDelete(event: CustomEvent<{ postId: number }>) {
		const { postId } = event.detail;

		try {
			await deletePost(postId);
			toast.success('Post deleted');
			$feedQuery.refetch();
		} catch (error) {
			toast.error('Failed to delete post');
		}
	}

	function handleReply(event: CustomEvent<{ postId: number }>) {
		// TODO: Open reply modal
		toast.info('Reply feature coming soon');
	}

	function handleRepost(event: CustomEvent<{ postId: number }>) {
		// TODO: Handle repost
		toast.info('Repost feature coming soon');
	}
</script>

<svelte:head>
	<title>Home | SWESphere</title>
</svelte:head>

<div
	class="relative"
	on:touchstart={handleTouchStart}
	on:touchmove={handleTouchMove}
	on:touchend={handleTouchEnd}
>
	<!-- Pull to refresh indicator -->
	{#if pullDistance > 0}
		<div
			class="absolute top-0 left-0 right-0 flex justify-center items-center pointer-events-none z-20"
			style="height: {pullDistance}px"
			in:fade={{ duration: 100 }}
		>
			<div
				class="p-2 rounded-full bg-surface shadow-lg"
				style="transform: rotate({pullDistance * 3}deg)"
			>
				<RefreshCw
					class="w-5 h-5 text-primary {pullDistance >= PULL_THRESHOLD ? 'animate-spin' : ''}"
				/>
			</div>
		</div>
	{/if}

	<!-- Header -->
	<header
		class="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b border-border"
		style="transform: translateY({pullDistance}px)"
	>
		<div class="flex items-center justify-between px-4 py-3">
			<h1 class="text-xl font-bold">Home</h1>
			{#if isRefetching}
				<Spinner size="sm" />
			{/if}
		</div>
	</header>

	<!-- Composer -->
	<div class="border-b border-border hidden md:block" style="transform: translateY({pullDistance}px)">
		<PostComposer on:submit={handlePostCreated} />
	</div>

	<!-- Feed Content -->
	<div style="transform: translateY({pullDistance}px)">
		{#if isLoading}
			<div class="flex justify-center py-16">
				<Spinner size="lg" />
			</div>
		{:else if posts.length === 0}
			<!-- Empty state -->
			<div class="flex flex-col items-center justify-center py-16 px-4 text-center">
				<div class="w-20 h-20 rounded-full bg-surface flex items-center justify-center mb-4">
					<svg class="w-10 h-10 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
					</svg>
				</div>
				<h2 class="text-xl font-bold mb-2">Your feed is empty</h2>
				<p class="text-text-secondary max-w-sm mb-6">
					When you follow people, their posts will show up here. Start exploring to find interesting accounts!
				</p>
				<a
					href="/explore"
					class="px-6 py-3 bg-primary text-white font-bold rounded-full hover:bg-primary-hover transition-colors"
				>
					Explore
				</a>
			</div>
		{:else}
			<!-- Posts list -->
			<div class="divide-y divide-border">
				{#each posts as post (post.id)}
					<PostCard
						{post}
						on:like={handleLike}
						on:reply={handleReply}
						on:repost={handleRepost}
						on:delete={handleDelete}
					/>
				{/each}
			</div>

			<!-- Load more trigger -->
			<div bind:this={loadMoreTrigger} class="py-8 flex justify-center">
				{#if isFetchingNextPage}
					<Spinner size="md" />
				{:else if !hasMore}
					<p class="text-text-secondary text-sm">You've reached the end</p>
				{/if}
			</div>
		{/if}
	</div>
</div>

<!-- Mobile floating compose button spacer -->
<div class="h-20 md:hidden"></div>
