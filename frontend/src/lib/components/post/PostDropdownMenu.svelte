<script lang="ts">
	/**
	 * PostDropdownMenu - Dropdown menu for post-level actions.
	 *
	 * Displays contextual actions like delete (for post owner).
	 * Handles click-outside-to-close and keyboard accessibility.
	 */
	import { scale, fade } from 'svelte/transition';
	import { MoreHorizontal, Trash2 } from 'lucide-svelte';

	// ============================================================================
	// Props
	// ============================================================================

	/** Whether the current user owns this post */
	export let isOwner: boolean = false;

	// ============================================================================
	// State
	// ============================================================================

	let isOpen = false;

	// ============================================================================
	// Handlers
	// ============================================================================

	function toggle() {
		isOpen = !isOpen;
	}

	function close() {
		isOpen = false;
	}

	function handleDelete() {
		close();
	}
</script>

<!-- Close menu when clicking anywhere -->
<svelte:window on:click={close} />

<div class="relative">
	<button
		type="button"
		class="p-2 -m-2 rounded-full hover:bg-primary/10 hover:text-primary transition-colors duration-200"
		on:click|stopPropagation={toggle}
		aria-label="More options"
		aria-expanded={isOpen}
		aria-haspopup="menu"
	>
		<MoreHorizontal class="w-5 h-5 text-text-secondary" />
	</button>

	{#if isOpen}
		<div
			class="absolute right-0 top-full mt-1 bg-surface border border-border rounded-xl shadow-xl z-10 min-w-[200px] overflow-hidden"
			role="menu"
			in:scale={{ duration: 150, start: 0.9, opacity: 0 }}
			out:fade={{ duration: 100 }}
		>
			{#if isOwner}
				<button
					type="button"
					class="w-full flex items-center gap-3 px-4 py-3 text-error hover:bg-error/10 transition-colors text-left"
					on:click|stopPropagation={handleDelete}
					on:click
					role="menuitem"
				>
					<Trash2 class="w-5 h-5" />
					Delete post
				</button>
			{/if}
		</div>
	{/if}
</div>

