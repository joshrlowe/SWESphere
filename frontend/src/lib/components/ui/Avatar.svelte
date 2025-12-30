<script lang="ts">
	import { clsx } from 'clsx';
	import { getAvatarUrl, type User, type UserPreview } from '$lib/types';

	type Size = 'sm' | 'md' | 'lg' | 'xl' | '2xl';

	export let user: User | UserPreview | null = null;
	export let src: string | null = null;
	export let alt: string = '';
	export let size: Size = 'md';

	const sizeClasses: Record<Size, string> = {
		sm: 'w-8 h-8',
		md: 'w-10 h-10',
		lg: 'w-12 h-12',
		xl: 'w-16 h-16',
		'2xl': 'w-32 h-32'
	};

	$: imageSrc = src || (user ? getAvatarUrl(user) : null);
	$: imageAlt = alt || (user ? `@${user.username}` : 'Avatar');

	$: classes = clsx(
		'rounded-full object-cover bg-surface flex-shrink-0',
		sizeClasses[size],
		$$props.class
	);

	function handleError(event: Event) {
		const img = event.target as HTMLImageElement;
		img.src = `https://api.dicebear.com/7.x/identicon/svg?seed=${Math.random()}&size=128`;
	}
</script>

{#if imageSrc}
	<img {src} alt={imageAlt} class={classes} on:error={handleError} />
{:else}
	<div class={clsx(classes, 'flex items-center justify-center text-text-muted')}>
		<svg
			class="w-1/2 h-1/2"
			fill="currentColor"
			viewBox="0 0 24 24"
			xmlns="http://www.w3.org/2000/svg"
		>
			<path
				d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"
			/>
		</svg>
	</div>
{/if}

