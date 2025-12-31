<script lang="ts">
	/**
	 * PostLikeButton - Animated like button with optimistic state management.
	 *
	 * Features:
	 * - Optimistic like/unlike with immediate UI feedback
	 * - Heart pop animation on like
	 * - Heart burst particle effect
	 * - Count animation with fly transition
	 */
	import { fly, scale } from 'svelte/transition';
	import { Heart } from 'lucide-svelte';
	import { clsx } from 'clsx';
	import { formatEngagementCount } from '$lib/types';

	// ============================================================================
	// Constants
	// ============================================================================

	const ANIMATION_DURATION_MS = 400;
	const PARTICLE_COUNT = 6;
	const PARTICLE_ROTATION_STEP = 60;

	// ============================================================================
	// Props
	// ============================================================================

	/** Whether the post is currently liked */
	export let isLiked: boolean;

	/** Current like count */
	export let likesCount: number;

	// ============================================================================
	// State
	// ============================================================================

	let isAnimating = false;

	// Optimistic state for immediate UI feedback
	let optimisticLiked = isLiked;
	let optimisticCount = likesCount;

	// ============================================================================
	// Derived State
	// ============================================================================

	// Sync optimistic state when props change (e.g., from server response)
	$: {
		optimisticLiked = isLiked;
		optimisticCount = likesCount;
	}

	$: formattedCount = formatEngagementCount(optimisticCount);
	$: ariaLabel = optimisticLiked ? 'Unlike' : 'Like';
	$: particleRotations = Array.from(
		{ length: PARTICLE_COUNT },
		(_, i) => i * PARTICLE_ROTATION_STEP
	);

	// ============================================================================
	// Handlers
	// ============================================================================

	function handleClick() {
		const wasLiked = optimisticLiked;

		// Optimistic update
		optimisticLiked = !wasLiked;
		optimisticCount += wasLiked ? -1 : 1;

		// Trigger animation only when liking
		if (!wasLiked) {
			triggerAnimation();
		}
	}

	function triggerAnimation() {
		isAnimating = true;
		setTimeout(() => {
			isAnimating = false;
		}, ANIMATION_DURATION_MS);
	}
</script>

<button
	type="button"
	class={clsx(
		'group flex items-center gap-1 p-2 rounded-full transition-all duration-200 active:scale-90',
		optimisticLiked ? 'text-error' : 'hover:bg-error/10'
	)}
	on:click={handleClick}
	on:click
	aria-label={ariaLabel}
	aria-pressed={optimisticLiked}
>
	<!-- Heart Icon with Animation -->
	<div class="relative">
		<Heart
			class={clsx(
				'w-5 h-5 transition-all duration-200',
				optimisticLiked ? 'text-error fill-error' : 'text-text-secondary group-hover:text-error',
				isAnimating && 'animate-like-pop'
			)}
		/>

		<!-- Heart Burst Particles -->
		{#if isAnimating}
			<div
				class="absolute inset-0 flex items-center justify-center pointer-events-none"
				out:scale={{ duration: ANIMATION_DURATION_MS, start: 1, opacity: 0 }}
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
	{#key optimisticCount}
		<span
			class={clsx(
				'text-sm transition-colors',
				optimisticLiked ? 'text-error' : 'text-text-secondary group-hover:text-error'
			)}
			in:fly={{ y: optimisticLiked ? -8 : 8, duration: 150 }}
		>
			{optimisticCount > 0 ? formattedCount : ''}
		</span>
	{/key}
</button>

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

