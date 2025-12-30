import '@testing-library/jest-dom/vitest';
import { vi, beforeAll, afterAll, afterEach } from 'vitest';
import { server } from './mocks/server';

// Extend Vitest matchers with jest-dom
declare module 'vitest' {
	interface Assertion<T> {
		toBeInTheDocument(): T;
		toHaveTextContent(text: string | RegExp): T;
		toBeVisible(): T;
		toBeDisabled(): T;
		toHaveAttribute(attr: string, value?: string): T;
		toHaveClass(...classNames: string[]): T;
		toHaveValue(value: string | number | string[]): T;
		toBeChecked(): T;
		toHaveFocus(): T;
	}
}

// Mock browser APIs
Object.defineProperty(window, 'matchMedia', {
	writable: true,
	value: vi.fn().mockImplementation((query) => ({
		matches: false,
		media: query,
		onchange: null,
		addListener: vi.fn(),
		removeListener: vi.fn(),
		addEventListener: vi.fn(),
		removeEventListener: vi.fn(),
		dispatchEvent: vi.fn()
	}))
});

// Mock localStorage
const localStorageMock = (() => {
	let store: Record<string, string> = {};
	return {
		getItem: vi.fn((key: string) => store[key] || null),
		setItem: vi.fn((key: string, value: string) => {
			store[key] = value;
		}),
		removeItem: vi.fn((key: string) => {
			delete store[key];
		}),
		clear: vi.fn(() => {
			store = {};
		}),
		get length() {
			return Object.keys(store).length;
		},
		key: vi.fn((index: number) => Object.keys(store)[index] || null)
	};
})();

Object.defineProperty(window, 'localStorage', {
	value: localStorageMock
});

// Setup MSW
beforeAll(() => {
	server.listen({ onUnhandledRequest: 'warn' });
});

afterEach(() => {
	server.resetHandlers();
	localStorageMock.clear();
});

afterAll(() => {
	server.close();
});

// Mock navigation
vi.mock('$app/navigation', () => ({
	goto: vi.fn(),
	invalidate: vi.fn(),
	invalidateAll: vi.fn(),
	preloadData: vi.fn(),
	preloadCode: vi.fn(),
	beforeNavigate: vi.fn(),
	afterNavigate: vi.fn(),
	onNavigate: vi.fn()
}));

// Mock environment
vi.mock('$app/environment', () => ({
	browser: true,
	dev: true,
	building: false,
	version: 'test'
}));

// Mock page store
vi.mock('$app/stores', () => {
	const { readable, writable } = require('svelte/store');
	return {
		page: readable({
			url: new URL('http://localhost:3000'),
			params: {},
			route: { id: '/' },
			status: 200,
			error: null,
			data: {},
			form: null
		}),
		navigating: readable(null),
		updated: {
			...readable(false),
			check: vi.fn()
		}
	};
});

