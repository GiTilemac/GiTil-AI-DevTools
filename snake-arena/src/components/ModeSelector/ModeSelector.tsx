import type { GameMode } from '../../game/types';
import styles from './ModeSelector.module.css';

const MODES: { value: GameMode; label: string }[] = [
  { value: 'pass-through', label: 'Pass-through' },
  { value: 'walls', label: 'Walls' },
];

export interface ModeSelectorProps {
  mode: GameMode;
  onChange(mode: GameMode): void;
  disabled?: boolean;
}

export function ModeSelector({ mode, onChange, disabled }: ModeSelectorProps) {
  return (
    <div className={styles.group} role="radiogroup" aria-label="Game mode">
      {MODES.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={mode === option.value}
          disabled={disabled}
          className={`${styles.option} ${mode === option.value ? styles.optionActive : ''}`}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
