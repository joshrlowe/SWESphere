<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { formatDistanceToNow } from 'date-fns';
	import { BadgeCheck, Calendar, MapPin, Link as LinkIcon, ArrowLeft } from 'lucide-svelte';
	import { goto } from '$app/navigation';
	import { Avatar, Button } from '$lib/components/ui';
	import FollowButton from './FollowButton.svelte';
	import { formatFollowerCount, type UserProfile } from '$lib/types';
	import { currentUser } from '$lib/stores';

	export let user: UserProfile;
	export let coverUrl: string | null = null;

	const dispatch = createEventDispatcher<{
		editProfile: void;
		follow: { userId: number; isFollowing: boolean };
	}>();

	$: isCurrentUser = $currentUser?.id === user.id;
	$: joinedDate = user.created_at
		? formatDistanceToNow(new Date(user.created_at), { addSuffix: true })
		: null;
	$: displayName = user.display_name || user.username;

	function handleBack() {
		history.back();
	}

	function handleEditProfile() {
		dispatch('editProfile');
	}

	function handleFollow(event: CustomEvent<{ userId: number; isFollowing: boolean }>) {
		dispatch('follow', event.detail);
	}
</script>

<div class="border-b border-border">
	<!-- Header -->
	<div class="sticky top-0 z-10 flex items-center gap-6 px-4 py-2 bg-background/80 backdrop-blur-sm">
		<button
			type="button"
			class="p-2 rounded-full hover:bg-surface-hover transition-colors"
			on:click={handleBack}
			aria-label="Go back"
		>
			<ArrowLeft class="w-5 h-5" />
		</button>
		<div>
			<h1 class="text-xl font-bold flex items-center gap-1">
				{displayName}
				{#if user.is_verified}
					<BadgeCheck class="w-5 h-5 text-primary" />
				{/if}
			</h1>
			<p class="text-sm text-text-secondary">{formatFollowerCount(user.posts_count)} posts</p>
		</div>
	</div>

	<!-- Cover Image -->
	<div class="h-32 sm:h-48 bg-surface">
		{#if coverUrl}
			<img src={coverUrl} alt="Cover" class="w-full h-full object-cover" />
		{/if}
	</div>

	<!-- Profile Info -->
	<div class="px-4 pb-4">
		<!-- Avatar & Actions -->
		<div class="flex justify-between items-start -mt-16 sm:-mt-20 mb-4">
			<Avatar {user} size="2xl" class="border-4 border-background" />

			<div class="mt-20 sm:mt-24">
				{#if isCurrentUser}
					<Button variant="secondary" on:click={handleEditProfile}>
						Edit profile
					</Button>
				{:else}
					<FollowButton
						userId={user.id}
						isFollowing={user.is_following ?? false}
						on:follow={handleFollow}
					/>
				{/if}
			</div>
		</div>

		<!-- Name & Username -->
		<div class="mb-3">
			<h2 class="text-xl font-bold flex items-center gap-1">
				{displayName}
				{#if user.is_verified}
					<BadgeCheck class="w-5 h-5 text-primary" />
				{/if}
			</h2>
			<p class="text-text-secondary">@{user.username}</p>
		</div>

		<!-- Bio -->
		{#if user.bio}
			<p class="mb-3 whitespace-pre-wrap">{user.bio}</p>
		{/if}

		<!-- Meta -->
		<div class="flex flex-wrap gap-x-4 gap-y-1 text-sm text-text-secondary mb-3">
			{#if user.location}
				<span class="flex items-center gap-1">
					<MapPin class="w-4 h-4" />
					{user.location}
				</span>
			{/if}
			{#if user.website}
				<a
					href={user.website}
					target="_blank"
					rel="noopener noreferrer"
					class="flex items-center gap-1 text-primary hover:underline"
				>
					<LinkIcon class="w-4 h-4" />
					{user.website.replace(/^https?:\/\//, '')}
				</a>
			{/if}
			{#if joinedDate}
				<span class="flex items-center gap-1">
					<Calendar class="w-4 h-4" />
					Joined {joinedDate}
				</span>
			{/if}
		</div>

		<!-- Stats -->
		<div class="flex gap-4 text-sm">
			<a
				href={`/${user.username}/following`}
				class="hover:underline"
			>
				<span class="font-bold text-text">{formatFollowerCount(user.following_count)}</span>
				<span class="text-text-secondary">Following</span>
			</a>
			<a
				href={`/${user.username}/followers`}
				class="hover:underline"
			>
				<span class="font-bold text-text">{formatFollowerCount(user.followers_count)}</span>
				<span class="text-text-secondary">Followers</span>
			</a>
		</div>
	</div>
</div>

