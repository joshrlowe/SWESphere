<script lang="ts">
	import { goto } from '$app/navigation';
	import { Button, Input } from '$lib/components/ui';
	import { auth, isAuthenticated, authError, isAuthLoading } from '$lib/stores';

	let email = '';
	let password = '';
	let error = '';

	$: if ($isAuthenticated) {
		goto('/feed');
	}

	async function handleSubmit() {
		error = '';

		if (!email || !password) {
			error = 'Please fill in all fields';
			return;
		}

		try {
			await auth.login({ email, password });
		} catch (err) {
			error = err instanceof Error ? err.message : 'Login failed';
		}
	}
</script>

<svelte:head>
	<title>Login | SWESphere</title>
</svelte:head>

<div class="min-h-screen flex items-center justify-center px-4 bg-background">
	<div class="w-full max-w-md">
		<!-- Logo -->
		<div class="text-center mb-8">
			<h1 class="text-4xl font-bold text-primary mb-2">SWESphere</h1>
			<p class="text-text-secondary">Welcome back</p>
		</div>

		<!-- Form -->
		<form on:submit|preventDefault={handleSubmit} class="space-y-4">
			<Input
				type="email"
				label="Email"
				placeholder="you@example.com"
				bind:value={email}
				required
				disabled={$isAuthLoading}
			/>

			<Input
				type="password"
				label="Password"
				placeholder="••••••••"
				bind:value={password}
				required
				disabled={$isAuthLoading}
			/>

			{#if error || $authError}
				<div class="p-3 rounded-lg bg-error/10 border border-error text-error text-sm">
					{error || $authError}
				</div>
			{/if}

			<Button type="submit" fullWidth loading={$isAuthLoading}>
				Log in
			</Button>
		</form>

		<!-- Links -->
		<div class="mt-6 text-center space-y-2">
			<a href="/auth/forgot-password" class="text-sm text-primary hover:underline">
				Forgot password?
			</a>
			<p class="text-text-secondary">
				Don't have an account?
				<a href="/auth/register" class="text-primary hover:underline">Sign up</a>
			</p>
		</div>
	</div>
</div>

