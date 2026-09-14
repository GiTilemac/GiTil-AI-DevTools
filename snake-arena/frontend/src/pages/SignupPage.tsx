import { type FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function SignupPage() {
  const { signup, error, loading, clearError } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    try {
      await signup({ username, password });
      navigate('/play');
    } catch {
      // error is surfaced via context state
    }
  }

  return (
    <div className="page">
      <h1>Sign up</h1>
      <div className="card">
        <form onSubmit={handleSubmit} noValidate>
          <div className="form-field">
            <label htmlFor="signup-username">Username</label>
            <input
              id="signup-username"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                clearError();
              }}
              autoComplete="username"
              required
            />
          </div>
          <div className="form-field">
            <label htmlFor="signup-password">Password</label>
            <input
              id="signup-password"
              type="password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                clearError();
              }}
              autoComplete="new-password"
              required
            />
          </div>
          {error && <p className="error-text">{error}</p>}
          <button type="submit" className="btn" disabled={loading}>
            {loading ? 'Signing up…' : 'Sign up'}
          </button>
        </form>
        <p className="muted" style={{ marginTop: 16 }}>
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </div>
    </div>
  );
}
