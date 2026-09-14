import type { GameMode } from '../game/types';

export interface User {
  id: string;
  username: string;
}

export interface LeaderboardEntry {
  id: string;
  username: string;
  score: number;
  mode: GameMode;
  achievedAt: string;
}

export interface SignupInput {
  username: string;
  password: string;
}

export interface LoginInput {
  username: string;
  password: string;
}

export interface SubmitScoreInput {
  username: string;
  score: number;
  mode: GameMode;
}
