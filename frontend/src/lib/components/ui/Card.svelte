<script lang="ts">
	import { clsx } from 'clsx';

	export let hover: boolean = false;
	export let padding: boolean = true;
	export let as: 'div' | 'article' | 'section' = 'div';
</script>

<svelte:element
	this={as}
	class={clsx(
		'bg-surface border border-border rounded-2xl',
		hover && 'hover:bg-surface-hover transition-colors duration-200 cursor-pointer',
		padding && 'p-4',
		$$props.class
	)}
	on:click
	{...$$restProps}
>
	<slot />
</svelte:element>

