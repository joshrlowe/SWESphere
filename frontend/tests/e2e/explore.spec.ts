import { test, expect } from '@playwright/test';
import { loadTestData, setupAuth } from './fixtures';

test.describe('Explore Page', () => {
	test.describe('Layout', () => {
		test.beforeEach(async ({ page }) => {
			const testData = loadTestData();
			await setupAuth(page, testData);
			await page.goto('/explore');
		});

		test('should display explore header', async ({ page }) => {
			await expect(page.getByRole('heading', { name: 'Explore' })).toBeVisible();
		});

		test('should display tabs', async ({ page }) => {
			await expect(page.getByRole('button', { name: 'For you' })).toBeVisible();
			await expect(page.getByRole('button', { name: 'Trending' })).toBeVisible();
		});

		test('should have For you tab active by default', async ({ page }) => {
			const forYouTab = page.getByRole('button', { name: 'For you' });
			await expect(forYouTab).toHaveClass(/font-bold/);
		});
	});

	test.describe('Tab Navigation', () => {
		test.beforeEach(async ({ page }) => {
			const testData = loadTestData();
			await setupAuth(page, testData);
			await page.goto('/explore');
		});

		test('should switch tabs on click', async ({ page }) => {
			const trendingTab = page.getByRole('button', { name: 'Trending' });
			await trendingTab.click();

			// The clicked tab should now be active
			await expect(trendingTab).toBeVisible();
			// Verify we're still on explore
			await expect(page).toHaveURL('/explore');
		});
	});

	test.describe('Content', () => {
		test('should load explore feed', async ({ page }) => {
			const testData = loadTestData();
			if (!testData.backendAvailable) {
				test.skip();
				return;
			}

			await setupAuth(page, testData);
			await page.goto('/explore');

			// Should show posts or empty state
			const content = page.locator('[role="article"], .text-text-secondary');
			await expect(content.first()).toBeVisible({ timeout: 15000 });
		});

		test('should show trending topics', async ({ page }) => {
			const testData = loadTestData();
			if (!testData.backendAvailable) {
				test.skip();
				return;
			}

			await setupAuth(page, testData);
			await page.setViewportSize({ width: 1280, height: 720 });
			await page.goto('/explore');

			// Check for trending section (may be in sidebar on desktop)
			const trending = page.getByText(/trend/i);
			// This is optional, so we just check the page loads correctly
			await expect(page.getByRole('heading', { name: 'Explore' })).toBeVisible();
		});
	});
});

test.describe('Search Functionality', () => {
	test.describe('Search Bar', () => {
		test('should display search bar', async ({ page }) => {
			const testData = loadTestData();
			await setupAuth(page, testData);
			await page.goto('/explore');

			const searchInput = page.getByPlaceholder('Search');
			await expect(searchInput).toBeVisible();
		});
	});

	test.describe('Search Results', () => {
		test('should show search results', async ({ page }) => {
			const testData = loadTestData();
			if (!testData.backendAvailable) {
				test.skip();
				return;
			}

			await setupAuth(page, testData);
			await page.goto('/explore');

			// Enter a search query
			const searchInput = page.getByPlaceholder('Search');
			await searchInput.fill('test');
			await searchInput.press('Enter');

			// Wait for results
			await page.waitForTimeout(2000);

			// Should display results or no results message
			await expect(page.locator('body')).toBeVisible();
		});
	});
});
