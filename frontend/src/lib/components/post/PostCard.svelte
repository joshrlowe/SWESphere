<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { formatDistanceToNow } from 'date-fns';
	import { Heart, MessageCircle, Repeat2, Share, MoreHorizontal, Trash2, BadgeCheck } from 'lucide-svelte';
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

	$: isOwner = $currentUser?.id === post.user_id;
	$: author = post.author;
	$: timeAgo = formatDistanceToNow(new Date(post.created_at), { addSuffix: true });

	function handleLike() {
		dispatch('like', { postId: post.id, isLiked: !post.is_liked });
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
		'flex gap-3 border-b border-border hover:bg-surface-hover transition-colors duration-200 cursor-pointer',
		compact ? 'px-4 py-3' : 'p-4'
	)}
	on:click={handleClick}
	on:keydown={(e) => e.key === 'Enter' && handleClick()}
	role="article"
	tabindex="0"
>
	<!-- Avatar -->
	<a
		href={author ? `/profile/${author.username}` : '#'}
		class="flex-shrink-0"
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
						class="text-text-secondary truncate"
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
					class="p-2 -m-2 rounded-full hover:bg-primary-light hover:text-primary transition-colors"
					on:click|stopPropagation={() => (showMenu = !showMenu)}
					aria-label="More options"
				>
					<MoreHorizontal class="w-5 h-5" />
				</button>

				{#if showMenu}
					<div
						class="absolute right-0 top-full mt-1 bg-surface border border-border rounded-xl shadow-lg z-10 min-w-[200px] overflow-hidden"
					>
						{#if isOwner}
							<button
								type="button"
								class="w-full flex items-center gap-3 px-4 py-3 text-error hover:bg-surface-hover transition-colors text-left"
								on:click|stopPropagation={handleDelete}
							>
								<Trash2 class="w-5 h-5" />
								Delete
							</button>
						{/if}
					</div>
				{/if}
			</div>
		</div>

		<!-- Body -->
		<p class="mt-1 text-text whitespace-pre-wrap break-words">{post.body}</p>

		<!-- Media -->
		{#if post.media_url}
			<div class="mt-3 rounded-2xl overflow-hidden border border-border">
				<img
					src={post.media_url}
					alt="Post media"
					class="w-full max-h-[500px] object-cover"
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
					class="group flex items-center gap-1 p-2 rounded-full hover:bg-primary-light transition-colors"
					on:click|stopPropagation={handleReply}
					aria-label="Reply"
				>
					<MessageCircle class="w-5 h-5 text-text-secondary group-hover:text-primary" />
					<span class="text-sm text-text-secondary group-hover:text-primary">
						{formatEngagementCount(post.comments_count)}
					</span>
				</button>

				<!-- Repost -->
				<button
					type="button"
					class={clsx(
						'group flex items-center gap-1 p-2 rounded-full transition-colors',
						post.is_repost ? 'text-success' : 'hover:bg-green-500/10'
					)}
					on:click|stopPropagation={handleRepost}
					aria-label="Repost"
				>
					<Repeat2
						class={clsx(
							'w-5 h-5',
							post.is_repost ? 'text-success' : 'text-text-secondary group-hover:text-success'
						)}
					/>
					<span
						class={clsx(
							'text-sm',
							post.is_repost ? 'text-success' : 'text-text-secondary group-hover:text-success'
						)}
					>
						{formatEngagementCount(post.reposts_count)}
					</span>
				</button>

				<!-- Like -->
				<button
					type="button"
					class={clsx(
						'group flex items-center gap-1 p-2 rounded-full transition-colors',
						post.is_liked ? 'text-error' : 'hover:bg-red-500/10'
					)}
					on:click|stopPropagation={handleLike}
					aria-label={post.is_liked ? 'Unlike' : 'Like'}
				>
					<Heart
						class={clsx(
							'w-5 h-5',
							post.is_liked
								? 'text-error fill-error'
								: 'text-text-secondary group-hover:text-error'
						)}
					/>
					<span
						class={clsx(
							'text-sm',
							post.is_liked ? 'text-error' : 'text-text-secondary group-hover:text-error'
						)}
					>
						{formatEngagementCount(post.likes_count)}
					</span>
				</button>

				<!-- Share -->
				<button
					type="button"
					class="group p-2 rounded-full hover:bg-primary-light transition-colors"
					on:click|stopPropagation
					aria-label="Share"
				>
					<Share class="w-5 h-5 text-text-secondary group-hover:text-primary" />
				</button>
			</div>
		{/if}
	</div>
</article>

<!-- Close menu on click outside -->
<svelte:window on:click={() => (showMenu = false)} />

