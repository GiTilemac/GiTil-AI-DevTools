import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { useAuth } from '../../context/AuthContext';
import { renderWithProviders } from '../../test/test-utils';
import { Navbar } from './Navbar';

function Harness() {
  const { signup } = useAuth();
  return (
    <div>
      <Navbar />
      <button type="button" onClick={() => signup({ username: 'navuser', password: 'pw' })}>
        trigger signup
      </button>
    </div>
  );
}

describe('Navbar', () => {
  it('shows Log in / Sign up when logged out', () => {
    renderWithProviders(<Navbar />);
    expect(screen.getByText('Log in')).toBeInTheDocument();
    expect(screen.getByText('Sign up')).toBeInTheDocument();
    expect(screen.queryByText(/Hi,/)).not.toBeInTheDocument();
  });

  it('shows the username and Logout when logged in, and logging out reverts the UI', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Harness />);

    await user.click(screen.getByText('trigger signup'));

    expect(await screen.findByText('Hi, navuser')).toBeInTheDocument();
    expect(screen.queryByText('Log in')).not.toBeInTheDocument();

    await user.click(screen.getByText('Logout'));

    expect(await screen.findByText('Log in')).toBeInTheDocument();
    expect(screen.queryByText(/Hi,/)).not.toBeInTheDocument();
  });
});
