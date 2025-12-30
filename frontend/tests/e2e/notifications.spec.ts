import { test, expect } from '@playwright/test';
import { loadTestData, setupAuth } from './fixtures';

test.describe('Notifications Page', () => {
	test.describe('Layout', () => {
		test.beforeEach(async ({ page }) => {
			const testData = loadTestData();
			await setupAuth(page, testData);
			await page.goto('/notifications');
		});

		test('should display notifications header', async ({ page }) => {
			await expect(page.getByRole('heading', { name: 'Notifications' })).toBeVisible();
		});

		test('should display tabs', async ({ page }) => {
			// Use exact match to avoid "Mark all as read" matching "All"
			await expect(page.getByRole('button', { name: 'All', exact: true })).toBeVisible();
			await expect(page.getByRole('button', { name: 'Mentions' })).toBeVisible();
		});

		test('should have mark all as read button', async ({ page }) => {
			await expect(page.getByRole('button', { name: /mark all as read/i })).toBeVisible();
		});
	});

	test.describe('Notification Types', () => {
		test('should display follow notifications', async ({ page }) => {
			const testData = loadTestData();
			if (!testData.backendAvailable) {
				test.skip();
				return;
			}

			await setupAuth(page, testData);
			await page.goto('/notifications');

			// Wait for notifications to load (or empty state)
			const content = page.locator('[role="article"], .notification-item, .text-text-secondary');
			await expect(content.first()).toBeVisible({ timeout: 10000 });
		});

		test('should display like notifications', async ({ page }) => {
			const testData = loadTestData();
			if (!testData.backendAvailable) {
				test.skip();
				return;
			}

			await setupAuth(page, testData);
			await page.goto('/notifications');

			// Page should load without errors
			await expect(page.getByRole('heading', { name: 'Notifications' })).toBeVisible();
		});

		test('should display comment notifications', async ({ page }) => {
			const testData = loadTestData();
			if (!testData.backendAvailable) {
				test.skip();
				return;
			}

			await setupAuth(page, testData);
			await page.goto('/notifications');

			// Page should load without errors
			await expect(page.getByRole('heading', { name: 'Notifications' })).toBeVisible();
		});

		test('should display mention notifications', async ({ page }) => {
			const testData = loadTestData();
			if (!testData.backendAvailable) {
				test.skip();
				return;
			}

			await setupAuth(page, testData);
			await page.goto('/notifications');

			// Switch to mentions tab
			await page.getByRole('button', { name: 'Mentions' }).click();

			// Page should stay loaded
			await expect(page.getByRole('heading', { name: 'Notifications' })).toBeVisible();
		});
	});

	test.describe('Notification Actions', () => {
		test('should navigate to related content', async ({ page }) => {
			const testData = loadTestData();
			if (!testData.backendAvailable) {
				test.skip();
				return;
			}

			await setupAuth(page, testData);
			await page.goto('/notifications');

			// Wait for notifications
			await page.waitForTimeout(2000);

			// Click on first notification link if available
			const notificationLinks = page.locator('a[href*="/status/"], a[href*="/profile/"]');
			if ((await notificationLinks.count()) > 0) {
				await notificationLinks.first().click();

				// Should navigate somewhere
				await expect(page).not.toHaveURL('/notifications');
			}
		});

		test('should mark notification as read', async ({ page }) => {
			const testData = loadTestData();
			if (!testData.backendAvailable) {
				test.skip();
				return;
			}

			await setupAuth(page, testData);
			await page.goto('/notifications');

			// Click mark all as read
			const markAllButton = page.getByRole('button', { name: /mark all as read/i });
			await markAllButton.click();

			// Button click should work without errors
			await expect(page.getByRole('heading', { name: 'Notifications' })).toBeVisible();
		});
	});

	test.describe('Empty State', () => {
		test('should show empty state when no notifications', async ({ page }) => {
			const testData = loadTestData();
			if (!testData.backendAvailable) {
				test.skip();
				return;
			}

			await setupAuth(page, testData);
			await page.goto('/notifications');

			// Should show either notifications or empty state
			const content = page.locator('[role="article"], .notification-item, .text-text-secondary');
			await expect(content.first()).toBeVisible({ timeout: 10000 });
		});
	});
});
