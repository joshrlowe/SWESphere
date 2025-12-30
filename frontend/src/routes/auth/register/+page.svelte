<script lang="ts">
	import { goto } from '$app/navigation';
	import { Button, Input } from '$lib/components/ui';
	import { register } from '$lib/api/auth';
	import { auth, isAuthenticated } from '$lib/stores';
	import { toast } from 'svelte-sonner';

	let username = '';
	let email = '';
	let password = '';
	let confirmPassword = '';
	let isLoading = false;
	let error = '';

	$: if ($isAuthenticated) {
		goto('/feed');
	}

	$: passwordsMatch = password === confirmPassword || !confirmPassword;

	async function handleSubmit() {
		error = '';

		if (!username || !email || !password || !confirmPassword) {
			error = 'Please fill in all fields';
			return;
		}

		if (password !== confirmPassword) {
			error = 'Passwords do not match';
			return;
		}

		if (password.length < 8) {
			error = 'Password must be at least 8 characters';
			return;
		}

		isLoading = true;

		try {
			await register({ username, email, password });
			toast.success('Account created! Please log in.');
			goto('/auth/login');
		} catch (err) {
			error = err instanceof Error ? err.message : 'Registration failed';
		} finally {
			isLoading = false;
		}
	}
</script>

<svelte:head>
	<title>Sign Up | SWESphere</title>
</svelte:head>

<div class="min-h-screen flex items-center justify-center px-4 bg-background">
	<div class="w-full max-w-md">
		<!-- Logo -->
		<div class="text-center mb-8">
			<h1 class="text-4xl font-bold text-primary mb-2">SWESphere</h1>
			<p class="text-text-secondary">Create your account</p>
		</div>

		<!-- Form -->
		<form on:submit|preventDefault={handleSubmit} class="space-y-4">
			<Input
				type="text"
				label="Username"
				placeholder="johndoe"
				bind:value={username}
				required
				disabled={isLoading}
				maxlength={20}
				helper="Letters, numbers, and underscores only"
			/>

			<Input
				type="email"
				label="Email"
				placeholder="you@example.com"
				bind:value={email}
				required
				disabled={isLoading}
			/>

			<Input
				type="password"
				label="Password"
				placeholder="••••••••"
				bind:value={password}
				required
				disabled={isLoading}
				helper="At least 8 characters"
			/>

			<Input
				type="password"
				label="Confirm Password"
				placeholder="••••••••"
				bind:value={confirmPassword}
				required
				disabled={isLoading}
				error={!passwordsMatch ? 'Passwords do not match' : ''}
			/>

			{#if error}
				<div class="p-3 rounded-lg bg-error/10 border border-error text-error text-sm">
					{error}
				</div>
			{/if}

			<Button type="submit" fullWidth loading={isLoading}>
				Create account
			</Button>
		</form>

		<!-- Links -->
		<div class="mt-6 text-center">
			<p class="text-text-secondary">
				Already have an account?
				<a href="/auth/login" class="text-primary hover:underline">Log in</a>
			</p>
		</div>

		<!-- Terms -->
		<p class="mt-6 text-center text-xs text-text-muted">
			By signing up, you agree to our
			<a href="/terms" class="text-primary hover:underline">Terms of Service</a>
			and
			<a href="/privacy" class="text-primary hover:underline">Privacy Policy</a>.
		</p>
	</div>
</div>

