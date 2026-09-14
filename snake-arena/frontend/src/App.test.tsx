import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { App } from './App';

// App owns its own AuthProvider, so these render <App> directly inside
// just a router - unlike page-level tests (see test/test-utils.tsx), which
// need renderWithProviders to supply the AuthProvider App normally would.
function renderApp(route: string) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <App />
    </MemoryRouter>,
  );
}

describe('App routing (spec 3.8)', () => {
  it('redirects / to /play', () => {
    renderApp('/');
    expect(screen.getByRole('heading', { name: 'Play' })).toBeInTheDocument();
  });

  it('renders the persistent Navbar on every route', () => {
    renderApp('/leaderboard');
    expect(screen.getByRole('navigation')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Leaderboard' })).toBeInTheDocument();
  });

  it('renders NotFoundPage for an unknown route, with a way back to Play', () => {
    renderApp('/this-route-does-not-exist');
    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /back to play/i })).toBeInTheDocument();
  });
});
