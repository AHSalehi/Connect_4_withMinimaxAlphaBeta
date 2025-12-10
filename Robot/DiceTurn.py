"""
Turn roller with uniform probability and a fatigue rule:

If any player acts in two consecutive turns, they are removed from the next roll.
After sitting out a single roll, they rejoin the pool. Useful for FastAPI
endpoints that need deterministic state transitions.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional, Sequence


@dataclass
class TurnState:
  last_player: Optional[str] = None
  consecutive_count: int = 0
  skip_next: Optional[str] = None


def roll_next_turn(players: Sequence[str], state: TurnState, *, rnd: Optional[random.Random] = None) -> dict:
  """
  Roll the dice uniformly to choose the next player.

  Rules:
  - If a player just played two turns in a row, they are excluded from this roll.
  - Excluded players return automatically after sitting out one roll.
  """
  if not players:
    raise ValueError("At least one player is required.")

  rnd = rnd or random
  pool: List[str] = [p for p in players if p != state.skip_next]
  if not pool:
    # Fallback: everyone was excluded (e.g., only one player) — allow all.
    pool = list(players)

  chosen = rnd.choice(pool)

  # Clear the skip after it has been applied once.
  if state.skip_next is not None:
    state.skip_next = None

  if chosen == state.last_player:
    state.consecutive_count += 1
  else:
    state.consecutive_count = 1
  state.last_player = chosen

  forced_skip = False
  if state.consecutive_count >= 2:
    state.skip_next = chosen
    state.consecutive_count = 0
    forced_skip = True

  next_pool = [p for p in players if p != state.skip_next] if state.skip_next else list(players)
  return {
    "player": chosen,
    "skip_next": state.skip_next,
    "forced_skip": forced_skip,
    "next_roll_pool": next_pool,
  }


__all__ = ["TurnState", "roll_next_turn"]
