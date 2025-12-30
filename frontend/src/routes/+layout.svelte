<script lang="ts">
	import { onMount } from 'svelte';
	import { QueryClient, QueryClientProvider } from '@tanstack/svelte-query';
	import { Toaster } from 'svelte-sonner';
	import { auth } from '$lib/stores';
	import '../app.css';

	const queryClient = new QueryClient({
		defaultOptions: {
			queries: {
				staleTime: 1000 * 60, // 1 minute
				retry: 1,
				refetchOnWindowFocus: false
			}
		}
	});

	onMount(() => {
		auth.initialize();
	});
</script>

<QueryClientProvider client={queryClient}>
	<slot />
	<Toaster
		position="bottom-center"
		toastOptions={{
			style: 'background: var(--color-surface); color: var(--color-text); border: 1px solid var(--color-border);'
		}}
	/>
</QueryClientProvider>

