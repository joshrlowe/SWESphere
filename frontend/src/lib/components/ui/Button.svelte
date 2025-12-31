<script lang="ts">
	import { clsx } from 'clsx';
	import { Loader2 } from 'lucide-svelte';
	import { scale } from 'svelte/transition';

	type Variant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
	type Size = 'sm' | 'md' | 'lg';

	export let variant: Variant = 'primary';
	export let size: Size = 'md';
	export let loading: boolean = false;
	export let disabled: boolean = false;
	export let fullWidth: boolean = false;
	export let type: 'button' | 'submit' | 'reset' = 'button';

	const variantClasses: Record<Variant, string> = {
		primary:
			'bg-primary text-white hover:bg-primary-hover active:bg-primary-hover shadow-sm hover:shadow',
		secondary:
			'bg-transparent text-text border border-border hover:bg-surface-hover active:bg-surface',
		outline:
			'bg-transparent text-primary border border-primary hover:bg-primary/10 active:bg-primary/20',
		ghost:
			'bg-transparent text-text-secondary hover:bg-surface-hover hover:text-text active:bg-surface',
		danger:
			'bg-error text-white hover:bg-red-600 active:bg-red-700 shadow-sm hover:shadow'
	};

	const sizeClasses: Record<Size, string> = {
		sm: 'text-xs px-3 py-1.5 gap-1.5',
		md: 'text-sm px-4 py-2 gap-2',
		lg: 'text-base px-6 py-3 gap-2.5'
	};

	const iconSizeClasses: Record<Size, string> = {
		sm: 'w-3 h-3',
		md: 'w-4 h-4',
		lg: 'w-5 h-5'
	};

	$: classes = clsx(
		// Base styles
		'inline-flex items-center justify-center rounded-full font-bold',
		'select-none outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background',
		// Transitions & animations
		'transition-all duration-200 ease-out',
		'active:scale-95',
		// Disabled state
		'disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100',
		// Variant & size
		variantClasses[variant],
		sizeClasses[size],
		// Full width
		fullWidth && 'w-full',
		// Custom classes
		$$props.class
	);
</script>

<button
	{type}
	class={classes}
	disabled={disabled || loading}
	on:click
	on:mouseenter
	on:mouseleave
	on:focus
	on:blur
	{...$$restProps}
>
	{#if loading}
		<span
			class="inline-flex"
			in:scale={{ duration: 150, start: 0.5 }}
			out:scale={{ duration: 100, start: 0.5 }}
		>
			<Loader2 class={clsx('animate-spin', iconSizeClasses[size])} />
		</span>
	{/if}
	<slot />
</button>
