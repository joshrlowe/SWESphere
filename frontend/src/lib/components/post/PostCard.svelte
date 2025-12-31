<script lang="ts">
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

	export let post: Post;
	export let showActions: boolean = true;
	export let compact: boolean = false;

	const dispatch = createEventDispatcher<{
		like: { postId: number; isLiked: boolean };
		reply: { postId: number };
		repost: { postId: number };
		delete: { postId: number };
		click: { postId: number };
	}>();

	let showMenu = false;
	let isLikeAnimating = false;

	// Optimistic state for likes
	let optimisticLiked = post.is_liked;
	let optimisticLikesCount = post.likes_count;

	// Sync with prop changes
	$: {
		optimisticLiked = post.is_liked;
		optimisticLikesCount = post.likes_count;
	}

	$: isOwner = $currentUser?.id === post.user_id;
	$: author = post.author;
	$: timeAgo = formatDistanceToNow(new Date(post.created_at), { addSuffix: true });

	function handleLike() {
		// Optimistic update
		const wasLiked = optimisticLiked;
		optimisticLiked = !wasLiked;
		optimisticLikesCount = wasLiked ? optimisticLikesCount - 1 : optimisticLikesCount + 1;

		// Trigger animation on like (not unlike)
		if (!wasLiked) {
			isLikeAnimating = true;
			setTimeout(() => {
				isLikeAnimating = false;
			}, 400);
		}

		dispatch('like', { postId: post.id, isLiked: !wasLiked });
	}

	function handleReply() {
		dispatch('reply', { postId: post.id });
	}

	function handleRepost() {
		dispatch('repost', { postId: post.id });
	}

	function handleDelete() {
		dispatch('delete', { postId: post.id });
		showMenu = false;
	}

	function handleClick() {
		dispatch('click', { postId: post.id });
	}
</script>

<article
	class={clsx(
		'flex gap-3 border-b border-border transition-colors duration-200 cursor-pointer',
		'hover:bg-surface-hover/50',
		compact ? 'px-4 py-3' : 'p-4'
	)}
	on:click={handleClick}
	on:keydown={(e) => e.key === 'Enter' && handleClick()}
	role="article"
	tabindex="0"
	in:fly={{ y: 20, duration: 300 }}
>
	<!-- Avatar -->
	<a
		href={author ? `/profile/${author.username}` : '#'}
		class="flex-shrink-0 transition-transform duration-200 hover:scale-105"
		on:click|stopPropagation
	>
		<Avatar user={author} size={compact ? 'sm' : 'md'} />
	</a>

	<!-- Content -->
	<div class="flex-1 min-w-0">
		<!-- Header -->
		<div class="flex items-start justify-between gap-2">
			<div class="flex items-center gap-1 min-w-0 flex-wrap">
				{#if author}
					<a
						href={`/profile/${author.username}`}
						class="font-bold text-text hover:underline truncate"
						on:click|stopPropagation
					>
						{author.display_name || author.username}
					</a>
					{#if author.is_verified}
						<BadgeCheck class="w-4 h-4 text-primary flex-shrink-0" />
					{/if}
					<a
						href={`/profile/${author.username}`}
						class="text-text-secondary truncate hover:underline"
						on:click|stopPropagation
					>
						@{author.username}
					</a>
				{/if}
				<span class="text-text-secondary">·</span>
				<span class="text-text-secondary text-sm whitespace-nowrap">{timeAgo}</span>
			</div>

			<!-- Menu -->
			<div class="relative">
				<button
					type="button"
					class="p-2 -m-2 rounded-full hover:bg-primary/10 hover:text-primary transition-colors duration-200"
					on:click|stopPropagation={() => (showMenu = !showMenu)}
					aria-label="More options"
				>
					<MoreHorizontal class="w-5 h-5 text-text-secondary" />
				</button>

				{#if showMenu}
					<div
						class="absolute right-0 top-full mt-1 bg-surface border border-border rounded-xl shadow-xl z-10 min-w-[200px] overflow-hidden"
						in:scale={{ duration: 150, start: 0.9, opacity: 0 }}
						out:fade={{ duration: 100 }}
					>
						{#if isOwner}
							<button
								type="button"
								class="w-full flex items-center gap-3 px-4 py-3 text-error hover:bg-error/10 transition-colors text-left"
								on:click|stopPropagation={handleDelete}
							>
								<Trash2 class="w-5 h-5" />
								Delete post
							</button>
						{/if}
					</div>
				{/if}
			</div>
		</div>

		<!-- Body -->
		<p class="mt-1 text-text whitespace-pre-wrap break-words leading-relaxed">{post.body}</p>

		<!-- Media -->
		{#if post.media_url}
			<div class="mt-3 rounded-2xl overflow-hidden border border-border">
				<img
					src={post.media_url}
					alt="Post media"
					class="w-full max-h-[500px] object-cover transition-opacity duration-300"
					loading="lazy"
				/>
			</div>
		{/if}

		<!-- Actions -->
		{#if showActions}
			<div class="flex items-center justify-between mt-3 max-w-md -ml-2">
				<!-- Reply -->
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
						{formatEngagementCount(post.comments_count)}
					</span>
					{/if}
				</button>

				<!-- Repost -->
				<button
					type="button"
					class={clsx(
						'group flex items-center gap-1 p-2 rounded-full transition-all duration-200 active:scale-90',
						post.is_repost ? 'text-success' : 'hover:bg-success/10'
					)}
					on:click|stopPropagation={handleRepost}
					aria-label="Repost"
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
						{formatEngagementCount(post.reposts_count)}
					</span>
					{/if}
				</button>

				<!-- Like -->
				<button
					type="button"
					class={clsx(
						'group flex items-center gap-1 p-2 rounded-full transition-all duration-200 active:scale-90',
						optimisticLiked ? 'text-error' : 'hover:bg-error/10'
					)}
					on:click|stopPropagation={handleLike}
					aria-label={optimisticLiked ? 'Unlike' : 'Like'}
				>
					<div class="relative">
					<Heart
						class={clsx(
								'w-5 h-5 transition-all duration-200',
								optimisticLiked
								? 'text-error fill-error'
									: 'text-text-secondary group-hover:text-error',
								isLikeAnimating && 'animate-like-pop'
						)}
					/>
						<!-- Heart burst animation -->
						{#if isLikeAnimating}
							<div
								class="absolute inset-0 flex items-center justify-center pointer-events-none"
								out:scale={{ duration: 400, start: 1, opacity: 0 }}
							>
								{#each Array(6) as _, i}
									<div
										class="absolute w-1 h-1 rounded-full bg-error"
										style="
											transform: rotate({i * 60}deg) translateY(-12px);
											animation: burst 0.4s ease-out forwards;
										"
									/>
								{/each}
							</div>
						{/if}
					</div>
					{#key optimisticLikesCount}
					<span
						class={clsx(
								'text-sm transition-colors',
								optimisticLiked ? 'text-error' : 'text-text-secondary group-hover:text-error'
						)}
							in:fly={{ y: optimisticLiked ? -8 : 8, duration: 150 }}
					>
							{optimisticLikesCount > 0 ? formatEngagementCount(optimisticLikesCount) : ''}
					</span>
					{/key}
				</button>

				<!-- Share -->
				<button
					type="button"
					class="group p-2 rounded-full hover:bg-primary/10 transition-all duration-200 active:scale-90"
					on:click|stopPropagation
					aria-label="Share"
				>
					<Share class="w-5 h-5 text-text-secondary group-hover:text-primary transition-colors" />
				</button>
			</div>
		{/if}
	</div>
</article>

<!-- Close menu on click outside -->
<svelte:window on:click={() => (showMenu = false)} />

<style>
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
