<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { createQuery, createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
	import { fly, fade } from 'svelte/transition';
	import { formatDistanceToNow, format } from 'date-fns';
	import {
		ArrowLeft,
		Calendar,
		MapPin,
		Link as LinkIcon,
		BadgeCheck,
		MoreHorizontal
	} from 'lucide-svelte';
	import { clsx } from 'clsx';
	import { Avatar, Button, Modal, Spinner } from '$lib/components/ui';
	import { PostCard } from '$lib/components/post';
	import { FollowButton } from '$lib/components/user';
	import { getUserByUsername, updateProfile } from '$lib/api/users';
	import { getUserPostsByUsername, likePost, unlikePost, deletePost } from '$lib/api/posts';
	import { currentUser } from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import type { PostsResponse, User } from '$lib/types';

	const queryClient = useQueryClient();

	$: username = $page.params.username ?? '';

	// Profile query
	$: profileQuery = createQuery({
		queryKey: ['user', username],
		queryFn: () => getUserByUsername(username),
		enabled: username.length > 0
	});

	// Posts query with infinite scroll
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

	// Derived state
	$: user = $profileQuery.data;
	$: posts = $postsQuery.data?.pages.flatMap((page) => page.items) ?? [];
	$: hasMore = $postsQuery.hasNextPage ?? false;
	$: isLoadingProfile = $profileQuery.isLoading;
	$: isLoadingPosts = $postsQuery.isLoading;
	$: isFetchingNextPage = $postsQuery.isFetchingNextPage;
	$: isOwnProfile = $currentUser?.username === username;

	// Tabs
	type Tab = 'posts' | 'replies' | 'media' | 'likes';
	let activeTab: Tab = 'posts';

	// Edit profile modal
	let showEditModal = false;
	let editForm = {
		display_name: '',
		bio: '',
		location: '',
		website: ''
	};
	let isSaving = false;

	// Infinite scroll observer
	let loadMoreTrigger: HTMLDivElement;
	let observer: IntersectionObserver;

	onMount(() => {
		observer = new IntersectionObserver(
			(entries) => {
				if (entries[0].isIntersecting && hasMore && !isFetchingNextPage) {
					$postsQuery.fetchNextPage();
				}
			},
			{ rootMargin: '200px' }
		);

		return () => observer?.disconnect();
	});

	$: if (loadMoreTrigger && observer) {
		observer.observe(loadMoreTrigger);
	}

	// Initialize edit form when opening modal
	function openEditModal() {
		if (user) {
			editForm = {
				display_name: user.display_name || '',
				bio: user.bio || '',
				location: user.location || '',
				website: user.website || ''
			};
		}
		showEditModal = true;
	}

	async function handleSaveProfile() {
		isSaving = true;
		try {
			await updateProfile(editForm);
			toast.success('Profile updated');
			$profileQuery.refetch();
			showEditModal = false;
		} catch (error) {
			toast.error('Failed to update profile');
		} finally {
			isSaving = false;
		}
	}

	function handleFollow() {
		$profileQuery.refetch();
	}

	async function handleLike(event: CustomEvent<{ postId: number; isLiked: boolean }>) {
		const { postId, isLiked } = event.detail;
		try {
			if (isLiked) {
				await likePost(postId);
			} else {
				await unlikePost(postId);
			}
		} catch {
			toast.error('Failed to update like');
			$postsQuery.refetch();
		}
	}

	async function handleDelete(event: CustomEvent<{ postId: number }>) {
		try {
			await deletePost(event.detail.postId);
			toast.success('Post deleted');
			$postsQuery.refetch();
		} catch {
			toast.error('Failed to delete post');
		}
	}

	function goBack() {
		history.back();
	}

	$: joinDate = user?.created_at
		? format(new Date(user.created_at), 'MMMM yyyy')
		: '';
</script>

<svelte:head>
	<title>
		{user ? `${user.display_name || user.username} (@${user.username})` : 'Profile'} | SWESphere
	</title>
</svelte:head>

<div>
	<!-- Header -->
	<header class="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b border-border">
		<div class="flex items-center gap-4 px-4 py-2">
			<button
				type="button"
				class="p-2 -ml-2 rounded-full hover:bg-surface-hover transition-colors"
				on:click={goBack}
				aria-label="Go back"
			>
				<ArrowLeft class="w-5 h-5" />
			</button>
			{#if user}
				<div>
					<h1 class="font-bold text-lg flex items-center gap-1">
						{user.display_name || user.username}
						{#if user.is_verified}
							<BadgeCheck class="w-5 h-5 text-primary" />
						{/if}
					</h1>
					<p class="text-sm text-text-secondary">{user.posts_count} posts</p>
				</div>
			{/if}
		</div>
	</header>

	{#if isLoadingProfile}
		<div class="flex justify-center py-16">
			<Spinner size="lg" />
		</div>
	{:else if user}
		<!-- Banner -->
		<div class="h-32 sm:h-48 bg-gradient-to-br from-primary/30 via-primary/10 to-transparent relative">
			{#if user.banner_url}
				<img src={user.banner_url} alt="Banner" class="w-full h-full object-cover" />
			{/if}
		</div>

		<!-- Profile Info -->
		<div class="px-4 pb-4">
			<!-- Avatar and Actions Row -->
			<div class="flex justify-between items-start -mt-16 sm:-mt-20 mb-4">
				<div class="ring-4 ring-background rounded-full">
					<Avatar user={user} size="2xl" />
				</div>

				<div class="flex items-center gap-2 mt-20 sm:mt-24">
					{#if isOwnProfile}
						<Button variant="secondary" on:click={openEditModal}>
							Edit profile
						</Button>
					{:else}
						<button
							type="button"
							class="p-2 rounded-full border border-border hover:bg-surface-hover transition-colors"
							aria-label="More options"
						>
							<MoreHorizontal class="w-5 h-5" />
						</button>
						<FollowButton user={user} on:follow={handleFollow} />
					{/if}
				</div>
			</div>

			<!-- Name and Username -->
			<div class="mb-3">
				<h2 class="text-xl font-bold flex items-center gap-1">
					{user.display_name || user.username}
					{#if user.is_verified}
						<BadgeCheck class="w-5 h-5 text-primary" />
					{/if}
				</h2>
				<p class="text-text-secondary">@{user.username}</p>
			</div>

			<!-- Bio -->
			{#if user.bio}
				<p class="text-text mb-3 whitespace-pre-wrap">{user.bio}</p>
			{/if}

			<!-- Meta info -->
			<div class="flex flex-wrap gap-x-4 gap-y-1 text-text-secondary text-sm mb-4">
				{#if user.location}
					<span class="flex items-center gap-1">
						<MapPin class="w-4 h-4" />
						{user.location}
					</span>
				{/if}
				{#if user.website}
					<a
						href={user.website.startsWith('http') ? user.website : `https://${user.website}`}
						target="_blank"
						rel="noopener noreferrer"
						class="flex items-center gap-1 text-primary hover:underline"
					>
						<LinkIcon class="w-4 h-4" />
						{user.website.replace(/^https?:\/\//, '')}
					</a>
				{/if}
				{#if joinDate}
					<span class="flex items-center gap-1">
						<Calendar class="w-4 h-4" />
						Joined {joinDate}
					</span>
				{/if}
			</div>

			<!-- Stats -->
			<div class="flex gap-4 text-sm">
				<a href={`/profile/${username}/following`} class="hover:underline">
					<span class="font-bold text-text">{user.following_count}</span>
					<span class="text-text-secondary">Following</span>
				</a>
				<a href={`/profile/${username}/followers`} class="hover:underline">
					<span class="font-bold text-text">{user.followers_count}</span>
					<span class="text-text-secondary">Followers</span>
				</a>
			</div>
		</div>

		<!-- Tabs -->
		<div class="flex border-b border-border sticky top-14 bg-background z-10">
			{#each [
				{ id: 'posts', label: 'Posts' },
				{ id: 'replies', label: 'Replies' },
				{ id: 'media', label: 'Media' },
				{ id: 'likes', label: 'Likes' }
			] as tab}
				<button
					type="button"
					class={clsx(
						'flex-1 py-4 text-center font-medium transition-colors relative',
						activeTab === tab.id
							? 'text-text'
							: 'text-text-secondary hover:bg-surface-hover hover:text-text'
					)}
					on:click={() => (activeTab = tab.id)}
				>
					{tab.label}
					{#if activeTab === tab.id}
						<span
							class="absolute bottom-0 left-1/2 -translate-x-1/2 w-14 h-1 bg-primary rounded-full"
							in:fade={{ duration: 150 }}
						></span>
					{/if}
				</button>
			{/each}
		</div>

		<!-- Posts -->
		{#if activeTab === 'posts'}
			{#if isLoadingPosts}
				<div class="flex justify-center py-12">
					<Spinner size="lg" />
				</div>
			{:else if posts.length === 0}
				<div class="flex flex-col items-center justify-center py-16 px-4 text-center">
					<h3 class="text-xl font-bold mb-2">
						{isOwnProfile ? "You haven't posted yet" : `@${username} hasn't posted yet`}
					</h3>
					<p class="text-text-secondary">
						{isOwnProfile
							? 'When you post, it will show up here.'
							: "When they do, their posts will show up here."}
					</p>
				</div>
			{:else}
				<div class="divide-y divide-border">
					{#each posts as post (post.id)}
						<PostCard
							{post}
							on:like={handleLike}
							on:delete={handleDelete}
						/>
					{/each}
				</div>

				<!-- Load more trigger -->
				<div bind:this={loadMoreTrigger} class="py-8 flex justify-center">
					{#if isFetchingNextPage}
						<Spinner size="md" />
					{:else if !hasMore && posts.length > 0}
						<p class="text-text-secondary text-sm">No more posts</p>
					{/if}
				</div>
			{/if}
		{:else}
			<div class="flex flex-col items-center justify-center py-16 px-4 text-center">
				<p class="text-text-secondary">This tab is coming soon</p>
			</div>
		{/if}
	{:else}
		<!-- User not found -->
		<div class="flex flex-col items-center justify-center py-16 px-4 text-center">
			<div class="w-24 h-24 rounded-full bg-surface flex items-center justify-center mb-4">
				<span class="text-4xl">🔍</span>
			</div>
			<h2 class="text-2xl font-bold mb-2">This account doesn't exist</h2>
			<p class="text-text-secondary mb-6">Try searching for another.</p>
			<Button variant="primary" on:click={() => goto('/explore')}>
				Explore
			</Button>
		</div>
	{/if}
</div>

<!-- Edit Profile Modal -->
<Modal bind:open={showEditModal} title="Edit profile">
	<form on:submit|preventDefault={handleSaveProfile} class="space-y-4">
		<div>
			<label for="display_name" class="block text-sm font-medium text-text-secondary mb-1.5">
				Name
			</label>
			<input
				id="display_name"
				type="text"
				bind:value={editForm.display_name}
				maxlength="50"
				class="w-full px-4 py-3 bg-transparent border border-border rounded-lg text-text focus:border-primary focus:ring-1 focus:ring-primary transition-colors"
			/>
		</div>

		<div>
			<label for="bio" class="block text-sm font-medium text-text-secondary mb-1.5">
				Bio
			</label>
			<textarea
				id="bio"
				bind:value={editForm.bio}
				maxlength="160"
				rows="3"
				class="w-full px-4 py-3 bg-transparent border border-border rounded-lg text-text focus:border-primary focus:ring-1 focus:ring-primary transition-colors resize-none"
			></textarea>
			<p class="text-xs text-text-muted text-right mt-1">{editForm.bio.length}/160</p>
		</div>

		<div>
			<label for="location" class="block text-sm font-medium text-text-secondary mb-1.5">
				Location
			</label>
			<input
				id="location"
				type="text"
				bind:value={editForm.location}
				maxlength="30"
				class="w-full px-4 py-3 bg-transparent border border-border rounded-lg text-text focus:border-primary focus:ring-1 focus:ring-primary transition-colors"
			/>
		</div>

		<div>
			<label for="website" class="block text-sm font-medium text-text-secondary mb-1.5">
				Website
			</label>
			<input
				id="website"
				type="url"
				bind:value={editForm.website}
				placeholder="https://"
				class="w-full px-4 py-3 bg-transparent border border-border rounded-lg text-text focus:border-primary focus:ring-1 focus:ring-primary transition-colors"
			/>
		</div>

		<div class="flex gap-3 pt-4">
			<Button variant="secondary" fullWidth on:click={() => (showEditModal = false)}>
				Cancel
			</Button>
			<Button type="submit" variant="primary" fullWidth loading={isSaving}>
				Save
			</Button>
		</div>
	</form>
</Modal>

<!-- Mobile bottom nav spacer -->
<div class="h-20 md:hidden"></div>
