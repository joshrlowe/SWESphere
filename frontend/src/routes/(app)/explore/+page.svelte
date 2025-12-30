<script lang="ts">
	import { createInfiniteQuery } from '@tanstack/svelte-query';
	import { PostList } from '$lib/components/post';
	import { Spinner } from '$lib/components/ui';
	import { getExploreFeed } from '$lib/api/posts';
	import type { PostsResponse } from '$lib/types';

	const exploreQuery = createInfiniteQuery({
		queryKey: ['feed', 'explore'],
		queryFn: async ({ pageParam = 1 }) => {
			return getExploreFeed(pageParam, 20);
		},
		getNextPageParam: (lastPage: PostsResponse) => {
			return lastPage.has_next ? lastPage.page + 1 : undefined;
		},
		initialPageParam: 1
	});

	$: posts = $exploreQuery.data?.pages.flatMap((page) => page.items) ?? [];
	$: hasMore = $exploreQuery.hasNextPage ?? false;
	$: isLoading = $exploreQuery.isLoading;
	$: isFetchingNextPage = $exploreQuery.isFetchingNextPage;

	function handleLoadMore() {
		if ($exploreQuery.hasNextPage && !$exploreQuery.isFetchingNextPage) {
			$exploreQuery.fetchNextPage();
		}
	}
</script>

<svelte:head>
	<title>Explore | SWESphere</title>
</svelte:head>

<div>
	<!-- Header -->
	<header class="sticky top-0 z-10 bg-background/80 backdrop-blur-sm border-b border-border">
		<h1 class="px-4 py-3 text-xl font-bold">Explore</h1>

		<!-- Tabs -->
		<div class="flex border-b border-border">
			<button class="flex-1 py-4 text-center font-bold relative">
				For you
				<span class="absolute bottom-0 left-1/2 -translate-x-1/2 w-14 h-1 bg-primary rounded-full"></span>
			</button>
			<button class="flex-1 py-4 text-center text-text-secondary hover:bg-surface-hover transition-colors">
				Trending
			</button>
		</div>
	</header>

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
			emptyMessage="Nothing to explore yet. Check back later!"
			on:loadMore={handleLoadMore}
		/>
	{/if}
</div>

