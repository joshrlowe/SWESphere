<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { fade, fly } from 'svelte/transition';
	import { X } from 'lucide-svelte';
	import { clsx } from 'clsx';

	export let open: boolean = false;
	export let title: string = '';
	export let showClose: boolean = true;
	export let size: 'sm' | 'md' | 'lg' | 'xl' = 'md';

	const dispatch = createEventDispatcher<{ close: void }>();

	const sizeClasses: Record<typeof size, string> = {
		sm: 'max-w-sm',
		md: 'max-w-lg',
		lg: 'max-w-2xl',
		xl: 'max-w-4xl'
	};

	function handleClose() {
		open = false;
		dispatch('close');
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			handleClose();
		}
	}

	function handleBackdropClick(event: MouseEvent) {
		if (event.target === event.currentTarget) {
			handleClose();
		}
	}
</script>

<svelte:window on:keydown={handleKeydown} />

{#if open}
	<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
	<div
		class="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4"
		transition:fade={{ duration: 150 }}
		on:click={handleBackdropClick}
	>
		<div
			class={clsx(
				'bg-surface rounded-2xl w-full max-h-[90vh] overflow-hidden shadow-xl',
				sizeClasses[size],
				$$props.class
			)}
			transition:fly={{ y: 10, duration: 200 }}
			role="dialog"
			aria-modal="true"
			aria-labelledby={title ? 'modal-title' : undefined}
		>
			{#if title || showClose}
				<div class="flex items-center gap-4 px-4 py-3 border-b border-border">
					{#if showClose}
						<button
							type="button"
							class="p-2 -ml-2 rounded-full hover:bg-surface-hover transition-colors"
							on:click={handleClose}
							aria-label="Close"
						>
							<X class="w-5 h-5" />
						</button>
					{/if}
					{#if title}
						<h2 id="modal-title" class="text-xl font-bold flex-1">{title}</h2>
					{/if}
					<slot name="header-action" />
				</div>
			{/if}

			<div class="overflow-y-auto">
				<slot />
			</div>

			{#if $$slots.footer}
				<div class="flex items-center justify-end gap-2 px-4 py-3 border-t border-border">
					<slot name="footer" />
				</div>
			{/if}
		</div>
	</div>
{/if}

