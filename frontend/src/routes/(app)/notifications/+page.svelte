<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';
	import { formatDistanceToNow } from 'date-fns';
	import { Heart, Repeat2, MessageCircle, UserPlus, AtSign, BadgeCheck } from 'lucide-svelte';
	import { clsx } from 'clsx';
	import { Avatar, Spinner } from '$lib/components/ui';
	import { api } from '$lib/api/client';
	import type { Notification } from '$lib/types';

	interface NotificationsResponse {
		items: Notification[];
		total: number;
		unread_count: number;
	}

	const notificationsQuery = createQuery({
		queryKey: ['notifications'],
		queryFn: async () => {
			return api.get<NotificationsResponse>('/notifications');
		}
	});

	$: notifications = $notificationsQuery.data?.items ?? [];
	$: isLoading = $notificationsQuery.isLoading;

	const iconMap = {
		new_follower: UserPlus,
		post_liked: Heart,
		post_commented: MessageCircle,
		post_reposted: Repeat2,
		mentioned: AtSign,
		reply: MessageCircle,
		system: BadgeCheck
	};

	const colorMap = {
		new_follower: 'text-primary',
		post_liked: 'text-error',
		post_commented: 'text-primary',
		post_reposted: 'text-success',
		mentioned: 'text-primary',
		reply: 'text-primary',
		system: 'text-primary'
	};

	function getIcon(type: Notification['type']) {
		return iconMap[type] || BadgeCheck;
	}

	function getColor(type: Notification['type']) {
		return colorMap[type] || 'text-primary';
	}
</script>

<svelte:head>
	<title>Notifications | SWESphere</title>
</svelte:head>

<div>
	<!-- Header -->
	<header class="sticky top-0 z-10 bg-background/80 backdrop-blur-sm border-b border-border">
		<div class="flex items-center justify-between px-4 py-3">
			<h1 class="text-xl font-bold">Notifications</h1>
			<button type="button" class="text-primary text-sm hover:underline">
				Mark all as read
			</button>
		</div>

		<!-- Tabs -->
		<div class="flex border-b border-border">
			<button class="flex-1 py-4 text-center font-bold relative">
				All
				<span class="absolute bottom-0 left-1/2 -translate-x-1/2 w-10 h-1 bg-primary rounded-full"></span>
			</button>
			<button class="flex-1 py-4 text-center text-text-secondary hover:bg-surface-hover transition-colors">
				Mentions
			</button>
		</div>
	</header>

	<!-- Notifications List -->
	{#if isLoading}
		<div class="flex justify-center py-12">
			<Spinner size="lg" />
		</div>
	{:else if notifications.length === 0}
		<div class="flex flex-col items-center justify-center py-16 px-4 text-center">
			<div class="w-16 h-16 rounded-full bg-surface flex items-center justify-center mb-4">
				<Bell class="w-8 h-8 text-text-muted" />
			</div>
			<h2 class="text-xl font-bold mb-2">Nothing to see here — yet</h2>
			<p class="text-text-secondary max-w-sm">
				When someone interacts with your posts, you'll see it here.
			</p>
		</div>
	{:else}
		<div class="divide-y divide-border">
			{#each notifications as notification (notification.id)}
				<a
					href={notification.data?.post_id ? `/post/${notification.data.post_id}` : '/notifications'}
					class={clsx(
						'flex gap-3 p-4 hover:bg-surface-hover transition-colors',
						!notification.read && 'bg-primary-light/30'
					)}
				>
					<div class={clsx('mt-1', getColor(notification.type))}>
						<svelte:component this={getIcon(notification.type)} class="w-6 h-6" />
					</div>

					<div class="flex-1 min-w-0">
						{#if notification.actor}
							<div class="flex items-center gap-2 mb-1">
								<Avatar
									src={notification.actor.avatar_url}
									alt={notification.actor.username}
									size="sm"
								/>
								<span class="font-bold truncate">
									{notification.actor.display_name || notification.actor.username}
								</span>
								{#if notification.actor.is_verified}
									<BadgeCheck class="w-4 h-4 text-primary flex-shrink-0" />
								{/if}
							</div>
						{/if}

						<p class="text-text">{notification.message}</p>

						<p class="text-sm text-text-secondary mt-1">
							{formatDistanceToNow(new Date(notification.created_at), { addSuffix: true })}
						</p>
					</div>
				</a>
			{/each}
		</div>
	{/if}
</div>

<script context="module">
	import { Bell } from 'lucide-svelte';
</script>

