import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { resolve } from 'path';

export default defineConfig({
	plugins: [svelte({ hot: !process.env.VITEST })],
	test: {
		include: ['tests/unit/**/*.test.ts', 'tests/components/**/*.test.ts'],
		globals: true,
		environment: 'jsdom',
		setupFiles: ['./tests/setup.ts'],
		coverage: {
			provider: 'v8',
			reporter: ['text', 'json', 'html'],
			include: ['src/lib/**/*.ts', 'src/lib/**/*.svelte'],
			exclude: ['src/lib/**/index.ts', 'node_modules']
		},
		alias: {
			$lib: resolve('./src/lib'),
			$app: resolve('./tests/mocks/app')
		},
		deps: {
			inline: [/svelte/]
		}
	},
	resolve: {
		alias: {
			$lib: resolve('./src/lib'),
			$app: resolve('./tests/mocks/app')
		}
	}
});

