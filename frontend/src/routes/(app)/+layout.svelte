<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import {
		Home,
		Search,
		Bell,
		User,
		Settings,
		LogOut,
		PenSquare,
		Hash
	} from 'lucide-svelte';
	import { clsx } from 'clsx';
	import { Avatar, Button, Modal } from '$lib/components/ui';
	import { PostComposer } from '$lib/components/post';
	import { auth, currentUser, isAuthenticated, isAuthInitialized } from '$lib/stores';

	let showComposeModal = false;

	$: if ($isAuthInitialized && !$isAuthenticated) {
		goto('/auth/login');
	}

	$: currentPath = $page.url.pathname;

	const navItems = [
		{ href: '/feed', label: 'Home', icon: Home },
		{ href: '/explore', label: 'Explore', icon: Hash },
		{ href: '/search', label: 'Search', icon: Search },
		{ href: '/notifications', label: 'Notifications', icon: Bell }
	];

	function isActive(href: string): boolean {
		return currentPath === href || currentPath.startsWith(href + '/');
	}

	function handleLogout() {
		auth.logout();
	}

	function handleComposeSubmit() {
		showComposeModal = false;
	}
</script>

<svelte:head>
	<title>SWESphere</title>
</svelte:head>

<div class="min-h-screen flex bg-background">
	<!-- Sidebar -->
	<aside class="hidden md:flex flex-col w-20 xl:w-72 border-r border-border sticky top-0 h-screen">
		<div class="flex-1 flex flex-col p-2 xl:p-4">
			<!-- Logo -->
			<a href="/feed" class="p-3 mb-2">
				<span class="text-2xl font-bold text-primary xl:block hidden">SWESphere</span>
				<span class="text-2xl font-bold text-primary xl:hidden">S</span>
			</a>

			<!-- Navigation -->
			<nav class="flex-1 space-y-1">
				{#each navItems as item}
					<a
						href={item.href}
						class={clsx(
							'flex items-center gap-4 px-4 py-3 rounded-full text-xl transition-colors',
							isActive(item.href)
								? 'font-bold text-text'
								: 'text-text hover:bg-surface-hover'
						)}
					>
						<svelte:component this={item.icon} class="w-7 h-7" />
						<span class="hidden xl:block">{item.label}</span>
					</a>
				{/each}

				{#if $currentUser}
					<a
						href={`/profile/${$currentUser.username}`}
						class={clsx(
							'flex items-center gap-4 px-4 py-3 rounded-full text-xl transition-colors',
							currentPath.includes($currentUser.username)
								? 'font-bold text-text'
								: 'text-text hover:bg-surface-hover'
						)}
					>
						<User class="w-7 h-7" />
						<span class="hidden xl:block">Profile</span>
					</a>
				{/if}
			</nav>

			<!-- Post Button -->
			<Button
				variant="primary"
				size="lg"
				fullWidth
				class="mt-4 hidden xl:flex"
				on:click={() => (showComposeModal = true)}
			>
				<PenSquare class="w-5 h-5 xl:hidden" />
				<span>Post</span>
			</Button>

			<button
				type="button"
				class="xl:hidden flex items-center justify-center w-14 h-14 mx-auto mt-4 bg-primary rounded-full hover:bg-primary-hover transition-colors"
				on:click={() => (showComposeModal = true)}
				aria-label="New post"
			>
				<PenSquare class="w-6 h-6 text-white" />
			</button>
		</div>

		<!-- User Menu -->
		{#if $currentUser}
			<div class="p-2 xl:p-4 border-t border-border">
				<div class="flex items-center gap-3 p-3 rounded-full hover:bg-surface-hover transition-colors cursor-pointer">
					<Avatar user={$currentUser} size="md" />
					<div class="hidden xl:block flex-1 min-w-0">
						<p class="font-bold text-text truncate">
							{$currentUser.display_name || $currentUser.username}
						</p>
						<p class="text-sm text-text-secondary truncate">@{$currentUser.username}</p>
					</div>
					<button
						type="button"
						class="hidden xl:block p-2 hover:bg-surface-hover rounded-full"
						on:click={handleLogout}
						aria-label="Logout"
					>
						<LogOut class="w-5 h-5 text-text-secondary" />
					</button>
				</div>
			</div>
		{/if}
	</aside>

	<!-- Main Content -->
	<main class="flex-1 min-w-0 max-w-feed border-r border-border">
		<slot />
	</main>

	<!-- Right Sidebar (Trends, Who to follow) -->
	<aside class="hidden lg:block w-80 xl:w-88 p-4 sticky top-0 h-screen overflow-y-auto">
		<!-- Search -->
		<div class="relative mb-4">
			<Search class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
			<input
				type="search"
				placeholder="Search"
				class="w-full pl-12 pr-4 py-3 bg-surface rounded-full text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary"
			/>
		</div>

		<!-- Trends -->
		<div class="card mb-4">
			<h2 class="text-xl font-bold p-4 border-b border-border">Trends for you</h2>
			<div class="divide-y divide-border">
				{#each Array(3) as _, i}
					<a href="/search?q=trending{i + 1}" class="block p-4 hover:bg-surface-hover transition-colors">
						<p class="text-xs text-text-secondary">Trending</p>
						<p class="font-bold">#Trending{i + 1}</p>
						<p class="text-xs text-text-secondary">{(i + 1) * 1000} posts</p>
					</a>
				{/each}
			</div>
			<a href="/explore" class="block p-4 text-primary hover:bg-surface-hover transition-colors">
				Show more
			</a>
		</div>

		<!-- Who to follow -->
		<div class="card">
			<h2 class="text-xl font-bold p-4 border-b border-border">Who to follow</h2>
			<div class="p-4 text-text-secondary text-sm">
				Suggestions will appear here
			</div>
		</div>

		<!-- Footer -->
		<footer class="mt-4 px-4 text-xs text-text-muted">
			<a href="/terms" class="hover:underline">Terms</a> ·
			<a href="/privacy" class="hover:underline">Privacy</a> ·
			<a href="/about" class="hover:underline">About</a>
			<p class="mt-2">© 2024 SWESphere</p>
		</footer>
	</aside>

	<!-- Mobile Bottom Navigation -->
	<nav class="md:hidden fixed bottom-0 left-0 right-0 bg-background border-t border-border safe-area-bottom">
		<div class="flex items-center justify-around py-2">
			{#each navItems as item}
				<a
					href={item.href}
					class={clsx(
						'p-3 rounded-full',
						isActive(item.href) ? 'text-text' : 'text-text-secondary'
					)}
				>
					<svelte:component this={item.icon} class="w-6 h-6" />
				</a>
			{/each}
		</div>
	</nav>
</div>

<!-- Compose Modal -->
<Modal bind:open={showComposeModal} title="Compose">
	<PostComposer on:submit={handleComposeSubmit} on:cancel={() => (showComposeModal = false)} />
</Modal>

