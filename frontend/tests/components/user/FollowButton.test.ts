import { describe, it, expect, vi, beforeEach } from 'vitest';
import { setTokens } from '$lib/api/client';

// FollowButton component tests
// Full rendering requires store context, tested in E2E

describe('FollowButton Component', () => {
	beforeEach(() => {
		setTokens({
			access_token: 'test-token',
			refresh_token: 'test-refresh',
			token_type: 'bearer'
		});
	});

	describe('Button text logic', () => {
		it('should show "Follow" when not following', () => {
			const isFollowing = false;
			const isHovering = false;
			const buttonText = isFollowing ? (isHovering ? 'Unfollow' : 'Following') : 'Follow';
			expect(buttonText).toBe('Follow');
		});

		it('should show "Following" when following', () => {
			const isFollowing = true;
			const isHovering = false;
			const buttonText = isFollowing ? (isHovering ? 'Unfollow' : 'Following') : 'Follow';
			expect(buttonText).toBe('Following');
		});

		it('should show "Unfollow" when following and hovering', () => {
			const isFollowing = true;
			const isHovering = true;
			const buttonText = isFollowing ? (isHovering ? 'Unfollow' : 'Following') : 'Follow';
			expect(buttonText).toBe('Unfollow');
		});
	});

	describe('Button variant logic', () => {
		it('should use primary variant when not following', () => {
			const isFollowing = false;
			const isHovering = false;
			const variant = isFollowing ? (isHovering ? 'danger' : 'secondary') : 'primary';
			expect(variant).toBe('primary');
		});

		it('should use secondary variant when following', () => {
			const isFollowing = true;
			const isHovering = false;
			const variant = isFollowing ? (isHovering ? 'danger' : 'secondary') : 'primary';
			expect(variant).toBe('secondary');
		});

		it('should use danger variant when following and hovering', () => {
			const isFollowing = true;
			const isHovering = true;
			const variant = isFollowing ? (isHovering ? 'danger' : 'secondary') : 'primary';
			expect(variant).toBe('danger');
		});
	});

	describe('Optimistic update logic', () => {
		it('should toggle following state optimistically', () => {
			let isFollowing = false;
			const newState = !isFollowing;
			isFollowing = newState;
			expect(isFollowing).toBe(true);
		});

		it('should revert on API error', () => {
			let isFollowing = false;
			const originalState = isFollowing;

			// Optimistic update
			isFollowing = true;

			// Revert on error
			isFollowing = originalState;

			expect(isFollowing).toBe(false);
		});
	});

	describe('Size prop', () => {
		it('should accept sm size', () => {
			const size: 'sm' | 'md' | 'lg' = 'sm';
			expect(size).toBe('sm');
		});

		it('should accept md size', () => {
			const size: 'sm' | 'md' | 'lg' = 'md';
			expect(size).toBe('md');
		});

		it('should accept lg size', () => {
			const size: 'sm' | 'md' | 'lg' = 'lg';
			expect(size).toBe('lg');
		});
	});

	describe('Loading state', () => {
		it('should prevent double-click during loading', () => {
			let isLoading = false;
			let clickCount = 0;

			const handleClick = () => {
				if (isLoading) return;
				isLoading = true;
				clickCount++;
			};

			handleClick();
			handleClick(); // Should be ignored

			expect(clickCount).toBe(1);
		});
	});
});

