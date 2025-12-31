<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { fly, fade } from 'svelte/transition';
	import { Image, Smile, MapPin, X, Calendar } from 'lucide-svelte';
	import { clsx } from 'clsx';
	import { Avatar, Button } from '$lib/components/ui';
	import { currentUser } from '$lib/stores';
	import { createPost } from '$lib/api/posts';
	import { toast } from 'svelte-sonner';

	export let placeholder: string = "What's happening?";
	export let replyToId: number | undefined = undefined;
	export let maxLength: number = 280;
	export let autofocus: boolean = false;

	const dispatch = createEventDispatcher<{
		submit: { body: string; replyToId?: number };
		cancel: void;
	}>();

	let body = '';
	let isSubmitting = false;
	let isFocused = false;
	let textareaEl: HTMLTextAreaElement;

	$: charCount = body.length;
	$: isOverLimit = charCount > maxLength;
	$: isNearLimit = charCount > maxLength * 0.9;
	$: canSubmit = body.trim().length > 0 && !isOverLimit && !isSubmitting;
	$: progress = Math.min(charCount / maxLength, 1);
	$: circumference = 2 * Math.PI * 9;
	$: strokeDashoffset = circumference * (1 - progress);

	$: charCountColor = isOverLimit
		? 'text-error stroke-error'
		: isNearLimit
			? 'text-warning stroke-warning'
			: 'text-text-muted stroke-primary';

	function handleInput() {
		// Auto-resize textarea
		if (textareaEl) {
			textareaEl.style.height = 'auto';
			textareaEl.style.height = `${Math.min(textareaEl.scrollHeight, 300)}px`;
		}
	}

	async function handleSubmit() {
		if (!canSubmit) return;

		isSubmitting = true;
		const postBody = body.trim();

		try {
			await createPost({
				body: postBody,
				reply_to_id: replyToId
			});

			body = '';
			if (textareaEl) {
				textareaEl.style.height = 'auto';
			}

			toast.success(replyToId ? 'Reply posted!' : 'Post created!');
			dispatch('submit', { body: postBody, replyToId });
		} catch (error) {
			toast.error('Failed to create post. Please try again.');
		} finally {
			isSubmitting = false;
		}
	}

	function handleCancel() {
		body = '';
		if (textareaEl) {
			textareaEl.style.height = 'auto';
		}
		dispatch('cancel');
	}

	function handleKeyDown(event: KeyboardEvent) {
		if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
			event.preventDefault();
			handleSubmit();
		}
	}

	function handleFocus() {
		isFocused = true;
	}

	function handleBlur() {
		if (!body.trim()) {
			isFocused = false;
		}
	}
</script>

<div
	class={clsx(
		'flex gap-3 p-4 border-b border-border transition-colors duration-200',
		isFocused && 'bg-surface-hover/30'
	)}
>
	<Avatar user={$currentUser} size="md" />

	<div class="flex-1 min-w-0">
		<textarea
			bind:this={textareaEl}
			bind:value={body}
			{placeholder}
			class={clsx(
				'w-full bg-transparent text-xl text-text placeholder:text-text-muted',
				'resize-none outline-none min-h-[52px] max-h-[300px]',
				'transition-all duration-200'
			)}
			rows="1"
			on:input={handleInput}
			on:keydown={handleKeyDown}
			on:focus={handleFocus}
			on:blur={handleBlur}
			autofocus={autofocus}
		></textarea>

		<!-- Toolbar -->
		{#if isFocused || body.length > 0}
			<div
				class="flex items-center justify-between mt-3 pt-3 border-t border-border"
				in:fly={{ y: 10, duration: 200 }}
			>
				<!-- Media buttons -->
				<div class="flex items-center gap-0.5">
				<button
					type="button"
						class="p-2 rounded-full hover:bg-primary/10 text-primary transition-all duration-200 active:scale-90"
					aria-label="Add image"
						title="Add image"
				>
					<Image class="w-5 h-5" />
				</button>
				<button
					type="button"
						class="p-2 rounded-full hover:bg-primary/10 text-primary transition-all duration-200 active:scale-90"
					aria-label="Add emoji"
						title="Add emoji"
				>
					<Smile class="w-5 h-5" />
				</button>
				<button
					type="button"
						class="p-2 rounded-full hover:bg-primary/10 text-primary transition-all duration-200 active:scale-90"
						aria-label="Schedule"
						title="Schedule"
					>
						<Calendar class="w-5 h-5" />
					</button>
					<button
						type="button"
						class="p-2 rounded-full hover:bg-primary/10 text-primary transition-all duration-200 active:scale-90"
					aria-label="Add location"
						title="Add location"
				>
					<MapPin class="w-5 h-5" />
				</button>
			</div>

				<!-- Right side: counter and submit -->
			<div class="flex items-center gap-3">
					<!-- Character counter -->
				{#if charCount > 0}
						<div
							class="flex items-center gap-2"
							in:fade={{ duration: 150 }}
						>
							<!-- Circular progress -->
							<svg class="w-6 h-6 -rotate-90" viewBox="0 0 22 22">
								<!-- Background circle -->
							<circle
								r="9"
									cx="11"
									cy="11"
								fill="transparent"
								stroke="currentColor"
								stroke-width="2"
								class="text-border"
							/>
								<!-- Progress circle -->
							<circle
								r="9"
									cx="11"
									cy="11"
								fill="transparent"
								stroke="currentColor"
								stroke-width="2"
									stroke-linecap="round"
									stroke-dasharray={circumference}
									stroke-dashoffset={strokeDashoffset}
									class={clsx('transition-all duration-150', charCountColor)}
							/>
						</svg>

							<!-- Remaining count (show when near limit) -->
							{#if isNearLimit}
								<span
									class={clsx(
										'text-sm font-medium tabular-nums transition-colors',
										charCountColor
									)}
									in:fly={{ x: -10, duration: 150 }}
								>
								{maxLength - charCount}
							</span>
						{/if}
					</div>
				{/if}

					<!-- Divider -->
					{#if charCount > 0 && (replyToId || true)}
						<div class="w-px h-6 bg-border"></div>
					{/if}

					<!-- Cancel button (only for replies) -->
				{#if replyToId}
					<button
						type="button"
							class="p-1.5 rounded-full hover:bg-surface-hover text-text-secondary transition-all duration-200 active:scale-90"
						on:click={handleCancel}
						aria-label="Cancel"
					>
						<X class="w-4 h-4" />
					</button>
				{/if}

					<!-- Submit button -->
				<Button
					variant="primary"
						size="sm"
					disabled={!canSubmit}
					loading={isSubmitting}
					on:click={handleSubmit}
				>
					{replyToId ? 'Reply' : 'Post'}
				</Button>
			</div>
		</div>
		{/if}

		<!-- Keyboard shortcut hint -->
		{#if isFocused && canSubmit}
			<p
				class="text-xs text-text-muted mt-2"
				in:fade={{ duration: 200, delay: 300 }}
			>
				Press <kbd class="px-1.5 py-0.5 rounded bg-surface-hover text-text-secondary font-mono text-xs">⌘</kbd>
				+ <kbd class="px-1.5 py-0.5 rounded bg-surface-hover text-text-secondary font-mono text-xs">Enter</kbd>
				to post
			</p>
		{/if}
	</div>
</div>
