import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeAll } from 'vitest';
import { installMockBackend, resetMockBackend } from './mockServer';

beforeAll(() => {
  installMockBackend();
});

afterEach(() => {
  cleanup();
  resetMockBackend();
});
