<script lang="ts">
	import { BadgeCheck } from 'lucide-svelte';
	import { Avatar, Card } from '$lib/components/ui';
	import FollowButton from './FollowButton.svelte';
	import { getDisplayName, type User } from '$lib/types';
	import { currentUser } from '$lib/stores';

	export let user: User;
	export let showBio: boolean = true;
	export let showFollow: boolean = true;

	$: isCurrentUser = $currentUser?.id === user.id;
	$: displayName = getDisplayName(user);
</script>

<Card hover class="p-4">
	<a href={`/${user.username}`} class="flex items-start gap-3 no-underline">
		<Avatar {user} size="lg" />

		<div class="flex-1 min-w-0">
			<div class="flex items-start justify-between gap-2">
				<div class="min-w-0">
					<div class="flex items-center gap-1">
						<span class="font-bold text-text hover:underline truncate">
							{displayName}
						</span>
						{#if user.is_verified}
							<BadgeCheck class="w-4 h-4 text-primary flex-shrink-0" />
						{/if}
					</div>
					<p class="text-text-secondary truncate">@{user.username}</p>
				</div>

				{#if showFollow && !isCurrentUser}
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<div on:click|stopPropagation on:keydown|stopPropagation>
						<FollowButton
							userId={user.id}
							size="sm"
						/>
					</div>
				{/if}
			</div>

			{#if showBio && user.bio}
				<p class="mt-2 text-text line-clamp-2">{user.bio}</p>
			{/if}
		</div>
	</a>
</Card>

