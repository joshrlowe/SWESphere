<script lang="ts">
	import { clsx } from 'clsx';
	import { createEventDispatcher } from 'svelte';

	export let value: string = '';
	export let placeholder: string = '';
	export let label: string = '';
	export let error: string = '';
	export let helper: string = '';
	export let disabled: boolean = false;
	export let required: boolean = false;
	export let maxlength: number | undefined = undefined;
	export let rows: number = 4;
	export let autoresize: boolean = false;
	export let id: string = '';

	let textarea: HTMLTextAreaElement;

	const dispatch = createEventDispatcher<{
		input: string;
		change: string;
		blur: FocusEvent;
		focus: FocusEvent;
	}>();

	function handleInput(event: Event) {
		const target = event.target as HTMLTextAreaElement;
		value = target.value;
		dispatch('input', value);

		if (autoresize && textarea) {
			textarea.style.height = 'auto';
			textarea.style.height = `${textarea.scrollHeight}px`;
		}
	}

	function handleChange(event: Event) {
		const target = event.target as HTMLTextAreaElement;
		dispatch('change', target.value);
	}

	$: inputId = id || `textarea-${Math.random().toString(36).slice(2, 9)}`;
	$: inputClasses = clsx(
		'w-full px-4 py-3 bg-transparent border rounded-lg text-text resize-none',
		'placeholder:text-text-muted',
		'focus:ring-1 transition-colors duration-200',
		error
			? 'border-error focus:border-error focus:ring-error'
			: 'border-border focus:border-primary focus:ring-primary',
		disabled && 'opacity-50 cursor-not-allowed',
		$$props.class
	);
</script>

<div class="w-full">
	{#if label}
		<label for={inputId} class="block text-sm font-medium text-text-secondary mb-1.5">
			{label}
			{#if required}
				<span class="text-error">*</span>
			{/if}
		</label>
	{/if}

	<textarea
		bind:this={textarea}
		id={inputId}
		class={inputClasses}
		{placeholder}
		{disabled}
		{required}
		{maxlength}
		{rows}
		{value}
		on:input={handleInput}
		on:change={handleChange}
		on:blur
		on:focus
		on:keydown
		on:keyup
		{...$$restProps}
	></textarea>

	<div class="flex justify-between mt-1">
		{#if error}
			<p class="text-xs text-error">{error}</p>
		{:else if helper}
			<p class="text-xs text-text-muted">{helper}</p>
		{:else}
			<span></span>
		{/if}

		{#if maxlength}
			<p
				class={clsx(
					'text-xs',
					value.length > maxlength ? 'text-error' : 'text-text-muted'
				)}
			>
				{value.length}/{maxlength}
			</p>
		{/if}
	</div>
</div>

