import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { GameBoard } from '../components/GameBoard/GameBoard';
import { ModeSelector } from '../components/ModeSelector/ModeSelector';
import { ScoreBar } from '../components/ScoreBar/ScoreBar';
import { useAuth } from '../context/AuthContext';
import { useGameLoop } from '../hooks/useGameLoop';
import { useLeaderboard } from '../hooks/useLeaderboard';

export function PlayPage() {
  const { user } = useAuth();
  const { submitScore } = useLeaderboard();
  const { state, setMode, restart } = useGameLoop('pass-through');
  const [submitted, setSubmitted] = useState(false);
  const submittedForTick = useRef<number | null>(null);

  useEffect(() => {
    if (state.status !== 'game-over') return;
    if (submittedForTick.current === state.tickCount) return;
    submittedForTick.current = state.tickCount;

    if (user) {
      submitScore(state.score, state.mode);
      setSubmitted(true);
    } else {
      setSubmitted(false);
    }
  }, [state.status, state.tickCount, state.score, state.mode, user, submitScore]);

  function handleRestart() {
    setSubmitted(false);
    submittedForTick.current = null;
    restart();
  }

  return (
    <div className="page">
      <h1>Play</h1>
      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <ModeSelector mode={state.mode} onChange={setMode} disabled={state.status === 'running'} />
          <ScoreBar score={state.score} status={state.status} />
        </div>

        <GameBoard state={state} />

        {state.status === 'game-over' && (
          <div className="card" style={{ padding: 16 }}>
            <p style={{ margin: '0 0 12px' }}>
              Final score: <strong>{state.score}</strong>
            </p>
            {user ? (
              submitted && <p className="muted" style={{ margin: '0 0 12px' }}>Score submitted to the leaderboard!</p>
            ) : (
              <p className="muted" style={{ margin: '0 0 12px' }}>
                <Link to="/login">Log in</Link> or <Link to="/signup">sign up</Link> to save your score to the leaderboard.
              </p>
            )}
            <button type="button" className="btn" onClick={handleRestart}>
              Play again
            </button>
          </div>
        )}

        <p className="muted" style={{ margin: 0 }}>
          Use the arrow keys or WASD to move. Choose a mode before you start — pass-through wraps you around the
          edges, walls end the game if you hit the boundary.
        </p>
      </div>
    </div>
  );
}
