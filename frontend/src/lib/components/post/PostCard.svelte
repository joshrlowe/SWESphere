<script lang="ts">
	/**
	 * PostCard - Displays a single post with author info, content, and action buttons.
	 *
	 * A composition of focused sub-components:
	 * - PostActionButton for reply, repost, share
	 * - PostLikeButton for animated like interactions
	 * - PostDropdownMenu for post-level actions
	 */
	import { createEventDispatcher } from 'svelte';
	import { fly } from 'svelte/transition';
	import { formatDistanceToNow } from 'date-fns';
	import { MessageCircle, Repeat2, Share, BadgeCheck } from 'lucide-svelte';
	import { clsx } from 'clsx';

	import { Avatar } from '$lib/components/ui';
	import { formatEngagementCount, getDisplayName, type Post } from '$lib/types';
	import { currentUser } from '$lib/stores';

	import PostActionButton from './PostActionButton.svelte';
	import PostLikeButton from './PostLikeButton.svelte';
	import PostDropdownMenu from './PostDropdownMenu.svelte';

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
	// Derived State
	// ============================================================================

	$: author = post.author;
	$: isOwner = $currentUser?.id === post.user_id;
	$: profileUrl = author ? `/profile/${author.username}` : '#';
	$: displayName = author ? getDisplayName(author) : 'Unknown';
	$: formattedTime = formatDistanceToNow(new Date(post.created_at), { addSuffix: true });

	// Pre-format engagement counts for display
	$: formattedReplies = formatEngagementCount(post.comments_count);
	$: formattedReposts = formatEngagementCount(post.reposts_count);

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
	}
</script>

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
	<!-- Avatar -->
	<a
		href={profileUrl}
		class="flex-shrink-0 transition-transform duration-200 hover:scale-105"
		on:click|stopPropagation
	>
		<Avatar user={author} size={compact ? 'sm' : 'md'} />
	</a>

	<!-- Content -->
	<div class="flex-1 min-w-0">
		<!-- Header: Author info + Menu -->
		<header class="flex items-start justify-between gap-2">
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

			<PostDropdownMenu {isOwner} on:click={handleDelete} />
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

		<!-- Action Buttons -->
		{#if showActions}
			<footer class="flex items-center justify-between mt-3 max-w-md -ml-2">
				<PostActionButton
					icon={MessageCircle}
					label="Reply"
					count={post.comments_count}
					formattedCount={formattedReplies}
					variant="primary"
					on:click|stopPropagation={handleReply}
				/>

				<PostActionButton
					icon={Repeat2}
					label="Repost"
					count={post.reposts_count}
					formattedCount={formattedReposts}
					active={post.is_repost}
					variant="success"
					on:click|stopPropagation={handleRepost}
				/>

				<div on:click|stopPropagation on:keydown|stopPropagation>
					<PostLikeButton
						isLiked={post.is_liked}
						likesCount={post.likes_count}
						on:click={handleLike}
					/>
				</div>

				<PostActionButton
					icon={Share}
					label="Share"
					variant="primary"
					on:click|stopPropagation
				/>
			</footer>
		{/if}
	</div>
</article>
