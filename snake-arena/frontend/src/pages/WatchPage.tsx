import { GameBoard } from '../components/GameBoard/GameBoard';
import { useLiveGame } from '../hooks/useLiveGame';

export function WatchPage() {
  const state = useLiveGame();

  return (
    <div className="page">
      <h1>Watch</h1>
      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {state ? (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>
                Watching: <strong>SnakeBot</strong> <span className="muted">(demo)</span>
              </span>
              <span>
                Score: <strong>{state.score}</strong>
              </span>
            </div>
            <GameBoard state={state} />
          </>
        ) : (
          <p className="muted">Connecting…</p>
        )}
      </div>
    </div>
  );
}
