<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { scale, fly, fade } from 'svelte/transition';
	import { spring } from 'svelte/motion';
	import { Bell } from 'lucide-svelte';
	import { clsx } from 'clsx';

	export let count: number = 0;
	export let maxDisplay: number = 99;
	export let href: string = '/notifications';
	export let size: 'sm' | 'md' | 'lg' = 'md';

	const dispatch = createEventDispatcher<{
		click: void;
	}>();

	let previousCount = count;
	let hasNewNotification = false;

	// Spring animation for the bell shake
	const bellRotation = spring(0, { stiffness: 0.2, damping: 0.3 });

	const sizeClasses = {
		sm: 'w-8 h-8',
		md: 'w-10 h-10',
		lg: 'w-12 h-12'
	};

	const iconSizes = {
		sm: 'w-4 h-4',
		md: 'w-5 h-5',
		lg: 'w-6 h-6'
	};

	const badgeSizes = {
		sm: 'min-w-[14px] h-[14px] text-[9px] -top-0.5 -right-0.5',
		md: 'min-w-[18px] h-[18px] text-[10px] -top-1 -right-1',
		lg: 'min-w-[22px] h-[22px] text-xs -top-1 -right-1'
	};

	$: displayCount = count > maxDisplay ? `${maxDisplay}+` : count.toString();
	$: hasUnread = count > 0;

	// Trigger animation when count increases
	$: if (count > previousCount) {
		triggerNewNotificationAnimation();
	}

	$: previousCount = count;

	function triggerNewNotificationAnimation() {
		hasNewNotification = true;

		// Shake the bell
		bellRotation.set(15);
		setTimeout(() => bellRotation.set(-15), 100);
		setTimeout(() => bellRotation.set(10), 200);
		setTimeout(() => bellRotation.set(-10), 300);
		setTimeout(() => bellRotation.set(0), 400);

		// Reset animation state
		setTimeout(() => {
			hasNewNotification = false;
		}, 600);
	}

	function handleClick(event: MouseEvent) {
		dispatch('click');
	}

	onMount(() => {
		previousCount = count;
	});
</script>

<a
	{href}
	class={clsx(
		'relative inline-flex items-center justify-center rounded-full',
		'transition-all duration-200 ease-out',
		'hover:bg-surface-hover active:scale-95',
		'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background',
		sizeClasses[size]
	)}
	on:click={handleClick}
	aria-label={hasUnread ? `${count} unread notifications` : 'Notifications'}
>
	<!-- Bell icon with shake animation -->
	<div style="transform: rotate({$bellRotation}deg)">
		<Bell
			class={clsx(
				iconSizes[size],
				'transition-colors duration-200',
				hasUnread ? 'text-text' : 'text-text-secondary'
			)}
		/>
	</div>

	<!-- Badge -->
	{#if hasUnread}
		<span
			class={clsx(
				'absolute flex items-center justify-center',
				'bg-error text-white font-bold rounded-full',
				'px-1 leading-none',
				badgeSizes[size],
				hasNewNotification && 'animate-bounce-subtle'
			)}
			in:scale={{ duration: 200, start: 0.5, opacity: 0 }}
		>
			{displayCount}
		</span>
	{/if}

	<!-- Pulse ring for new notifications -->
	{#if hasNewNotification}
		<span
			class="absolute inset-0 rounded-full bg-primary/30 animate-ping-slow"
			out:fade={{ duration: 300 }}
		></span>
	{/if}
</a>

<style>
	:global(.animate-bounce-subtle) {
		animation: bounce-subtle 0.5s ease-in-out;
	}

	@keyframes bounce-subtle {
		0%,
		100% {
			transform: scale(1);
		}
		50% {
			transform: scale(1.2);
		}
	}

	:global(.animate-ping-slow) {
		animation: ping-slow 1s cubic-bezier(0, 0, 0.2, 1) forwards;
	}

	@keyframes ping-slow {
		0% {
			transform: scale(1);
			opacity: 0.5;
		}
		100% {
			transform: scale(1.5);
			opacity: 0;
		}
	}
</style>

