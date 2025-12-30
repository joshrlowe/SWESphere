<script lang="ts">
	import { clsx } from 'clsx';

	type Size = 'sm' | 'md' | 'lg';

	export let size: Size = 'md';

	const sizeClasses: Record<Size, string> = {
		sm: 'w-4 h-4 border-2',
		md: 'w-8 h-8 border-2',
		lg: 'w-12 h-12 border-3'
	};
</script>

<div
	class={clsx(
		'animate-spin rounded-full border-text-muted border-t-primary',
		sizeClasses[size],
		$$props.class
	)}
	role="status"
	aria-label="Loading"
>
	<span class="sr-only">Loading...</span>
</div>

