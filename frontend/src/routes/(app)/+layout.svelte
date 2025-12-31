<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { fly, fade } from 'svelte/transition';
	import {
		Home,
		Search,
		Bell,
		User,
		Settings,
		LogOut,
		PenSquare,
		Hash,
		MoreHorizontal
	} from 'lucide-svelte';
	import { clsx } from 'clsx';
	import { Avatar, Button, Modal } from '$lib/components/ui';
	import { PostComposer } from '$lib/components/post';
	import { NotificationBell } from '$lib/components/notification';
	import { auth, currentUser, isAuthenticated, isAuthInitialized } from '$lib/stores';
	import { createQuery } from '@tanstack/svelte-query';
	import { api } from '$lib/api/client';

	let showComposeModal = false;
	let showUserMenu = false;

	// Redirect to login if not authenticated
	$: if ($isAuthInitialized && !$isAuthenticated) {
		goto('/auth/login');
	}

	$: currentPath = $page.url.pathname;

	// Fetch unread notification count
	const notificationCountQuery = createQuery({
		queryKey: ['notifications', 'unread-count'],
		queryFn: async () => {
			const res = await api.get<{ unread_count: number }>('/notifications/unread-count');
			return res.unread_count;
		},
		refetchInterval: 30000 // Refetch every 30 seconds
	});

	$: unreadCount = $notificationCountQuery.data ?? 0;

	const navItems = [
		{ href: '/feed', label: 'Home', icon: Home },
		{ href: '/explore', label: 'Explore', icon: Hash },
		{ href: '/notifications', label: 'Notifications', icon: Bell, showBadge: true }
	];

	function isActive(href: string): boolean {
		if (href === '/feed') return currentPath === '/feed';
		return currentPath === href || currentPath.startsWith(href + '/');
	}

	function handleLogout() {
		auth.logout();
		showUserMenu = false;
	}

	function handleComposeSubmit() {
		showComposeModal = false;
	}
</script>

<svelte:head>
	<title>SWESphere</title>
</svelte:head>

<div class="min-h-screen flex bg-background">
	<!-- Left Sidebar -->
	<aside
		class="hidden md:flex flex-col w-20 xl:w-72 border-r border-border sticky top-0 h-screen"
	>
		<div class="flex-1 flex flex-col p-2 xl:p-4">
			<!-- Logo -->
			<a
				href="/feed"
				class="p-3 mb-2 rounded-full hover:bg-surface-hover transition-colors inline-flex items-center"
			>
				<span class="text-2xl font-bold text-primary xl:block hidden">SWESphere</span>
				<span class="text-2xl font-bold text-primary xl:hidden">S</span>
			</a>

			<!-- Navigation -->
			<nav class="flex-1 space-y-1">
				{#each navItems as item}
					<a
						href={item.href}
						class={clsx(
							'flex items-center gap-4 px-4 py-3 rounded-full text-xl transition-all duration-200',
							'hover:bg-surface-hover active:scale-95',
							isActive(item.href) ? 'font-bold text-text' : 'text-text'
						)}
					>
						{#if item.showBadge && unreadCount > 0}
							<div class="relative">
								<svelte:component this={item.icon} class="w-7 h-7" />
								<span
									class="absolute -top-1 -right-1 min-w-[18px] h-[18px] bg-primary text-white text-[10px] font-bold rounded-full flex items-center justify-center px-1"
								>
									{unreadCount > 99 ? '99+' : unreadCount}
								</span>
							</div>
						{:else}
							<svelte:component this={item.icon} class="w-7 h-7" />
						{/if}
						<span class="hidden xl:block">{item.label}</span>
					</a>
				{/each}

				{#if $currentUser}
					<a
						href={`/profile/${$currentUser.username}`}
						class={clsx(
							'flex items-center gap-4 px-4 py-3 rounded-full text-xl transition-all duration-200',
							'hover:bg-surface-hover active:scale-95',
							currentPath.includes(`/profile/${$currentUser.username}`)
								? 'font-bold text-text'
								: 'text-text'
						)}
					>
						<User class="w-7 h-7" />
						<span class="hidden xl:block">Profile</span>
					</a>
				{/if}

				<a
					href="/settings"
					class={clsx(
						'flex items-center gap-4 px-4 py-3 rounded-full text-xl transition-all duration-200',
						'hover:bg-surface-hover active:scale-95',
						isActive('/settings') ? 'font-bold text-text' : 'text-text'
					)}
				>
					<Settings class="w-7 h-7" />
					<span class="hidden xl:block">Settings</span>
				</a>
			</nav>

			<!-- Post Button -->
			<Button
				variant="primary"
				size="lg"
				fullWidth
				class="mt-4 hidden xl:flex"
				on:click={() => (showComposeModal = true)}
			>
				Post
			</Button>

			<button
				type="button"
				class="xl:hidden flex items-center justify-center w-14 h-14 mx-auto mt-4 bg-primary rounded-full hover:bg-primary-hover transition-all duration-200 active:scale-95 shadow-lg"
				on:click={() => (showComposeModal = true)}
				aria-label="New post"
			>
				<PenSquare class="w-6 h-6 text-white" />
			</button>
		</div>

		<!-- User Menu -->
		{#if $currentUser}
			<div class="p-2 xl:p-4 border-t border-border relative">
				<button
					type="button"
					class="w-full flex items-center gap-3 p-3 rounded-full hover:bg-surface-hover transition-colors"
					on:click={() => (showUserMenu = !showUserMenu)}
				>
					<Avatar user={$currentUser} size="md" />
					<div class="hidden xl:block flex-1 min-w-0 text-left">
						<p class="font-bold text-text truncate">
							{$currentUser.display_name || $currentUser.username}
						</p>
						<p class="text-sm text-text-secondary truncate">@{$currentUser.username}</p>
					</div>
					<MoreHorizontal class="w-5 h-5 text-text-secondary hidden xl:block" />
				</button>

				<!-- User Dropdown Menu -->
				{#if showUserMenu}
					<div
						class="absolute bottom-full left-2 right-2 mb-2 bg-surface border border-border rounded-xl shadow-xl overflow-hidden z-50"
						in:fly={{ y: 10, duration: 150 }}
						out:fade={{ duration: 100 }}
					>
						<a
							href={`/profile/${$currentUser.username}`}
							class="flex items-center gap-3 px-4 py-3 hover:bg-surface-hover transition-colors"
							on:click={() => (showUserMenu = false)}
						>
							<User class="w-5 h-5" />
							View profile
						</a>
						<a
							href="/settings"
							class="flex items-center gap-3 px-4 py-3 hover:bg-surface-hover transition-colors"
							on:click={() => (showUserMenu = false)}
						>
							<Settings class="w-5 h-5" />
							Settings
						</a>
						<button
							type="button"
							class="w-full flex items-center gap-3 px-4 py-3 hover:bg-surface-hover transition-colors text-left text-error"
							on:click={handleLogout}
						>
							<LogOut class="w-5 h-5" />
							Log out @{$currentUser.username}
						</button>
					</div>
				{/if}
			</div>
		{/if}
	</aside>

	<!-- Main Content -->
	<main class="flex-1 min-w-0 max-w-[600px] border-r border-border">
		<slot />
	</main>

	<!-- Right Sidebar (Trends, Who to follow) -->
	<aside class="hidden lg:block w-80 xl:w-[350px] p-4 sticky top-0 h-screen overflow-y-auto">
		<!-- Search -->
		<div class="relative mb-4">
			<Search class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
			<input
				type="search"
				placeholder="Search"
				class="w-full pl-12 pr-4 py-3 bg-surface rounded-full text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary transition-all duration-200"
			/>
		</div>

		<!-- Trends -->
		<div class="bg-surface rounded-2xl overflow-hidden mb-4">
			<h2 class="text-xl font-bold px-4 py-3">Trends for you</h2>
			<div>
				{#each Array(5) as _, i}
					<a
						href="/search?q=trending{i + 1}"
						class="block px-4 py-3 hover:bg-surface-hover transition-colors"
					>
						<p class="text-xs text-text-secondary">Trending in Tech</p>
						<p class="font-bold">#SvelteKit</p>
						<p class="text-xs text-text-secondary">{(i + 1) * 1234} posts</p>
					</a>
				{/each}
			</div>
			<a
				href="/explore"
				class="block px-4 py-3 text-primary hover:bg-surface-hover transition-colors"
			>
				Show more
			</a>
		</div>

		<!-- Who to follow -->
		<div class="bg-surface rounded-2xl overflow-hidden">
			<h2 class="text-xl font-bold px-4 py-3">Who to follow</h2>
			<div class="px-4 py-8 text-center text-text-secondary text-sm">
				<p>Suggestions will appear here</p>
			</div>
		</div>

		<!-- Footer -->
		<footer class="mt-4 px-4 text-xs text-text-muted flex flex-wrap gap-x-2 gap-y-1">
			<a href="/terms" class="hover:underline">Terms of Service</a>
			<a href="/privacy" class="hover:underline">Privacy Policy</a>
			<a href="/about" class="hover:underline">About</a>
			<span class="w-full mt-1">© 2024 SWESphere</span>
		</footer>
	</aside>

	<!-- Mobile Bottom Navigation -->
	<nav
		class="md:hidden fixed bottom-0 left-0 right-0 bg-background/95 backdrop-blur-sm border-t border-border z-50"
		style="padding-bottom: env(safe-area-inset-bottom)"
	>
		<div class="flex items-center justify-around py-2">
			<a
				href="/feed"
				class={clsx(
					'p-3 rounded-full transition-colors',
					isActive('/feed') ? 'text-text' : 'text-text-secondary'
				)}
			>
				<Home class="w-6 h-6" />
			</a>
			<a
				href="/explore"
				class={clsx(
					'p-3 rounded-full transition-colors',
					isActive('/explore') ? 'text-text' : 'text-text-secondary'
				)}
			>
				<Search class="w-6 h-6" />
			</a>
			<button
				type="button"
				class="p-3 bg-primary rounded-full text-white shadow-lg active:scale-95 transition-transform"
				on:click={() => (showComposeModal = true)}
			>
				<PenSquare class="w-5 h-5" />
			</button>
			<a
				href="/notifications"
				class={clsx(
					'p-3 rounded-full transition-colors relative',
					isActive('/notifications') ? 'text-text' : 'text-text-secondary'
				)}
			>
				<Bell class="w-6 h-6" />
				{#if unreadCount > 0}
					<span
						class="absolute top-1 right-1 min-w-[16px] h-[16px] bg-primary text-white text-[9px] font-bold rounded-full flex items-center justify-center"
					>
						{unreadCount > 9 ? '9+' : unreadCount}
					</span>
				{/if}
			</a>
			{#if $currentUser}
				<a
					href={`/profile/${$currentUser.username}`}
					class={clsx(
						'p-1 rounded-full transition-colors',
						currentPath.includes(`/profile/${$currentUser.username}`) && 'ring-2 ring-primary'
					)}
				>
					<Avatar user={$currentUser} size="sm" />
				</a>
			{/if}
		</div>
	</nav>
</div>

<!-- Close user menu on outside click -->
<svelte:window on:click={() => (showUserMenu = false)} />

<!-- Compose Modal -->
<Modal bind:open={showComposeModal} title="Compose post">
	<PostComposer autofocus on:submit={handleComposeSubmit} on:cancel={() => (showComposeModal = false)} />
</Modal>
