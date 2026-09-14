import { act, renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it } from 'vitest';
import { AuthProvider, useAuth } from './AuthContext';

function wrapper({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

describe('useAuth', () => {
  it('throws when used outside an AuthProvider', () => {
    expect(() => renderHook(() => useAuth())).toThrow(/AuthProvider/);
  });

  it('starts with no user', () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.user).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('signup sets the current user', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    await act(async () => {
      await result.current.signup({ username: 'freshuser', password: 'pw' });
    });
    expect(result.current.user?.username).toBe('freshuser');
  });

  it('successful login sets the current user', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    await act(async () => {
      await result.current.signup({ username: 'loginflow', password: 'pw' });
      await result.current.logout();
    });
    await act(async () => {
      await result.current.login({ username: 'loginflow', password: 'pw' });
    });
    expect(result.current.user?.username).toBe('loginflow');
  });

  it('failed login sets an error and leaves user null', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    await act(async () => {
      await result.current.login({ username: 'ghost', password: 'nope' }).catch(() => {});
    });
    await waitFor(() => {
      expect(result.current.error).toMatch(/invalid/i);
    });
    expect(result.current.user).toBeNull();
  });

  it('logout clears the current user', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    await act(async () => {
      await result.current.signup({ username: 'byebye', password: 'pw' });
    });
    await act(async () => {
      await result.current.logout();
    });
    expect(result.current.user).toBeNull();
  });
});
