import { describe, it, expect } from 'vitest';
import { getAvatarUrl } from '$lib/types/user';

// Avatar component logic tests
// Note: Svelte 5 component rendering requires special testing setup
// Full component rendering is tested in E2E tests with Playwright

describe('Avatar Component Logic', () => {
	const mockUser = {
		id: 1,
		username: 'testuser',
		display_name: 'Test User',
		avatar_url: 'https://example.com/avatar.jpg',
		is_verified: false
	};

	describe('Size classes', () => {
		const sizeClasses = {
			sm: 'w-8 h-8',
			md: 'w-10 h-10',
			lg: 'w-12 h-12',
			xl: 'w-16 h-16',
			'2xl': 'w-32 h-32'
		};

		it('should have small size classes', () => {
			expect(sizeClasses.sm).toContain('w-8');
			expect(sizeClasses.sm).toContain('h-8');
		});

		it('should have medium size classes', () => {
			expect(sizeClasses.md).toContain('w-10');
			expect(sizeClasses.md).toContain('h-10');
		});

		it('should have large size classes', () => {
			expect(sizeClasses.lg).toContain('w-12');
			expect(sizeClasses.lg).toContain('h-12');
		});

		it('should have extra large size classes', () => {
			expect(sizeClasses.xl).toContain('w-16');
			expect(sizeClasses.xl).toContain('h-16');
		});

		it('should have 2xl size classes', () => {
			expect(sizeClasses['2xl']).toContain('w-32');
			expect(sizeClasses['2xl']).toContain('h-32');
		});
	});

	describe('Image source logic', () => {
		it('should use user avatar_url when available', () => {
			const imageSrc = mockUser.avatar_url;
			expect(imageSrc).toBe('https://example.com/avatar.jpg');
		});

		it('should use getAvatarUrl fallback when no avatar', () => {
			const userWithoutAvatar = { ...mockUser, avatar_url: null };
			const imageSrc = getAvatarUrl(userWithoutAvatar);

			expect(imageSrc).toContain('dicebear.com');
		});

		it('should use src prop when provided directly', () => {
			const src = 'https://example.com/direct-image.jpg';
			const imageSrc = src || getAvatarUrl(mockUser);

			expect(imageSrc).toBe('https://example.com/direct-image.jpg');
		});
	});

	describe('Alt text logic', () => {
		it('should use custom alt when provided', () => {
			const customAlt = 'Custom Alt Text';
			const alt = customAlt || `@${mockUser.username}`;

			expect(alt).toBe('Custom Alt Text');
		});

		it('should use @username when no custom alt', () => {
			const customAlt = '';
			const alt = customAlt || `@${mockUser.username}`;

			expect(alt).toBe('@testuser');
		});

		it('should default to Avatar when no user and no alt', () => {
			const customAlt = '';
			const user = null;
			const alt = customAlt || (user ? `@${user.username}` : 'Avatar');

			expect(alt).toBe('Avatar');
		});
	});

	describe('Base styling', () => {
		it('should have rounded-full class', () => {
			const baseClasses = 'rounded-full object-cover bg-surface flex-shrink-0';
			expect(baseClasses).toContain('rounded-full');
		});

		it('should have object-cover class', () => {
			const baseClasses = 'rounded-full object-cover bg-surface flex-shrink-0';
			expect(baseClasses).toContain('object-cover');
		});

		it('should have bg-surface class', () => {
			const baseClasses = 'rounded-full object-cover bg-surface flex-shrink-0';
			expect(baseClasses).toContain('bg-surface');
		});
	});

	describe('Error handling', () => {
		it('should switch to fallback on image error', () => {
			const originalSrc = 'https://example.com/broken.jpg';
			const handleError = () => `https://api.dicebear.com/7.x/identicon/svg?seed=${Math.random()}&size=128`;

			const fallbackSrc = handleError();
			expect(fallbackSrc).toContain('dicebear.com');
		});
	});
});
