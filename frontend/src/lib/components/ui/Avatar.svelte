<script lang="ts">
	import { clsx } from 'clsx';
	import { fade } from 'svelte/transition';
	import { getAvatarUrl, type User, type UserPreview } from '$lib/types';

	type Size = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';

	export let user: User | UserPreview | null = null;
	export let src: string | null = null;
	export let alt: string = '';
	export let size: Size = 'md';
	export let ring: boolean = false;
	export let fallback: string | null = null;

	const sizeClasses: Record<Size, string> = {
		xs: 'w-6 h-6 text-xs',
		sm: 'w-8 h-8 text-sm',
		md: 'w-10 h-10 text-base',
		lg: 'w-12 h-12 text-lg',
		xl: 'w-16 h-16 text-xl',
		'2xl': 'w-32 h-32 text-4xl'
	};

	const ringClasses: Record<Size, string> = {
		xs: 'ring-1 ring-offset-1',
		sm: 'ring-2 ring-offset-1',
		md: 'ring-2 ring-offset-2',
		lg: 'ring-2 ring-offset-2',
		xl: 'ring-3 ring-offset-2',
		'2xl': 'ring-4 ring-offset-2'
	};

	let imageError = false;

	$: imageSrc = src || (user ? getAvatarUrl(user) : null);
	$: imageAlt = alt || (user ? `@${user.username}` : 'Avatar');
	$: initials = getInitials();
	$: showImage = imageSrc && !imageError;

	$: classes = clsx(
		'rounded-full flex-shrink-0 overflow-hidden',
		sizeClasses[size],
		ring && [ringClasses[size], 'ring-primary ring-offset-background'],
		$$props.class
	);

	function getInitials(): string {
		// Use provided fallback first
		if (fallback) {
			return fallback.slice(0, 2).toUpperCase();
		}

		// Try to get from user
		if (user) {
			if (user.display_name) {
				const parts = user.display_name.trim().split(/\s+/);
				if (parts.length >= 2) {
					return (parts[0][0] + parts[1][0]).toUpperCase();
				}
				return parts[0].slice(0, 2).toUpperCase();
			}
			return user.username.slice(0, 2).toUpperCase();
		}

		return '?';
	}

	function handleError() {
		imageError = true;
	}

	// Reset error state when src changes
	$: if (imageSrc) {
		imageError = false;
	}
</script>

<div class={classes}>
	{#if showImage}
		<img
			src={imageSrc}
			alt={imageAlt}
			class="w-full h-full object-cover"
			on:error={handleError}
			in:fade={{ duration: 150 }}
		/>
{:else}
		<div
			class="w-full h-full flex items-center justify-center bg-gradient-to-br from-primary/80 to-primary text-white font-semibold select-none"
			in:fade={{ duration: 150 }}
		>
			{initials}
	</div>
{/if}
</div>
