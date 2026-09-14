const IS_TEST = import.meta.env.MODE === 'test';
const DEFAULT_LATENCY_MS = 250;

/** Wraps a value in a Promise that resolves after a simulated network delay (skipped under test). */
export function delay<T>(value: T, ms: number = DEFAULT_LATENCY_MS): Promise<T> {
  if (IS_TEST) {
    return Promise.resolve(value);
  }
  return new Promise((resolve) => {
    setTimeout(() => resolve(value), ms);
  });
}
