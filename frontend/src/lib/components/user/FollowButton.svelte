<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { Button } from '$lib/components/ui';
	import { followUser, unfollowUser } from '$lib/api/users';
	import { toast } from 'svelte-sonner';

	export let userId: number;
	export let isFollowing: boolean = false;
	export let size: 'sm' | 'md' | 'lg' = 'md';

	const dispatch = createEventDispatcher<{
		follow: { userId: number; isFollowing: boolean };
	}>();

	let isLoading = false;
	let isHovering = false;

	$: buttonText = isFollowing ? (isHovering ? 'Unfollow' : 'Following') : 'Follow';
	$: variant = isFollowing ? (isHovering ? 'danger' : 'secondary') : 'primary' as const;

	async function handleClick() {
		if (isLoading) return;

		isLoading = true;
		const newState = !isFollowing;

		// Optimistic update
		isFollowing = newState;

		try {
			if (newState) {
				await followUser(userId);
			} else {
				await unfollowUser(userId);
			}
			dispatch('follow', { userId, isFollowing: newState });
		} catch (error) {
			// Revert on error
			isFollowing = !newState;
			toast.error(newState ? 'Failed to follow user' : 'Failed to unfollow user');
		} finally {
			isLoading = false;
		}
	}
</script>

<Button
	variant={isFollowing ? (isHovering ? 'danger' : 'secondary') : 'primary'}
	{size}
	loading={isLoading}
	on:click={handleClick}
	on:mouseenter={() => (isHovering = true)}
	on:mouseleave={() => (isHovering = false)}
>
	{buttonText}
</Button>

