export interface ScoreBarProps {
  score: number;
  status: 'idle' | 'running' | 'game-over';
}

export function ScoreBar({ score, status }: ScoreBarProps) {
  const statusLabel = status === 'idle' ? 'Press an arrow key to start' : status === 'running' ? 'Playing' : 'Game over';
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <span>
        Score: <strong>{score}</strong>
      </span>
      <span className="muted">{statusLabel}</span>
    </div>
  );
}
