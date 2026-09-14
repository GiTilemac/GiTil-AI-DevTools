import { render, type RenderOptions } from '@testing-library/react';
import type { ReactElement, ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../context/AuthContext';

function AllProviders({ children, route }: { children: ReactNode; route?: string }) {
  return (
    <MemoryRouter initialEntries={route ? [route] : ['/']}>
      <AuthProvider>{children}</AuthProvider>
    </MemoryRouter>
  );
}

export function renderWithProviders(ui: ReactElement, options: RenderOptions & { route?: string } = {}) {
  const { route, ...renderOptions } = options;
  return render(ui, { wrapper: ({ children }) => <AllProviders route={route}>{children}</AllProviders>, ...renderOptions });
}

export * from '@testing-library/react';
