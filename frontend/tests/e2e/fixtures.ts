/**
 * E2E Test Fixtures
 * 
 * Provides authenticated page contexts and test data for E2E tests.
 */

import { test as base, expect, Page } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

interface TestUser {
	email: string;
	username: string;
	password: string;
	id?: number;
}

interface AuthTokens {
	access_token: string;
	refresh_token: string;
	token_type: string;
}

interface StoredAuth {
	user: TestUser;
	tokens: AuthTokens;
}

interface TestData {
	backendAvailable: boolean;
	user1?: StoredAuth;
	user2?: StoredAuth;
	testPosts?: number[];
}

// Load test data from global setup
function loadTestData(): TestData {
	const authFile = path.join(__dirname, '.auth', 'test-user.json');
	
	if (!fs.existsSync(authFile)) {
		return { backendAvailable: false };
	}

	try {
		return JSON.parse(fs.readFileSync(authFile, 'utf-8'));
	} catch {
		return { backendAvailable: false };
	}
}

// Custom test fixture with authentication
export const test = base.extend<{
	authenticatedPage: Page;
	testData: TestData;
	secondUserPage: Page;
}>({
	testData: async ({}, use) => {
		const data = loadTestData();
		await use(data);
	},

	authenticatedPage: async ({ page, testData }, use) => {
		if (!testData.backendAvailable || !testData.user1) {
			// Skip test if no backend
			test.skip();
			return;
		}

		// Set up authentication in localStorage before navigation
		await page.addInitScript((auth: StoredAuth) => {
			localStorage.setItem('auth_tokens', JSON.stringify({
				access_token: auth.tokens.access_token,
				refresh_token: auth.tokens.refresh_token,
				token_type: auth.tokens.token_type
			}));
			localStorage.setItem('auth_user', JSON.stringify(auth.user));
		}, testData.user1);

		await use(page);
	},

	secondUserPage: async ({ browser, testData }, use) => {
		if (!testData.backendAvailable || !testData.user2) {
			test.skip();
			return;
		}

		const context = await browser.newContext();
		const page = await context.newPage();

		await page.addInitScript((auth: StoredAuth) => {
			localStorage.setItem('auth_tokens', JSON.stringify({
				access_token: auth.tokens.access_token,
				refresh_token: auth.tokens.refresh_token,
				token_type: auth.tokens.token_type
			}));
			localStorage.setItem('auth_user', JSON.stringify(auth.user));
		}, testData.user2);

		await use(page);
		await context.close();
	}
});

export { expect };

// Helper to check if backend tests should run
export function skipIfNoBackend(testData: TestData) {
	if (!testData.backendAvailable) {
		test.skip();
	}
}

// Auth helper for regular test files
export async function setupAuth(page: Page, testData: TestData): Promise<boolean> {
	if (!testData.backendAvailable || !testData.user1) {
		return false;
	}

	await page.addInitScript((auth: StoredAuth) => {
		localStorage.setItem('auth_tokens', JSON.stringify({
			access_token: auth.tokens.access_token,
			refresh_token: auth.tokens.refresh_token,
			token_type: auth.tokens.token_type
		}));
		localStorage.setItem('auth_user', JSON.stringify(auth.user));
	}, testData.user1);

	return true;
}

// Export test data loader for use in other files
export { loadTestData };

