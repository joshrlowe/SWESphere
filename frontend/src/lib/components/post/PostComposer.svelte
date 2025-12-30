<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { Image, Smile, MapPin, X } from 'lucide-svelte';
	import { clsx } from 'clsx';
	import { Avatar, Button } from '$lib/components/ui';
	import { currentUser } from '$lib/stores';
	import { createPost } from '$lib/api/posts';
	import { toast } from 'svelte-sonner';

	export let placeholder: string = "What's happening?";
	export let replyToId: number | undefined = undefined;
	export let maxLength: number = 280;

	const dispatch = createEventDispatcher<{
		submit: { body: string; replyToId?: number };
		cancel: void;
	}>();

	let body = '';
	let isSubmitting = false;
	let textareaEl: HTMLTextAreaElement;

	$: charCount = body.length;
	$: isOverLimit = charCount > maxLength;
	$: canSubmit = body.trim().length > 0 && !isOverLimit && !isSubmitting;
	$: charCountColor = isOverLimit
		? 'text-error'
		: charCount > maxLength * 0.9
			? 'text-warning'
			: 'text-text-muted';

	function handleInput() {
		// Auto-resize textarea
		if (textareaEl) {
			textareaEl.style.height = 'auto';
			textareaEl.style.height = `${textareaEl.scrollHeight}px`;
		}
	}

	async function handleSubmit() {
		if (!canSubmit) return;

		isSubmitting = true;

		try {
			await createPost({
				body: body.trim(),
				reply_to_id: replyToId
			});

			body = '';
			if (textareaEl) {
				textareaEl.style.height = 'auto';
			}

			toast.success(replyToId ? 'Reply posted!' : 'Post created!');
			dispatch('submit', { body, replyToId });
		} catch (error) {
			toast.error('Failed to create post');
		} finally {
			isSubmitting = false;
		}
	}

	function handleCancel() {
		dispatch('cancel');
	}

	function handleKeyDown(event: KeyboardEvent) {
		if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
			event.preventDefault();
			handleSubmit();
		}
	}
</script>

<div class="flex gap-3 p-4 border-b border-border">
	<Avatar user={$currentUser} size="md" />

	<div class="flex-1 min-w-0">
		<textarea
			bind:this={textareaEl}
			bind:value={body}
			{placeholder}
			class={clsx(
				'w-full bg-transparent text-xl text-text placeholder:text-text-muted',
				'resize-none outline-none min-h-[52px] max-h-[300px]'
			)}
			rows="1"
			on:input={handleInput}
			on:keydown={handleKeyDown}
		></textarea>

		<!-- Toolbar -->
		<div class="flex items-center justify-between mt-3 pt-3 border-t border-border">
			<div class="flex items-center gap-1">
				<button
					type="button"
					class="p-2 rounded-full hover:bg-primary-light text-primary transition-colors"
					aria-label="Add image"
				>
					<Image class="w-5 h-5" />
				</button>
				<button
					type="button"
					class="p-2 rounded-full hover:bg-primary-light text-primary transition-colors"
					aria-label="Add emoji"
				>
					<Smile class="w-5 h-5" />
				</button>
				<button
					type="button"
					class="p-2 rounded-full hover:bg-primary-light text-primary transition-colors"
					aria-label="Add location"
				>
					<MapPin class="w-5 h-5" />
				</button>
			</div>

			<div class="flex items-center gap-3">
				{#if charCount > 0}
					<div class="flex items-center gap-2">
						<svg class="w-5 h-5 -rotate-90" viewBox="0 0 20 20">
							<circle
								r="9"
								cx="10"
								cy="10"
								fill="transparent"
								stroke="currentColor"
								stroke-width="2"
								class="text-border"
							/>
							<circle
								r="9"
								cx="10"
								cy="10"
								fill="transparent"
								stroke="currentColor"
								stroke-width="2"
								stroke-dasharray={2 * Math.PI * 9}
								stroke-dashoffset={2 * Math.PI * 9 * (1 - Math.min(charCount / maxLength, 1))}
								class={charCountColor}
							/>
						</svg>
						{#if charCount > maxLength * 0.8}
							<span class={clsx('text-sm', charCountColor)}>
								{maxLength - charCount}
							</span>
						{/if}
					</div>
				{/if}

				{#if replyToId}
					<button
						type="button"
						class="p-1.5 rounded-full hover:bg-surface-hover text-text-secondary"
						on:click={handleCancel}
						aria-label="Cancel"
					>
						<X class="w-4 h-4" />
					</button>
				{/if}

				<Button
					variant="primary"
					disabled={!canSubmit}
					loading={isSubmitting}
					on:click={handleSubmit}
				>
					{replyToId ? 'Reply' : 'Post'}
				</Button>
			</div>
		</div>
	</div>
</div>

