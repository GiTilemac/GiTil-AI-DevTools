import { Navigate, Route, Routes } from 'react-router-dom';
import { Navbar } from './components/Navbar/Navbar';
import { AuthProvider } from './context/AuthContext';
import { LeaderboardPage } from './pages/LeaderboardPage';
import { LoginPage } from './pages/LoginPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { PlayPage } from './pages/PlayPage';
import { SignupPage } from './pages/SignupPage';
import { WatchPage } from './pages/WatchPage';

export function App() {
  return (
    <AuthProvider>
      <Navbar />
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Navigate to="/play" replace />} />
          <Route path="/play" element={<PlayPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/leaderboard" element={<LeaderboardPage />} />
          <Route path="/watch" element={<WatchPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
    </AuthProvider>
  );
}
