<script lang="ts">
	import { page } from '$app/stores';
	import { createQuery, createInfiniteQuery } from '@tanstack/svelte-query';
	import { ProfileHeader } from '$lib/components/user';
	import { PostList } from '$lib/components/post';
	import { Spinner } from '$lib/components/ui';
	import { getUserByUsername } from '$lib/api/users';
	import { getUserPostsByUsername } from '$lib/api/posts';
	import type { PostsResponse } from '$lib/types';

	$: username = $page.params.username ?? '';

	$: profileQuery = createQuery({
		queryKey: ['user', username],
		queryFn: () => getUserByUsername(username),
		enabled: username.length > 0
	});

	$: postsQuery = createInfiniteQuery({
		queryKey: ['posts', 'user', username],
		queryFn: async ({ pageParam = 1 }) => {
			return getUserPostsByUsername(username, pageParam, 20);
		},
		getNextPageParam: (lastPage: PostsResponse) => {
			return lastPage.has_next ? lastPage.page + 1 : undefined;
		},
		enabled: username.length > 0,
		initialPageParam: 1
	});

	$: user = $profileQuery.data;
	$: posts = $postsQuery.data?.pages.flatMap((page) => page.items) ?? [];
	$: hasMore = $postsQuery.hasNextPage ?? false;
	$: isLoadingProfile = $profileQuery.isLoading;
	$: isLoadingPosts = $postsQuery.isLoading;
	$: isFetchingNextPage = $postsQuery.isFetchingNextPage;

	function handleLoadMore() {
		if ($postsQuery.hasNextPage && !$postsQuery.isFetchingNextPage) {
			$postsQuery.fetchNextPage();
		}
	}

	function handleEditProfile() {
		// TODO: Open edit profile modal
	}

	function handleFollow(event: CustomEvent<{ userId: number; isFollowing: boolean }>) {
		$profileQuery.refetch();
	}
</script>

<svelte:head>
	<title>{user ? `${user.display_name || user.username} (@${user.username})` : 'Profile'} | SWESphere</title>
</svelte:head>

<div>
	{#if isLoadingProfile}
		<div class="flex justify-center py-12">
			<Spinner size="lg" />
		</div>
	{:else if user}
		<ProfileHeader
			{user}
			on:editProfile={handleEditProfile}
			on:follow={handleFollow}
		/>

		<!-- Tabs -->
		<div class="flex border-b border-border">
			<button class="flex-1 py-4 text-center font-bold relative">
				Posts
				<span class="absolute bottom-0 left-1/2 -translate-x-1/2 w-12 h-1 bg-primary rounded-full"></span>
			</button>
			<button class="flex-1 py-4 text-center text-text-secondary hover:bg-surface-hover transition-colors">
				Replies
			</button>
			<button class="flex-1 py-4 text-center text-text-secondary hover:bg-surface-hover transition-colors">
				Media
			</button>
			<button class="flex-1 py-4 text-center text-text-secondary hover:bg-surface-hover transition-colors">
				Likes
			</button>
		</div>

		<!-- Posts -->
		{#if isLoadingPosts}
			<div class="flex justify-center py-12">
				<Spinner size="lg" />
			</div>
		{:else}
			<PostList
				{posts}
				{hasMore}
				isLoading={isFetchingNextPage}
				emptyMessage="No posts yet"
				on:loadMore={handleLoadMore}
			/>
		{/if}
	{:else}
		<div class="flex flex-col items-center justify-center py-16 px-4 text-center">
			<h2 class="text-xl font-bold mb-2">User not found</h2>
			<p class="text-text-secondary">The user @{username} doesn't exist.</p>
		</div>
	{/if}
</div>

