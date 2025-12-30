<script lang="ts">
	import { clsx } from 'clsx';
	import { createEventDispatcher } from 'svelte';

	export let value: string = '';
	export let type: 'text' | 'email' | 'password' | 'search' | 'url' | 'tel' = 'text';
	export let placeholder: string = '';
	export let label: string = '';
	export let error: string = '';
	export let helper: string = '';
	export let disabled: boolean = false;
	export let required: boolean = false;
	export let maxlength: number | undefined = undefined;
	export let id: string = '';

	const dispatch = createEventDispatcher<{
		input: string;
		change: string;
		blur: FocusEvent;
		focus: FocusEvent;
	}>();

	function handleInput(event: Event) {
		const target = event.target as HTMLInputElement;
		value = target.value;
		dispatch('input', value);
	}

	function handleChange(event: Event) {
		const target = event.target as HTMLInputElement;
		dispatch('change', target.value);
	}

	$: inputId = id || `input-${Math.random().toString(36).slice(2, 9)}`;
	$: inputClasses = clsx(
		'w-full px-4 py-3 bg-transparent border rounded-lg text-text',
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

	<input
		{type}
		id={inputId}
		class={inputClasses}
		{placeholder}
		{disabled}
		{required}
		{maxlength}
		{value}
		on:input={handleInput}
		on:change={handleChange}
		on:blur
		on:focus
		on:keydown
		on:keyup
		{...$$restProps}
	/>

	{#if error}
		<p class="text-xs text-error mt-1">{error}</p>
	{:else if helper}
		<p class="text-xs text-text-muted mt-1">{helper}</p>
	{/if}

	{#if maxlength && value}
		<p class="text-xs text-text-muted mt-1 text-right">
			{value.length}/{maxlength}
		</p>
	{/if}
</div>

