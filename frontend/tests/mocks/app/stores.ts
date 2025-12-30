import { readable, writable } from 'svelte/store';

export const page = readable({
	url: new URL('http://localhost:3000'),
	params: {},
	route: { id: '/' },
	status: 200,
	error: null,
	data: {},
	form: null
});

export const navigating = readable(null);

export const updated = {
	...readable(false),
	check: async () => false
};

