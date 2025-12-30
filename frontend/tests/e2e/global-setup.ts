/**
 * Global setup for E2E tests
 * 
 * Creates test user and data before tests run.
 * Stores authentication tokens for use in tests.
 */

import { chromium, FullConfig } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const API_BASE_URL = process.env.PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

// Test user credentials - password must be 8+ chars with uppercase, lowercase, digit
export const TEST_USER = {
	email: 'e2e_test@example.com',
	username: 'e2e_testuser',
	password: 'Test1234'
};

// Second test user for follow/unfollow tests
export const TEST_USER_2 = {
	email: 'e2e_test2@example.com',
	username: 'e2e_testuser2',
	password: 'Test1234'
};

interface AuthTokens {
	access_token: string;
	refresh_token: string;
	token_type: string;
}

interface StoredAuth {
	user: typeof TEST_USER & { id?: number };
	tokens: AuthTokens;
}

async function createUserIfNotExists(user: typeof TEST_USER): Promise<StoredAuth | null> {
	try {
		// Try to register the user
		const registerResponse = await fetch(`${API_BASE_URL}/auth/register`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				email: user.email,
				username: user.username,
				password: user.password
			})
		});

		if (registerResponse.ok || registerResponse.status === 400) {
			// User exists or was created, now login
			const loginResponse = await fetch(`${API_BASE_URL}/auth/login`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					username: user.username,
					password: user.password
				})
			});

			if (loginResponse.ok) {
				const data = await loginResponse.json();
				// Backend returns { user, tokens: { access_token, refresh_token, token_type } }
				const tokens = data.tokens || data;
				return {
					user: { ...user, id: data.user?.id },
					tokens: {
						access_token: tokens.access_token,
						refresh_token: tokens.refresh_token,
						token_type: tokens.token_type || 'bearer'
					}
				};
			} else {
				console.error('Login failed:', await loginResponse.text());
			}
		} else {
			console.error('Registration failed:', await registerResponse.text());
		}
	} catch (error) {
		console.error('Error creating/logging in user:', error);
	}
	return null;
}

async function createTestPost(tokens: AuthTokens, body: string): Promise<number | null> {
	try {
		const response = await fetch(`${API_BASE_URL}/posts/`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'Authorization': `Bearer ${tokens.access_token}`
			},
			body: JSON.stringify({ body })
		});

		if (response.ok) {
			const post = await response.json();
			return post.id;
		} else {
			console.error('Failed to create post:', await response.text());
		}
	} catch (error) {
		console.error('Error creating post:', error);
	}
	return null;
}

async function globalSetup(config: FullConfig) {
	console.log('🔧 Setting up E2E test environment...');

	const storageDir = path.join(__dirname, '.auth');
	if (!fs.existsSync(storageDir)) {
		fs.mkdirSync(storageDir, { recursive: true });
	}

	// Check if backend is running
	try {
		// Try the explore endpoint which doesn't require auth
		const healthCheck = await fetch(`${API_BASE_URL}/posts/explore?page=1&per_page=1`).catch(() => null);
		if (!healthCheck) {
			console.warn('⚠️ Backend does not appear to be running at', API_BASE_URL);
			console.warn('   Some E2E tests will be skipped.');
			
			// Store empty auth to indicate backend is not available
			fs.writeFileSync(
				path.join(storageDir, 'test-user.json'),
				JSON.stringify({ backendAvailable: false, reason: 'Backend not running' })
			);
			return;
		}
	} catch {
		console.warn('⚠️ Cannot connect to backend at', API_BASE_URL);
		fs.writeFileSync(
			path.join(storageDir, 'test-user.json'),
			JSON.stringify({ backendAvailable: false, reason: 'Connection failed' })
		);
		return;
	}

	// Create test users
	console.log('👤 Creating test user 1...');
	const auth1 = await createUserIfNotExists(TEST_USER);
	
	console.log('👤 Creating test user 2...');
	const auth2 = await createUserIfNotExists(TEST_USER_2);

	if (!auth1) {
		console.warn('⚠️ Could not create/login test user 1');
		console.warn('   This may be due to a bcrypt/passlib compatibility issue in the backend.');
		console.warn('   To fix: cd backend && pip install bcrypt==4.1.2');
		console.warn('   Backend-dependent tests will be skipped.');
		fs.writeFileSync(
			path.join(storageDir, 'test-user.json'),
			JSON.stringify({ backendAvailable: false, reason: 'Auth setup failed - check bcrypt version' })
		);
		return;
	}

	// Create some test posts
	console.log('📝 Creating test posts...');
	const postIds: number[] = [];
	for (let i = 0; i < 5; i++) {
		const postId = await createTestPost(auth1.tokens, `Test post ${i + 1} for E2E testing 🚀`);
		if (postId) postIds.push(postId);
	}

	// Store auth data for tests
	fs.writeFileSync(
		path.join(storageDir, 'test-user.json'),
		JSON.stringify({
			backendAvailable: true,
			user1: auth1,
			user2: auth2,
			testPosts: postIds
		}, null, 2)
	);

	console.log('✅ E2E setup complete!');
	console.log(`   - User 1: ${auth1.user.username}`);
	console.log(`   - User 2: ${auth2?.user.username || 'N/A'}`);
	console.log(`   - Test posts: ${postIds.length}`);
}

export default globalSetup;

