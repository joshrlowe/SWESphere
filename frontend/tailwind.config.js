/** @type {import('tailwindcss').Config} */
export default {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	darkMode: 'class',
	theme: {
		extend: {
			colors: {
				// Twitter/X Dark Theme
				primary: {
					DEFAULT: 'var(--color-primary)',
					hover: 'var(--color-primary-hover)',
					light: 'var(--color-primary-light)'
				},
				background: 'var(--color-background)',
				surface: {
					DEFAULT: 'var(--color-surface)',
					hover: 'var(--color-surface-hover)',
					elevated: 'var(--color-surface-elevated)'
				},
				text: {
					DEFAULT: 'var(--color-text)',
					secondary: 'var(--color-text-secondary)',
					muted: 'var(--color-text-muted)'
				},
				border: {
					DEFAULT: 'var(--color-border)',
					light: 'var(--color-border-light)'
				},
				success: 'var(--color-success)',
				error: 'var(--color-error)',
				warning: 'var(--color-warning)'
			},
			fontFamily: {
				sans: [
					'-apple-system',
					'BlinkMacSystemFont',
					'Segoe UI',
					'Roboto',
					'Helvetica',
					'Arial',
					'sans-serif'
				]
			},
			fontSize: {
				'2xs': '0.625rem'
			},
			spacing: {
				'18': '4.5rem',
				'88': '22rem'
			},
			maxWidth: {
				'feed': '600px'
			},
			animation: {
				'fade-in': 'fadeIn 0.2s ease-out',
				'slide-up': 'slideUp 0.3s ease-out',
				'spin-slow': 'spin 2s linear infinite'
			},
			keyframes: {
				fadeIn: {
					'0%': { opacity: '0' },
					'100%': { opacity: '1' }
				},
				slideUp: {
					'0%': { opacity: '0', transform: 'translateY(10px)' },
					'100%': { opacity: '1', transform: 'translateY(0)' }
				}
			}
		}
	},
	plugins: [
		require('@tailwindcss/forms')({
			strategy: 'class'
		}),
		require('@tailwindcss/typography')
	]
};

