<script lang="ts">
	import { goto } from '$app/navigation';
	import { fly, fade } from 'svelte/transition';
	import { Eye, EyeOff, AlertCircle, Loader2 } from 'lucide-svelte';
	import { Button } from '$lib/components/ui';
	import { auth, isAuthenticated, authError, isAuthLoading } from '$lib/stores';

	let email = '';
	let password = '';
	let showPassword = false;
	let error = '';
	let touched = { email: false, password: false };

	// Redirect if already authenticated
	$: if ($isAuthenticated) {
		goto('/feed');
	}

	// Validation
	$: emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
	$: emailError = touched.email && !email ? 'Email is required' : touched.email && !emailValid ? 'Enter a valid email' : '';
	$: passwordError = touched.password && !password ? 'Password is required' : '';
	$: formValid = email && password && emailValid;

	async function handleSubmit() {
		touched = { email: true, password: true };
		error = '';

		if (!formValid) return;

		try {
			await auth.login({ email, password });
		} catch (err) {
			error = err instanceof Error ? err.message : 'Login failed. Please try again.';
		}
	}

	function togglePassword() {
		showPassword = !showPassword;
	}
</script>

<svelte:head>
	<title>Log in | SWESphere</title>
</svelte:head>

<div class="min-h-screen flex bg-background">
	<!-- Left side - Branding (hidden on mobile) -->
	<div class="hidden lg:flex lg:w-1/2 items-center justify-center bg-gradient-to-br from-primary/20 via-background to-background p-12">
		<div class="max-w-md">
			<h1 class="text-6xl font-bold text-primary mb-6">SWESphere</h1>
			<p class="text-2xl text-text-secondary leading-relaxed">
				Connect with developers, share your thoughts, and stay updated with the tech community.
			</p>
		</div>
	</div>

	<!-- Right side - Login form -->
	<div class="flex-1 flex items-center justify-center px-4 py-12">
		<div class="w-full max-w-md" in:fly={{ y: 20, duration: 300, delay: 100 }}>
			<!-- Mobile Logo -->
			<div class="lg:hidden text-center mb-8">
				<h1 class="text-4xl font-bold text-primary mb-2">SWESphere</h1>
			</div>

			<!-- Heading -->
			<div class="mb-8">
				<h2 class="text-3xl font-bold text-text mb-2">Welcome back</h2>
				<p class="text-text-secondary">Sign in to your account to continue</p>
			</div>

			<!-- Form -->
			<form on:submit|preventDefault={handleSubmit} class="space-y-5">
				<!-- Email Input -->
				<div>
					<label for="email" class="block text-sm font-medium text-text-secondary mb-2">
						Email address
					</label>
					<input
						id="email"
						type="email"
						placeholder="you@example.com"
						bind:value={email}
						on:blur={() => (touched.email = true)}
						disabled={$isAuthLoading}
						class="w-full px-4 py-3 bg-transparent border rounded-lg text-text placeholder:text-text-muted focus:ring-2 transition-all duration-200 {emailError ? 'border-error focus:border-error focus:ring-error/20' : 'border-border focus:border-primary focus:ring-primary/20'}"
					/>
					{#if emailError}
						<p class="text-xs text-error mt-1.5 flex items-center gap-1" in:fly={{ y: -5, duration: 150 }}>
							<AlertCircle class="w-3 h-3" />
							{emailError}
						</p>
					{/if}
				</div>

				<!-- Password Input -->
				<div>
					<label for="password" class="block text-sm font-medium text-text-secondary mb-2">
						Password
					</label>
					<div class="relative">
						<input
							id="password"
							type={showPassword ? 'text' : 'password'}
							placeholder="••••••••"
							bind:value={password}
							on:blur={() => (touched.password = true)}
							disabled={$isAuthLoading}
							class="w-full px-4 py-3 pr-12 bg-transparent border rounded-lg text-text placeholder:text-text-muted focus:ring-2 transition-all duration-200 {passwordError ? 'border-error focus:border-error focus:ring-error/20' : 'border-border focus:border-primary focus:ring-primary/20'}"
						/>
						<button
							type="button"
							class="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 rounded-full hover:bg-surface-hover text-text-secondary hover:text-text transition-colors"
							on:click={togglePassword}
							aria-label={showPassword ? 'Hide password' : 'Show password'}
						>
							{#if showPassword}
								<EyeOff class="w-5 h-5" />
							{:else}
								<Eye class="w-5 h-5" />
							{/if}
						</button>
					</div>
					{#if passwordError}
						<p class="text-xs text-error mt-1.5 flex items-center gap-1" in:fly={{ y: -5, duration: 150 }}>
							<AlertCircle class="w-3 h-3" />
							{passwordError}
						</p>
					{/if}
				</div>

				<!-- Forgot Password Link -->
				<div class="text-right">
					<a
						href="/auth/forgot-password"
						class="text-sm text-primary hover:underline transition-colors"
					>
						Forgot password?
					</a>
				</div>

				<!-- Error Message -->
				{#if error || $authError}
					<div
						class="p-4 rounded-lg bg-error/10 border border-error/30 flex items-start gap-3"
						in:fly={{ y: -10, duration: 200 }}
					>
						<AlertCircle class="w-5 h-5 text-error flex-shrink-0 mt-0.5" />
						<div>
							<p class="text-sm text-error font-medium">Unable to sign in</p>
							<p class="text-sm text-error/80 mt-1">{error || $authError}</p>
						</div>
					</div>
				{/if}

				<!-- Submit Button -->
				<Button
					type="submit"
					fullWidth
					size="lg"
					loading={$isAuthLoading}
					disabled={$isAuthLoading}
				>
					{#if $isAuthLoading}
						Signing in...
					{:else}
						Sign in
					{/if}
				</Button>
			</form>

			<!-- Divider -->
			<div class="flex items-center gap-4 my-8">
				<div class="flex-1 h-px bg-border"></div>
				<span class="text-sm text-text-muted">or</span>
				<div class="flex-1 h-px bg-border"></div>
			</div>

			<!-- Sign Up Link -->
			<p class="text-center text-text-secondary">
				Don't have an account?
				<a href="/auth/register" class="text-primary font-semibold hover:underline">
					Sign up
				</a>
			</p>
		</div>
	</div>
</div>
