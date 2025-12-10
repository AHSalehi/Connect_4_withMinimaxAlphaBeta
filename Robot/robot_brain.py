from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

ROWS = 10
COLS = 10
CONNECT_N = 4
MAX_DEPTH = 4
WIN_SCORE = 10_000


@dataclass
class SearchResult:
  column: int
  row: int
  score: float
  depth: int
  nodes: int
  decision_ms: float


def choose_best_move(
  board: List[List[Optional[str]]],
  bot_id: str = "BOT",
  opponent_ids: Optional[Sequence[str]] = None,
  depth: int = MAX_DEPTH,
) -> SearchResult:
  """Compute the bot's move with alpha-beta pruning."""
  start = time.perf_counter()
  nodes = [0]

  opponents = list(opponent_ids) if opponent_ids else infer_opponents(board, bot_id)
  valid_columns = [c for c in range(COLS) if find_drop_row(board, c) is not None]
  if not valid_columns:
    raise ValueError("Board is full; no moves available.")

  best_score = -math.inf
  best_move: Optional[Tuple[int, int]] = None

  for col in valid_columns:
    drop_row = find_drop_row(board, col)
    assert drop_row is not None
    child_board = place_disc(board, drop_row, col, bot_id)

    score = minimax(
      board=child_board,
      depth=depth - 1,
      maximizing=False,
      bot_id=bot_id,
      opponents=opponents,
      alpha=-math.inf,
      beta=math.inf,
      last_move=(drop_row, col),
      nodes=nodes,
    )

    if score > best_score:
      best_score = score
      best_move = (drop_row, col)

  decision_ms = (time.perf_counter() - start) * 1000.0
  if best_move is None:
    raise RuntimeError("Failed to select a move despite available columns.")

  return SearchResult(
    column=best_move[1],
    row=best_move[0],
    score=best_score,
    depth=depth,
    nodes=nodes[0],
    decision_ms=decision_ms,
  )


def minimax(
  board: List[List[Optional[str]]],
  depth: int,
  maximizing: bool,
  bot_id: str,
  opponents: Sequence[str],
  alpha: float,
  beta: float,
  last_move: Optional[Tuple[int, int]],
  nodes: List[int],
) -> float:
  """Alpha-beta search; returns a heuristic score from the bot's perspective."""
  nodes[0] += 1

  if last_move is not None:
    if check_win(board, last_move[0], last_move[1], connect_n=CONNECT_N):
      winner = board[last_move[0]][last_move[1]]
      if winner == bot_id:
        return WIN_SCORE + depth  # prefer faster wins
      return -WIN_SCORE - depth   # prefer slower losses

  if depth == 0 or board_is_full(board):
    return evaluate_board(board, bot_id=bot_id, opponents=opponents)

  valid_columns = [c for c in range(COLS) if find_drop_row(board, c) is not None]
  if not valid_columns:
    return evaluate_board(board, bot_id=bot_id, opponents=opponents)

  if maximizing:
    value = -math.inf
    for col in valid_columns:
      row = find_drop_row(board, col)
      assert row is not None
      child_board = place_disc(board, row, col, bot_id)
      score = minimax(child_board, depth - 1, False, bot_id, opponents, alpha, beta, (row, col), nodes)
      value = max(value, score)
      alpha = max(alpha, value)
      if alpha >= beta:
        break
    return value

  # Minimizing layer: explore every human id and take the worst outcome for the bot.
  value = math.inf
  for col in valid_columns:
    row = find_drop_row(board, col)
    assert row is not None
    for opp in opponents:
      child_board = place_disc(board, row, col, opp)
      score = minimax(child_board, depth - 1, True, bot_id, opponents, alpha, beta, (row, col), nodes)
      if score < value:
        value = score
      beta = min(beta, value)
      if beta <= alpha:
        break
    if beta <= alpha:
      break
  return value


def evaluate_board(board: List[List[Optional[str]]], bot_id: str, opponents: Sequence[str]) -> float:
  """Static evaluation: positive is good for the bot."""
  score = 0.0

  center_col = COLS // 2
  center_weight = 2.5
  center_count = sum(1 for r in range(ROWS) if board[r][center_col] == bot_id)
  score += center_count * center_weight

  # Scan all possible windows of length CONNECT_N.
  directions = [
    (0, 1),   # horizontal
    (1, 0),   # vertical
    (1, 1),   # diag down-right
    (-1, 1),  # diag up-right
  ]

  for row in range(ROWS):
    for col in range(COLS):
      for dr, dc in directions:
        if not in_bounds(row + (CONNECT_N - 1) * dr, col + (CONNECT_N - 1) * dc):
          continue
        window = [
          board[row + k * dr][col + k * dc]
          for k in range(CONNECT_N)
        ]
        score += score_window(window, bot_id, opponents)

  return score


def score_window(window: Sequence[Optional[str]], bot_id: str, opponents: Sequence[str]) -> float:
  bot_count = sum(1 for cell in window if cell == bot_id)
  opp_count = sum(1 for cell in window if cell in opponents)
  empty_count = window.count(None)

  if bot_count > 0 and opp_count > 0:
    return 0.0  # contested window
  if bot_count == CONNECT_N:
    return WIN_SCORE
  if opp_count == CONNECT_N:
    return -WIN_SCORE

  score = 0.0
  if bot_count == 3 and empty_count == 1:
    score += 50
  elif bot_count == 2 and empty_count == 2:
    score += 10
  elif bot_count == 1 and empty_count == 3:
    score += 2

  if opp_count == 3 and empty_count == 1:
    score -= 60  # prioritize blocking
  elif opp_count == 2 and empty_count == 2:
    score -= 8

  return score


def infer_opponents(board: List[List[Optional[str]]], bot_id: str) -> List[str]:
  """Pick every seen id that is not the bot as an adversary."""
  ids = set()
  for row in board:
    for cell in row:
      if cell is not None and cell != bot_id:
        ids.add(cell)
  if not ids:
    # Default to two human placeholders when board is empty.
    return ["P1", "P2"]
  return list(ids)


def find_drop_row(board: List[List[Optional[str]]], col: int) -> Optional[int]:
  """Return the lowest open row index for this column, or None if full."""
  for row in range(ROWS - 1, -1, -1):
    if board[row][col] is None:
      return row
  return None


def board_is_full(board: List[List[Optional[str]]]) -> bool:
  return all(board[0][c] is not None for c in range(COLS))


def place_disc(board: List[List[Optional[str]]], row: int, col: int, player: str) -> List[List[Optional[str]]]:
  """Copy the board and place a disc at (row, col)."""
  copy = [list(r) for r in board]
  copy[row][col] = player
  return copy


def in_bounds(row: int, col: int) -> bool:
  return 0 <= row < ROWS and 0 <= col < COLS


def check_win(board: List[List[Optional[str]]], row: int, col: int, connect_n: int = CONNECT_N) -> bool:
  """Check if the disc at (row, col) completes a line of length `connect_n`."""
  player = board[row][col]
  if player is None:
    return False

  directions = [
    (0, 1),
    (1, 0),
    (1, 1),
    (-1, 1),
  ]

  for dr, dc in directions:
    count = 1
    # Forward
    r, c = row + dr, col + dc
    while in_bounds(r, c) and board[r][c] == player:
      count += 1
      r += dr
      c += dc
    # Backward
    r, c = row - dr, col - dc
    while in_bounds(r, c) and board[r][c] == player:
      count += 1
      r -= dr
      c -= dc
    if count >= connect_n:
      return True
  return False


__all__ = [
  "SearchResult",
  "choose_best_move",
  "find_drop_row",
  "check_win",
  "evaluate_board",
  "infer_opponents",
]
