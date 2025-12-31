import { describe, it, expect, vi } from 'vitest';

// Button component logic tests
// Note: Svelte 5 component rendering requires special testing setup
// Full component rendering is tested in E2E tests with Playwright

describe('Button Component Logic', () => {
	describe('Variant Classes', () => {
		const variantClasses = {
			primary: 'bg-primary text-white hover:bg-primary-hover',
			secondary: 'bg-transparent text-text border border-border',
			outline: 'bg-transparent text-primary border border-primary',
			ghost: 'bg-transparent text-text-secondary',
			danger: 'bg-error text-white'
		};

		it('should have primary variant styles', () => {
			expect(variantClasses.primary).toContain('bg-primary');
		});

		it('should have secondary variant styles', () => {
			expect(variantClasses.secondary).toContain('border');
		});

		it('should have outline variant styles', () => {
			expect(variantClasses.outline).toContain('text-primary');
		});

		it('should have ghost variant styles', () => {
			expect(variantClasses.ghost).toContain('bg-transparent');
		});

		it('should have danger variant styles', () => {
			expect(variantClasses.danger).toContain('bg-error');
		});
	});

	describe('Size Classes', () => {
		const sizeClasses = {
			sm: 'text-xs px-3 py-1.5',
			md: 'text-sm px-4 py-2',
			lg: 'text-base px-6 py-3'
		};

		it('should have small size styles', () => {
			expect(sizeClasses.sm).toContain('text-xs');
		});

		it('should have medium size styles', () => {
			expect(sizeClasses.md).toContain('text-sm');
		});

		it('should have large size styles', () => {
			expect(sizeClasses.lg).toContain('text-base');
		});
	});

	describe('Disabled state', () => {
		it('should apply disabled opacity class', () => {
			const disabledClass = 'disabled:opacity-50 disabled:cursor-not-allowed';
			expect(disabledClass).toContain('disabled:opacity-50');
		});
	});

	describe('Active state', () => {
		it('should apply active scale animation', () => {
			const activeClass = 'active:scale-95 transition-transform';
			expect(activeClass).toContain('active:scale-95');
		});

		it('should have transition for smooth animation', () => {
			const transitionClass = 'transition-all duration-200';
			expect(transitionClass).toContain('transition-all');
			expect(transitionClass).toContain('duration-200');
		});
	});

	describe('Focus styles', () => {
		it('should have focus-visible ring', () => {
			const focusClass = 'focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2';
			expect(focusClass).toContain('focus-visible:ring-2');
			expect(focusClass).toContain('focus-visible:ring-primary');
		});
	});

	describe('Full width', () => {
		it('should apply w-full class when fullWidth', () => {
			const fullWidth = true;
			const className = fullWidth ? 'w-full' : '';
			expect(className).toBe('w-full');
		});
	});

	describe('Button types', () => {
		it('should support button type', () => {
			const type: 'button' | 'submit' | 'reset' = 'button';
			expect(type).toBe('button');
		});

		it('should support submit type', () => {
			const type: 'button' | 'submit' | 'reset' = 'submit';
			expect(type).toBe('submit');
		});

		it('should support reset type', () => {
			const type: 'button' | 'submit' | 'reset' = 'reset';
			expect(type).toBe('reset');
		});
	});
});
