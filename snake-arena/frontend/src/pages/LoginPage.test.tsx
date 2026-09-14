import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { backendClient } from '../api/backendClient';
import { renderWithProviders } from '../test/test-utils';
import { LoginPage } from './LoginPage';

describe('LoginPage', () => {
  it('logs in with valid credentials', async () => {
    await backendClient.auth.signup({ username: 'validuser', password: 'correcthorse' });
    await backendClient.auth.logout();

    const user = userEvent.setup();
    renderWithProviders(<LoginPage />, { route: '/login' });

    await user.type(screen.getByLabelText('Username'), 'validuser');
    await user.type(screen.getByLabelText('Password'), 'correcthorse');
    await user.click(screen.getByRole('button', { name: /log in/i }));

    await waitFor(async () => {
      expect(await backendClient.auth.getCurrentUser()).toMatchObject({ username: 'validuser' });
    });
  });

  it('shows an inline error and does not log in with invalid credentials', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />, { route: '/login' });

    await user.type(screen.getByLabelText('Username'), 'nobody');
    await user.type(screen.getByLabelText('Password'), 'wrong');
    await user.click(screen.getByRole('button', { name: /log in/i }));

    expect(await screen.findByText(/invalid username or password/i)).toBeInTheDocument();
    expect(await backendClient.auth.getCurrentUser()).toBeNull();
  });
});
