<script lang="ts">
	import { createQuery, createInfiniteQuery } from '@tanstack/svelte-query';
	import { PostComposer, PostList } from '$lib/components/post';
	import { Spinner } from '$lib/components/ui';
	import { getHomeFeed } from '$lib/api/posts';
	import type { Post, PostsResponse } from '$lib/types';

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

	$: posts = $feedQuery.data?.pages.flatMap((page) => page.items) ?? [];
	$: hasMore = $feedQuery.hasNextPage ?? false;
	$: isLoading = $feedQuery.isLoading;
	$: isFetchingNextPage = $feedQuery.isFetchingNextPage;

	function handleLoadMore() {
		if ($feedQuery.hasNextPage && !$feedQuery.isFetchingNextPage) {
			$feedQuery.fetchNextPage();
		}
	}

	function handlePostCreated() {
		$feedQuery.refetch();
	}
</script>

<svelte:head>
	<title>Home | SWESphere</title>
</svelte:head>

<div>
	<!-- Header -->
	<header class="sticky top-0 z-10 bg-background/80 backdrop-blur-sm border-b border-border">
		<h1 class="px-4 py-3 text-xl font-bold">Home</h1>
	</header>

	<!-- Composer -->
	<div class="border-b border-border">
		<PostComposer on:submit={handlePostCreated} />
	</div>

	<!-- Feed -->
	{#if isLoading}
		<div class="flex justify-center py-12">
			<Spinner size="lg" />
		</div>
	{:else}
		<PostList
			{posts}
			{hasMore}
			isLoading={isFetchingNextPage}
			emptyMessage="Your feed is empty. Follow some users to see their posts!"
			on:loadMore={handleLoadMore}
		/>
	{/if}
</div>

