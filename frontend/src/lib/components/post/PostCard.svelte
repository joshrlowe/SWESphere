<script lang="ts">
	/**
	 * PostCard - Displays a single post with author info, content, and action buttons.
	 *
	 * Features:
	 * - Optimistic like updates with animation
	 * - Dropdown menu for post actions (delete for owner)
	 * - Responsive layout with compact mode
	 * - Keyboard accessible
	 */
	import { createEventDispatcher } from 'svelte';
	import { fly, scale, fade } from 'svelte/transition';
	import { formatDistanceToNow } from 'date-fns';
	import {
		Heart,
		MessageCircle,
		Repeat2,
		Share,
		MoreHorizontal,
		Trash2,
		BadgeCheck
	} from 'lucide-svelte';
	import { clsx } from 'clsx';
	import { Avatar } from '$lib/components/ui';
	import { formatEngagementCount, type Post } from '$lib/types';
	import { currentUser } from '$lib/stores';

	// ============================================================================
	// Constants
	// ============================================================================

	const LIKE_ANIMATION_DURATION_MS = 400;
	const HEART_BURST_PARTICLE_COUNT = 6;
	const PARTICLE_ROTATION_DEGREES = 60;

	// ============================================================================
	// Props
	// ============================================================================

	export let post: Post;
	export let showActions: boolean = true;
	export let compact: boolean = false;

	// ============================================================================
	// Events
	// ============================================================================

	const dispatch = createEventDispatcher<{
		like: { postId: number; isLiked: boolean };
		reply: { postId: number };
		repost: { postId: number };
		delete: { postId: number };
		click: { postId: number };
	}>();

	// ============================================================================
	// State
	// ============================================================================

	let isMenuOpen = false;
	let isLikeAnimating = false;

	// Optimistic state for immediate UI feedback
	let optimisticLiked = post.is_liked;
	let optimisticLikesCount = post.likes_count;

	// ============================================================================
	// Derived State
	// ============================================================================

	// Sync optimistic state when post prop changes
	$: {
		optimisticLiked = post.is_liked;
		optimisticLikesCount = post.likes_count;
	}

	$: author = post.author;
	$: isOwner = $currentUser?.id === post.user_id;
	$: profileUrl = author ? `/profile/${author.username}` : '#';
	$: displayName = author?.display_name || author?.username || 'Unknown';
	$: formattedTime = formatDistanceToNow(new Date(post.created_at), { addSuffix: true });

	// Pre-format engagement counts
	$: formattedReplies = formatEngagementCount(post.comments_count);
	$: formattedReposts = formatEngagementCount(post.reposts_count);
	$: formattedLikes = formatEngagementCount(optimisticLikesCount);

	// Generate heart burst particle rotations
	$: particleRotations = Array.from(
		{ length: HEART_BURST_PARTICLE_COUNT },
		(_, i) => i * PARTICLE_ROTATION_DEGREES
	);

	// ============================================================================
	// Event Handlers
	// ============================================================================

	function handlePostClick() {
		dispatch('click', { postId: post.id });
	}

	function handleKeyDown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			handlePostClick();
		}
	}

	function handleLike() {
		const wasLiked = optimisticLiked;

		// Optimistic update
		optimisticLiked = !wasLiked;
		optimisticLikesCount += wasLiked ? -1 : 1;

		// Trigger animation only when liking (not unliking)
		if (!wasLiked) {
			triggerLikeAnimation();
		}

		dispatch('like', { postId: post.id, isLiked: !wasLiked });
	}

	function triggerLikeAnimation() {
		isLikeAnimating = true;
		setTimeout(() => {
			isLikeAnimating = false;
		}, LIKE_ANIMATION_DURATION_MS);
	}

	function handleReply() {
		dispatch('reply', { postId: post.id });
	}

	function handleRepost() {
		dispatch('repost', { postId: post.id });
	}

	function handleDelete() {
		dispatch('delete', { postId: post.id });
		closeMenu();
	}

	function toggleMenu() {
		isMenuOpen = !isMenuOpen;
	}

	function closeMenu() {
		isMenuOpen = false;
	}
</script>

<!-- Close menu when clicking outside -->
<svelte:window on:click={closeMenu} />

<article
	class={clsx(
		'flex gap-3 border-b border-border transition-colors duration-200 cursor-pointer',
		'hover:bg-surface-hover/50',
		compact ? 'px-4 py-3' : 'p-4'
	)}
	on:click={handlePostClick}
	on:keydown={handleKeyDown}
	role="article"
	tabindex="0"
	in:fly={{ y: 20, duration: 300 }}
>
	<!-- ======================================================================== -->
	<!-- Avatar Section                                                          -->
	<!-- ======================================================================== -->
	<a
		href={profileUrl}
		class="flex-shrink-0 transition-transform duration-200 hover:scale-105"
		on:click|stopPropagation
	>
		<Avatar user={author} size={compact ? 'sm' : 'md'} />
	</a>

	<!-- ======================================================================== -->
	<!-- Content Section                                                         -->
	<!-- ======================================================================== -->
	<div class="flex-1 min-w-0">
		<!-- Header: Author info + Menu -->
		<header class="flex items-start justify-between gap-2">
			<!-- Author Info -->
			<div class="flex items-center gap-1 min-w-0 flex-wrap">
				{#if author}
					<a
						href={profileUrl}
						class="font-bold text-text hover:underline truncate"
						on:click|stopPropagation
					>
						{displayName}
					</a>

					{#if author.is_verified}
						<BadgeCheck class="w-4 h-4 text-primary flex-shrink-0" aria-label="Verified" />
					{/if}

					<a
						href={profileUrl}
						class="text-text-secondary truncate hover:underline"
						on:click|stopPropagation
					>
						@{author.username}
					</a>
				{/if}

				<span class="text-text-secondary" aria-hidden="true">·</span>
				<time class="text-text-secondary text-sm whitespace-nowrap" datetime={post.created_at}>
					{formattedTime}
				</time>
			</div>

			<!-- Dropdown Menu -->
			<div class="relative">
				<button
					type="button"
					class="p-2 -m-2 rounded-full hover:bg-primary/10 hover:text-primary transition-colors duration-200"
					on:click|stopPropagation={toggleMenu}
					aria-label="More options"
					aria-expanded={isMenuOpen}
					aria-haspopup="menu"
				>
					<MoreHorizontal class="w-5 h-5 text-text-secondary" />
				</button>

				{#if isMenuOpen}
					<div
						class="absolute right-0 top-full mt-1 bg-surface border border-border rounded-xl shadow-xl z-10 min-w-[200px] overflow-hidden"
						role="menu"
						in:scale={{ duration: 150, start: 0.9, opacity: 0 }}
						out:fade={{ duration: 100 }}
					>
						{#if isOwner}
							<button
								type="button"
								class="w-full flex items-center gap-3 px-4 py-3 text-error hover:bg-error/10 transition-colors text-left"
								on:click|stopPropagation={handleDelete}
								role="menuitem"
							>
								<Trash2 class="w-5 h-5" />
								Delete post
							</button>
						{/if}
					</div>
				{/if}
			</div>
		</header>

		<!-- Post Body -->
		<p class="mt-1 text-text whitespace-pre-wrap break-words leading-relaxed">
			{post.body}
		</p>

		<!-- Media Attachment -->
		{#if post.media_url}
			<figure class="mt-3 rounded-2xl overflow-hidden border border-border">
				<img
					src={post.media_url}
					alt="Post media"
					class="w-full max-h-[500px] object-cover transition-opacity duration-300"
					loading="lazy"
				/>
			</figure>
		{/if}

		<!-- ================================================================== -->
		<!-- Action Buttons                                                     -->
		<!-- ================================================================== -->
		{#if showActions}
			<footer class="flex items-center justify-between mt-3 max-w-md -ml-2">
				<!-- Reply Button -->
				<button
					type="button"
					class="group flex items-center gap-1 p-2 rounded-full hover:bg-primary/10 transition-all duration-200 active:scale-90"
					on:click|stopPropagation={handleReply}
					aria-label="Reply"
				>
					<MessageCircle
						class="w-5 h-5 text-text-secondary group-hover:text-primary transition-colors"
					/>
					{#if post.comments_count > 0}
						<span class="text-sm text-text-secondary group-hover:text-primary transition-colors">
							{formattedReplies}
						</span>
					{/if}
				</button>

				<!-- Repost Button -->
				<button
					type="button"
					class={clsx(
						'group flex items-center gap-1 p-2 rounded-full transition-all duration-200 active:scale-90',
						post.is_repost ? 'text-success' : 'hover:bg-success/10'
					)}
					on:click|stopPropagation={handleRepost}
					aria-label="Repost"
					aria-pressed={post.is_repost}
				>
					<Repeat2
						class={clsx(
							'w-5 h-5 transition-colors',
							post.is_repost ? 'text-success' : 'text-text-secondary group-hover:text-success'
						)}
					/>
					{#if post.reposts_count > 0}
						<span
							class={clsx(
								'text-sm transition-colors',
								post.is_repost ? 'text-success' : 'text-text-secondary group-hover:text-success'
							)}
						>
							{formattedReposts}
						</span>
					{/if}
				</button>

				<!-- Like Button -->
				<button
					type="button"
					class={clsx(
						'group flex items-center gap-1 p-2 rounded-full transition-all duration-200 active:scale-90',
						optimisticLiked ? 'text-error' : 'hover:bg-error/10'
					)}
					on:click|stopPropagation={handleLike}
					aria-label={optimisticLiked ? 'Unlike' : 'Like'}
					aria-pressed={optimisticLiked}
				>
					<!-- Heart Icon with Animation -->
					<div class="relative">
						<Heart
							class={clsx(
								'w-5 h-5 transition-all duration-200',
								optimisticLiked ? 'text-error fill-error' : 'text-text-secondary group-hover:text-error',
								isLikeAnimating && 'animate-like-pop'
							)}
						/>

						<!-- Heart Burst Particles -->
						{#if isLikeAnimating}
							<div
								class="absolute inset-0 flex items-center justify-center pointer-events-none"
								out:scale={{ duration: LIKE_ANIMATION_DURATION_MS, start: 1, opacity: 0 }}
								aria-hidden="true"
							>
								{#each particleRotations as rotation}
									<div
										class="absolute w-1 h-1 rounded-full bg-error burst-particle"
										style="--rotation: {rotation}deg"
									/>
								{/each}
							</div>
						{/if}
					</div>

					<!-- Like Count with Animation -->
					{#key optimisticLikesCount}
						<span
							class={clsx(
								'text-sm transition-colors',
								optimisticLiked ? 'text-error' : 'text-text-secondary group-hover:text-error'
							)}
							in:fly={{ y: optimisticLiked ? -8 : 8, duration: 150 }}
						>
							{optimisticLikesCount > 0 ? formattedLikes : ''}
						</span>
					{/key}
				</button>

				<!-- Share Button -->
				<button
					type="button"
					class="group p-2 rounded-full hover:bg-primary/10 transition-all duration-200 active:scale-90"
					on:click|stopPropagation
					aria-label="Share"
				>
					<Share class="w-5 h-5 text-text-secondary group-hover:text-primary transition-colors" />
				</button>
			</footer>
		{/if}
	</div>
</article>

<style>
	/* Heart burst particle animation */
	.burst-particle {
		animation: burst 0.4s ease-out forwards;
		transform: rotate(var(--rotation, 0deg)) translateY(-8px);
	}

	@keyframes burst {
		0% {
			opacity: 1;
			transform: rotate(var(--rotation, 0deg)) translateY(-8px) scale(1);
		}
		100% {
			opacity: 0;
			transform: rotate(var(--rotation, 0deg)) translateY(-20px) scale(0);
		}
	}

	/* Heart pop animation on like */
	:global(.animate-like-pop) {
		animation: like-pop 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
	}

	@keyframes like-pop {
		0% {
			transform: scale(1);
		}
		25% {
			transform: scale(1.3);
		}
		50% {
			transform: scale(0.9);
		}
		75% {
			transform: scale(1.1);
		}
		100% {
			transform: scale(1);
		}
	}
</style>
