<script lang="ts">
	import { clsx } from 'clsx';
	import { Loader2 } from 'lucide-svelte';

	type Variant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
	type Size = 'sm' | 'md' | 'lg';

	export let variant: Variant = 'primary';
	export let size: Size = 'md';
	export let loading: boolean = false;
	export let disabled: boolean = false;
	export let fullWidth: boolean = false;
	export let type: 'button' | 'submit' | 'reset' = 'button';

	const variantClasses: Record<Variant, string> = {
		primary: 'bg-primary text-white hover:bg-primary-hover active:bg-primary-hover',
		secondary: 'bg-transparent text-text border border-border hover:bg-surface-hover',
		outline: 'bg-transparent text-primary border border-primary hover:bg-primary-light',
		ghost: 'bg-transparent text-text-secondary hover:bg-surface-hover hover:text-text',
		danger: 'bg-error text-white hover:bg-red-700'
	};

	const sizeClasses: Record<Size, string> = {
		sm: 'text-xs px-3 py-1.5',
		md: 'text-sm px-4 py-2',
		lg: 'text-base px-6 py-3'
	};

	$: classes = clsx(
		'inline-flex items-center justify-center gap-2 rounded-full font-bold',
		'transition-colors duration-200 cursor-pointer',
		'disabled:opacity-50 disabled:cursor-not-allowed',
		variantClasses[variant],
		sizeClasses[size],
		fullWidth && 'w-full',
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
	{...$$restProps}
>
	{#if loading}
		<Loader2 class="w-4 h-4 animate-spin" />
	{/if}
	<slot />
</button>

