"""
FastAPI backend for 10x10 Connect 4 with three players (P1, P2, BOT).

Endpoints
---------
- GET /state           : current board, winner, last move, move history
- POST /dice/roll      : roll next player with fatigue rule
- POST /move/human     : apply a human move (gravity-aware)
- POST /move/bot       : ask the bot to choose and apply a move (minimax+AB)
- POST /reset          : reset the game state

Board representation: 10x10 list of lists containing player ids or null.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator

# Ensure the Robot package is importable when running from Backend/
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.append(str(ROOT))

from Robot import TurnState, choose_best_move, find_drop_row  # type: ignore
from Robot import check_win, roll_next_turn  # type: ignore
from Robot.robot_brain import MAX_DEPTH  # type: ignore

ROWS = 10
COLS = 10
PLAYERS: List[str] = ["P1", "P2", "BOT"]

app = FastAPI(title="Connect 4 (10x10) Backend", version="0.1.0")


# ----------------------------
# Pydantic models
# ----------------------------
class StateResponse(BaseModel):
  board: List[List[Optional[str]]]
  winner: Optional[str]
  last_move: Optional[dict]
  history: List[dict]


class DiceRequest(BaseModel):
  players: Optional[List[str]] = Field(default=None, description="Override player pool.")

  @validator("players")
  def ensure_non_empty(cls, v):  # type: ignore
    if v is not None and len(v) == 0:
      raise ValueError("players cannot be empty")
    return v


class DiceResponse(BaseModel):
  player: str
  skip_next: Optional[str]
  forced_skip: bool
  next_roll_pool: List[str]


class HumanMoveRequest(BaseModel):
  player_id: Literal["P1", "P2"]
  column: int = Field(..., ge=0, lt=COLS, description="Column index (0-based)")


class BotMoveRequest(BaseModel):
  depth: int = Field(default=None, ge=1, le=8, description="Optional search depth override.")


class MoveResponse(BaseModel):
  row: int
  column: int
  board: List[List[Optional[str]]]
  winner: Optional[str]
  history: List[dict]
  bot_stats: Optional[dict] = None


# ----------------------------
# Game state
# ----------------------------
def _new_board() -> List[List[Optional[str]]]:
  return [[None for _ in range(COLS)] for _ in range(ROWS)]


state = {
  "board": _new_board(),
  "winner": None,
  "last_move": None,
  "history": [],  # list of dicts: {player,row,col}
  "turn_state": TurnState(),
}


# ----------------------------
# Helpers
# ----------------------------
def _apply_move(player_id: str, column: int) -> tuple[int, int]:
  if state["winner"]:
    raise HTTPException(status_code=400, detail=f"Game over. Winner: {state['winner']}")

  drop_row = find_drop_row(state["board"], column)
  if drop_row is None:
    raise HTTPException(status_code=400, detail="Column is full.")

  state["board"][drop_row][column] = player_id
  state["last_move"] = {"player": player_id, "row": drop_row, "col": column}
  state["history"].append(state["last_move"])

  if check_win(state["board"], drop_row, column):
    state["winner"] = player_id

  return drop_row, column


# ----------------------------
# Routes
# ----------------------------
@app.get("/state", response_model=StateResponse)
def get_state():
  return {
    "board": state["board"],
    "winner": state["winner"],
    "last_move": state["last_move"],
    "history": state["history"][-50:],
  }


@app.post("/dice/roll", response_model=DiceResponse)
def roll_dice(body: DiceRequest):
  players = body.players or PLAYERS
  result = roll_next_turn(players, state["turn_state"])
  return result


@app.post("/move/human", response_model=MoveResponse)
def human_move(body: HumanMoveRequest):
  if body.player_id not in PLAYERS or body.player_id == "BOT":
    raise HTTPException(status_code=400, detail="Invalid human player id.")

  row, col = _apply_move(body.player_id, body.column)
  return {
    "row": row,
    "column": col,
    "board": state["board"],
    "winner": state["winner"],
    "history": state["history"][-50:],
    "bot_stats": None,
  }


@app.post("/move/bot", response_model=MoveResponse)
def bot_move(body: BotMoveRequest):
  if state["winner"]:
    raise HTTPException(status_code=400, detail=f"Game over. Winner: {state['winner']}")

  depth = body.depth or MAX_DEPTH
  try:
    result = choose_best_move(state["board"], bot_id="BOT", depth=depth)
  except ValueError as exc:
    raise HTTPException(status_code=400, detail=str(exc))

  applied_row, applied_col = _apply_move("BOT", result.column)
  return {
    "row": applied_row,
    "column": applied_col,
    "board": state["board"],
    "winner": state["winner"],
    "history": state["history"][-50:],
    "bot_stats": {
      "score": result.score,
      "depth": result.depth,
      "nodes": result.nodes,
      "decision_ms": result.decision_ms,
    },
  }


@app.post("/reset")
def reset():
  state["board"] = _new_board()
  state["winner"] = None
  state["last_move"] = None
  state["history"] = []
  state["turn_state"] = TurnState()
  return {"ok": True}


__all__ = ["app"]
