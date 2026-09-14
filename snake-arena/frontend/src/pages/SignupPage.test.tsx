import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { backendClient } from '../api/backendClient';
import { renderWithProviders } from '../test/test-utils';
import { SignupPage } from './SignupPage';

describe('SignupPage', () => {
  it('logs the user in immediately after a successful signup', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SignupPage />, { route: '/signup' });

    await user.type(screen.getByLabelText('Username'), 'brandnew');
    await user.type(screen.getByLabelText('Password'), 'pw');
    await user.click(screen.getByRole('button', { name: /sign up/i }));

    await waitFor(async () => {
      expect(await backendClient.auth.getCurrentUser()).toMatchObject({ username: 'brandnew' });
    });
  });

  it('shows an inline error for a duplicate username', async () => {
    await backendClient.auth.signup({ username: 'existing', password: 'pw' });
    await backendClient.auth.logout();

    const user = userEvent.setup();
    renderWithProviders(<SignupPage />, { route: '/signup' });

    await user.type(screen.getByLabelText('Username'), 'existing');
    await user.type(screen.getByLabelText('Password'), 'anything');
    await user.click(screen.getByRole('button', { name: /sign up/i }));

    expect(await screen.findByText(/already taken/i)).toBeInTheDocument();
  });
});
