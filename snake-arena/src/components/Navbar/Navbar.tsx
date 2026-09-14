import { NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import styles from './Navbar.module.css';

function navLinkClass({ isActive }: { isActive: boolean }): string {
  return isActive ? styles.linkActive : '';
}

export function Navbar() {
  const { user, logout } = useAuth();

  return (
    <nav className={styles.nav}>
      <NavLink to="/play" className={styles.brand}>
        Snake Arena
      </NavLink>

      <div className={styles.links}>
        <NavLink to="/play" className={navLinkClass}>
          Play
        </NavLink>
        <NavLink to="/leaderboard" className={navLinkClass}>
          Leaderboard
        </NavLink>
        <NavLink to="/watch" className={navLinkClass}>
          Watch
        </NavLink>
      </div>

      <div className={styles.right}>
        {user ? (
          <>
            <span className={styles.username}>Hi, {user.username}</span>
            <button type="button" className={styles.logoutBtn} onClick={() => logout()}>
              Logout
            </button>
          </>
        ) : (
          <div className={styles.authLinks}>
            <NavLink to="/login">Log in</NavLink>
            <NavLink to="/signup" className="btn">
              Sign up
            </NavLink>
          </div>
        )}
      </div>
    </nav>
  );
}
