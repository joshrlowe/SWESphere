<script lang="ts">
	import { onMount } from 'svelte';
	import { createQuery, createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
	import { formatDistanceToNow } from 'date-fns';
	import { fly, fade, scale } from 'svelte/transition';
	import {
		Heart,
		Repeat2,
		MessageCircle,
		UserPlus,
		AtSign,
		BadgeCheck,
		Bell,
		CheckCheck,
		Settings
	} from 'lucide-svelte';
	import { clsx } from 'clsx';
	import { Avatar, Button, Spinner } from '$lib/components/ui';
	import { api } from '$lib/api/client';
	import { toast } from 'svelte-sonner';
	import type { Notification, NotificationType } from '$lib/types';

	interface NotificationsResponse {
		items: Notification[];
		total: number;
		page: number;
		per_page: number;
		has_next: boolean;
		unread_count: number;
	}

	const queryClient = useQueryClient();

	// Tabs
	type Tab = 'all' | 'mentions';
	let activeTab: Tab = 'all';

	// Notifications query
	const notificationsQuery = createQuery({
		queryKey: ['notifications', activeTab],
		queryFn: async () => {
			const params = activeTab === 'mentions' ? '?type=mentioned' : '';
			return api.get<NotificationsResponse>(`/notifications${params}`);
		}
	});

	$: notifications = $notificationsQuery.data?.items ?? [];
	$: unreadCount = $notificationsQuery.data?.unread_count ?? 0;
	$: isLoading = $notificationsQuery.isLoading;

	// Icon and color mappings
	const notificationConfig: Record<
		NotificationType,
		{ icon: typeof Heart; color: string; bgColor: string }
	> = {
		new_follower: { icon: UserPlus, color: 'text-primary', bgColor: 'bg-primary/10' },
		post_liked: { icon: Heart, color: 'text-error', bgColor: 'bg-error/10' },
		post_commented: { icon: MessageCircle, color: 'text-primary', bgColor: 'bg-primary/10' },
		post_reposted: { icon: Repeat2, color: 'text-success', bgColor: 'bg-success/10' },
		mentioned: { icon: AtSign, color: 'text-primary', bgColor: 'bg-primary/10' },
		reply: { icon: MessageCircle, color: 'text-primary', bgColor: 'bg-primary/10' },
		system: { icon: Bell, color: 'text-primary', bgColor: 'bg-primary/10' }
	};

	function getConfig(type: NotificationType) {
		return notificationConfig[type] || notificationConfig.system;
	}

	function getNotificationLink(notification: Notification): string {
		const data = notification.data as Record<string, unknown>;

		switch (notification.type) {
			case 'new_follower':
				return notification.actor ? `/profile/${notification.actor.username}` : '/notifications';
			case 'post_liked':
			case 'post_commented':
			case 'post_reposted':
			case 'mentioned':
			case 'reply':
				return data?.post_id ? `/post/${data.post_id}` : '/notifications';
			default:
				return '/notifications';
		}
	}

	async function markAsRead(notificationId: number) {
		try {
			await api.post(`/notifications/${notificationId}/read`);
			$notificationsQuery.refetch();
			// Also invalidate the unread count
			queryClient.invalidateQueries({ queryKey: ['notifications', 'unread-count'] });
		} catch {
			// Silently fail
		}
	}

	async function markAllAsRead() {
		try {
			await api.post('/notifications/read-all');
			toast.success('All notifications marked as read');
			$notificationsQuery.refetch();
			queryClient.invalidateQueries({ queryKey: ['notifications', 'unread-count'] });
		} catch {
			toast.error('Failed to mark notifications as read');
		}
	}

	function handleNotificationClick(notification: Notification) {
		if (!notification.read) {
			markAsRead(notification.id);
		}
	}

	// Mark visible unread as read when viewing
	onMount(() => {
		// Optional: auto-mark as read after viewing for a few seconds
		const timer = setTimeout(() => {
			const unreadIds = notifications.filter((n) => !n.read).map((n) => n.id);
			// Could batch mark as read here
		}, 3000);

		return () => clearTimeout(timer);
	});
</script>

<svelte:head>
	<title>Notifications | SWESphere</title>
</svelte:head>

<div>
	<!-- Header -->
	<header class="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b border-border">
		<div class="flex items-center justify-between px-4 py-3">
			<h1 class="text-xl font-bold">Notifications</h1>
			<div class="flex items-center gap-2">
				<Button
					variant="ghost"
					size="sm"
					on:click={markAllAsRead}
					disabled={unreadCount === 0}
					aria-label="Mark all as read"
				>
					<CheckCheck class="w-4 h-4" />
					<span class="hidden sm:inline">Mark all as read</span>
				</Button>
				<a
					href="/settings/notifications"
					class="p-2 rounded-full hover:bg-surface-hover transition-colors"
					aria-label="Notification settings"
				>
					<Settings class="w-5 h-5 text-text-secondary" />
				</a>
			</div>
		</div>

		<!-- Tabs -->
		<div class="flex">
			{#each [
				{ id: 'all', label: 'All' },
				{ id: 'mentions', label: 'Mentions' }
			] as tab}
				<button
					type="button"
					class={clsx(
						'flex-1 py-4 text-center font-medium transition-colors relative',
						activeTab === tab.id
							? 'text-text'
							: 'text-text-secondary hover:bg-surface-hover hover:text-text'
					)}
					on:click={() => (activeTab = tab.id)}
				>
					{tab.label}
					{#if activeTab === tab.id}
						<span
							class="absolute bottom-0 left-1/2 -translate-x-1/2 w-14 h-1 bg-primary rounded-full"
							in:fade={{ duration: 150 }}
						></span>
					{/if}
				</button>
			{/each}
		</div>
	</header>

	<!-- Content -->
	{#if isLoading}
		<div class="flex justify-center py-16">
			<Spinner size="lg" />
		</div>
	{:else if notifications.length === 0}
		<!-- Empty State -->
		<div class="flex flex-col items-center justify-center py-20 px-4 text-center">
			<div
				class="w-20 h-20 rounded-full bg-surface flex items-center justify-center mb-6"
				in:scale={{ duration: 300, delay: 100 }}
			>
				<Bell class="w-10 h-10 text-text-muted" />
			</div>
			<h2 class="text-2xl font-bold mb-2" in:fly={{ y: 10, duration: 300, delay: 150 }}>
				Nothing here yet
			</h2>
			<p
				class="text-text-secondary max-w-xs"
				in:fly={{ y: 10, duration: 300, delay: 200 }}
			>
				{activeTab === 'mentions'
					? "When someone mentions you, you'll see it here."
					: "When someone interacts with your posts, you'll see it here."}
			</p>
		</div>
	{:else}
		<!-- Notifications List -->
		<div class="divide-y divide-border">
			{#each notifications as notification, i (notification.id)}
				{@const config = getConfig(notification.type)}
				<a
					href={getNotificationLink(notification)}
					class={clsx(
						'flex gap-3 p-4 transition-all duration-200',
						'hover:bg-surface-hover',
						!notification.read && 'bg-primary/5'
					)}
					on:click={() => handleNotificationClick(notification)}
					in:fly={{ y: 20, duration: 300, delay: i * 30 }}
				>
					<!-- Icon -->
					<div class={clsx('p-2 rounded-full mt-0.5', config.bgColor)}>
						<svelte:component this={config.icon} class={clsx('w-5 h-5', config.color)} />
					</div>

					<!-- Content -->
					<div class="flex-1 min-w-0">
						<!-- Actor avatar row -->
						{#if notification.actor}
							<div class="flex items-center gap-2 mb-2">
								<Avatar
									src={notification.actor.avatar_url}
									alt={notification.actor.username}
									size="sm"
								/>
								<div class="flex items-center gap-1 min-w-0">
									<span class="font-bold truncate">
										{notification.actor.display_name || notification.actor.username}
									</span>
									{#if notification.actor.is_verified}
										<BadgeCheck class="w-4 h-4 text-primary flex-shrink-0" />
									{/if}
								</div>
							</div>
						{/if}

						<!-- Message -->
						<p class="text-text leading-snug">{notification.message}</p>

						<!-- Preview (for post interactions) -->
						{#if notification.data?.post_preview}
							<p class="text-text-secondary text-sm mt-1.5 line-clamp-2">
								{notification.data.post_preview}
							</p>
						{/if}

						<!-- Timestamp -->
						<p class="text-sm text-text-secondary mt-2">
							{formatDistanceToNow(new Date(notification.created_at), { addSuffix: true })}
						</p>
					</div>

					<!-- Unread indicator -->
					{#if !notification.read}
						<div class="flex-shrink-0 mt-2">
							<span class="w-2 h-2 rounded-full bg-primary block"></span>
						</div>
					{/if}
				</a>
			{/each}
		</div>

		<!-- Load more -->
		<div class="py-8 flex justify-center">
			<p class="text-text-secondary text-sm">You're all caught up!</p>
		</div>
	{/if}
</div>

<!-- Mobile bottom nav spacer -->
<div class="h-20 md:hidden"></div>
