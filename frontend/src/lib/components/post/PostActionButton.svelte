<script lang="ts">
	/**
	 * PostActionButton - A reusable action button for post interactions.
	 *
	 * Handles the common pattern of icon + count with hover states
	 * and color variants for reply, repost, like, and share actions.
	 */
	import { clsx } from 'clsx';
	import type { ComponentType } from 'svelte';

	// ============================================================================
	// Props
	// ============================================================================

	/** The Lucide icon component to render */
	export let icon: ComponentType;

	/** Accessible label for the button */
	export let label: string;

	/** Engagement count to display (optional) */
	export let count: number | null = null;

	/** Formatted count string (optional, uses count if not provided) */
	export let formattedCount: string = '';

	/** Whether the action is currently active (liked, reposted, etc.) */
	export let active: boolean = false;

	/** Color variant for hover and active states */
	export let variant: 'primary' | 'success' | 'error' = 'primary';

	// ============================================================================
	// Styling
	// ============================================================================

	const variantStyles = {
		primary: {
			hover: 'hover:bg-primary/10',
			text: 'group-hover:text-primary',
			active: 'text-primary'
		},
		success: {
			hover: 'hover:bg-success/10',
			text: 'group-hover:text-success',
			active: 'text-success'
		},
		error: {
			hover: 'hover:bg-error/10',
			text: 'group-hover:text-error',
			active: 'text-error'
		}
	};

	$: styles = variantStyles[variant];
	$: displayCount = formattedCount || (count && count > 0 ? String(count) : '');
</script>

<button
	type="button"
	class={clsx(
		'group flex items-center gap-1 p-2 rounded-full transition-all duration-200 active:scale-90',
		active ? styles.active : styles.hover
	)}
	on:click
	aria-label={label}
>
	<slot name="icon">
		<svelte:component
			this={icon}
			class={clsx(
				'w-5 h-5 transition-colors',
				active ? styles.active : `text-text-secondary ${styles.text}`
			)}
		/>
	</slot>

	{#if displayCount}
		<slot name="count">
			<span
				class={clsx(
					'text-sm transition-colors',
					active ? styles.active : `text-text-secondary ${styles.text}`
				)}
			>
				{displayCount}
			</span>
		</slot>
	{/if}
</button>

