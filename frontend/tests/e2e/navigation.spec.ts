import { test, expect } from '@playwright/test';
import { loadTestData, setupAuth } from './fixtures';

test.describe('Navigation', () => {
	test.describe('Sidebar Navigation', () => {
		test.beforeEach(async ({ page }) => {
			const testData = loadTestData();
			await setupAuth(page, testData);
			await page.setViewportSize({ width: 1280, height: 720 });
		});

		test('should display sidebar on desktop', async ({ page }) => {
			await page.goto('/feed');

			const sidebar = page.locator('aside').first();
			await expect(sidebar).toBeVisible();
		});

		test('should have navigation links', async ({ page }) => {
			await page.goto('/feed');

			await expect(page.getByRole('link', { name: /home/i })).toBeVisible();
			await expect(page.getByRole('link', { name: /explore/i })).toBeVisible();
			await expect(page.getByRole('link', { name: /notifications/i })).toBeVisible();
		});

		test('should navigate to explore', async ({ page }) => {
			await page.goto('/feed');

			await page.getByRole('link', { name: /explore/i }).click();

			await expect(page).toHaveURL('/explore');
		});

		test('should navigate to notifications', async ({ page }) => {
			await page.goto('/feed');

			await page.getByRole('link', { name: /notifications/i }).click();

			await expect(page).toHaveURL('/notifications');
		});

		test('should highlight active navigation item', async ({ page }) => {
			await page.goto('/feed');

			const homeLink = page.getByRole('link', { name: /home/i });
			await expect(homeLink).toHaveClass(/font-bold/);
		});
	});

	test.describe('Mobile Navigation', () => {
		test.beforeEach(async ({ page }) => {
			const testData = loadTestData();
			await setupAuth(page, testData);
			await page.setViewportSize({ width: 375, height: 667 });
		});

		test('should display bottom navigation on mobile', async ({ page }) => {
			await page.goto('/feed');

			const bottomNav = page.locator('nav.fixed.bottom-0');
			await expect(bottomNav).toBeVisible();
		});

		test('should have mobile navigation icons', async ({ page }) => {
			await page.goto('/feed');

			const bottomNav = page.locator('nav.fixed.bottom-0');
			const links = bottomNav.locator('a');

			await expect(links).toHaveCount(4);
		});

		test('should navigate using bottom nav', async ({ page }) => {
			await page.goto('/feed');

			const bottomNav = page.locator('nav.fixed.bottom-0');
			const exploreLink = bottomNav.locator('a').nth(1);
			await exploreLink.click();

			await expect(page).toHaveURL(/explore|search/);
		});
	});

	test.describe('Post Button', () => {
		test.beforeEach(async ({ page }) => {
			const testData = loadTestData();
			await setupAuth(page, testData);
		});

		test('should show compose button on desktop', async ({ page }) => {
			await page.setViewportSize({ width: 1280, height: 720 });
			await page.goto('/feed');

			// Use sidebar specific button
			const sidebarPostButton = page.locator('aside').getByRole('button', { name: /post/i });
			await expect(sidebarPostButton).toBeVisible();
		});

		test('should open compose modal on click', async ({ page }) => {
			const testData = loadTestData();
			if (!testData.backendAvailable) {
				test.skip();
				return;
			}

			await setupAuth(page, testData);
			await page.setViewportSize({ width: 1280, height: 720 });
			await page.goto('/feed');
			
			// Wait for page to fully load
			await page.waitForLoadState('networkidle');

			// Click the sidebar post button specifically
			const sidebarPostButton = page.locator('aside').getByRole('button', { name: /post/i });
			await expect(sidebarPostButton).toBeVisible();
			await sidebarPostButton.click();

			// Modal should appear - check for modal overlay or dialog role
			const modal = page.locator('[role="dialog"]');
			await expect(modal).toBeVisible({ timeout: 5000 });
		});

		test('should close modal on escape', async ({ page }) => {
			const testData = loadTestData();
			if (!testData.backendAvailable) {
				test.skip();
				return;
			}

			await setupAuth(page, testData);
			await page.setViewportSize({ width: 1280, height: 720 });
			await page.goto('/feed');
			
			// Wait for page to fully load
			await page.waitForLoadState('networkidle');

			// Click the sidebar post button
			const sidebarPostButton = page.locator('aside').getByRole('button', { name: /post/i });
			await expect(sidebarPostButton).toBeVisible();
			await sidebarPostButton.click();

			// Wait for modal to appear
			const modal = page.locator('[role="dialog"]');
			await expect(modal).toBeVisible({ timeout: 5000 });

			// Press Escape
			await page.keyboard.press('Escape');

			// Modal should close
			await expect(modal).not.toBeVisible({ timeout: 5000 });
		});
	});

	test.describe('User Menu', () => {
		test('should display user info in sidebar', async ({ page }) => {
			const testData = loadTestData();
			if (!testData.backendAvailable || !testData.user1) {
				test.skip();
				return;
			}

			await setupAuth(page, testData);
			await page.setViewportSize({ width: 1280, height: 720 });
			await page.goto('/feed');

			// Should show username somewhere (use first() to avoid strict mode violation)
			await expect(page.getByText(testData.user1.user.username, { exact: false }).first()).toBeVisible({ timeout: 10000 });
		});

		test('should logout on logout click', async ({ page }) => {
			const testData = loadTestData();
			if (!testData.backendAvailable) {
				test.skip();
				return;
			}

			await setupAuth(page, testData);
			await page.setViewportSize({ width: 1280, height: 720 });
			await page.goto('/feed');

			// Find and click logout
			const logoutButton = page.getByRole('button', { name: /logout|log out|sign out/i });
			if ((await logoutButton.count()) > 0) {
				await logoutButton.click();

				// Should redirect to login
				await expect(page).toHaveURL(/\/auth\/login/);
			}
		});
	});
});

test.describe('Route Guards', () => {
	test('should redirect unauthenticated users from protected routes', async ({ page }) => {
		await page.goto('/feed');

		await expect(page).toHaveURL(/\/auth\/login/);
	});

	test('should allow access to public routes', async ({ page }) => {
		await page.goto('/auth/login');

		await expect(page).toHaveURL('/auth/login');
	});

	test('should redirect authenticated users from login to feed', async ({ page }) => {
		const testData = loadTestData();
		if (!testData.backendAvailable || !testData.user1) {
			test.skip();
			return;
		}

		await setupAuth(page, testData);
		await page.goto('/auth/login');

		// Should redirect to feed
		await expect(page).toHaveURL('/feed', { timeout: 10000 });
	});
});

test.describe('Back Navigation', () => {
	test('should go back on back button click', async ({ page }) => {
		const testData = loadTestData();
		if (!testData.backendAvailable) {
			test.skip();
			return;
		}

		await setupAuth(page, testData);
		await page.goto('/feed');

		// Navigate to explore
		await page.getByRole('link', { name: /explore/i }).click();
		await expect(page).toHaveURL('/explore');

		// Use browser back
		await page.goBack();

		// Should go back to feed
		await expect(page).toHaveURL('/feed');
	});
});

test.describe('Deep Linking', () => {
	test('should load specific post', async ({ page }) => {
		// Post detail page not implemented yet
			test.skip();
	});

	test('should load specific profile', async ({ page }) => {
		const testData = loadTestData();
		if (!testData.backendAvailable || !testData.user1) {
			test.skip();
			return;
		}

		await setupAuth(page, testData);
		await page.goto(`/profile/${testData.user1.user.username}`);

		// Should show profile (username should be visible)
		await expect(page.getByText(`@${testData.user1.user.username}`)).toBeVisible({ timeout: 10000 });
	});
});
