<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { isAuthenticated, isAuthInitialized } from '$lib/stores';

	$: if ($isAuthInitialized) {
		if ($isAuthenticated) {
			goto('/feed');
		} else {
			goto('/auth/login');
		}
	}
</script>

<div class="min-h-screen flex items-center justify-center bg-background">
	<div class="animate-spin rounded-full w-12 h-12 border-2 border-text-muted border-t-primary"></div>
</div>

