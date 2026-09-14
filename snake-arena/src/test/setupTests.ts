import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';
import { resetWatchState } from '../api/backendClient';
import { resetDb } from '../api/mockDb';

afterEach(() => {
  cleanup();
  resetDb();
  resetWatchState();
});
