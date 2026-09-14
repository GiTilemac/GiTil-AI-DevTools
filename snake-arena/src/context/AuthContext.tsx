import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { backendClient, BackendError } from '../api/backendClient';
import type { LoginInput, SignupInput, User } from '../api/types';

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  error: string | null;
  login(input: LoginInput): Promise<void>;
  signup(input: SignupInput): Promise<void>;
  logout(): Promise<void>;
  clearError(): void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const login = useCallback(async (input: LoginInput) => {
    setLoading(true);
    setError(null);
    try {
      const loggedInUser = await backendClient.auth.login(input);
      setUser(loggedInUser);
    } catch (err) {
      setError(err instanceof BackendError ? err.message : 'Something went wrong. Please try again.');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const signup = useCallback(async (input: SignupInput) => {
    setLoading(true);
    setError(null);
    try {
      const newUser = await backendClient.auth.signup(input);
      setUser(newUser);
    } catch (err) {
      setError(err instanceof BackendError ? err.message : 'Something went wrong. Please try again.');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    await backendClient.auth.logout();
    setUser(null);
  }, []);

  const clearError = useCallback(() => setError(null), []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, loading, error, login, signup, logout, clearError }),
    [user, loading, error, login, signup, logout, clearError],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
