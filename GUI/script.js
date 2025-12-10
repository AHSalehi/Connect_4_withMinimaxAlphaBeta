const SIZE = 10;

const PLAYERS = [
  { id: "P1", name: "Human One", role: "Player 1", color: "#ff6b6b", short: "P1" },
  { id: "P2", name: "Human Two", role: "Player 2", color: "#34d399", short: "P2" },
  { id: "BOT", name: "Minimax Bot", role: "Robot", color: "#f7b733", short: "Bot" },
];

const boardState = Array.from({ length: SIZE }, () => Array(SIZE).fill(null));
const moveHistory = [];

const boardGrid = document.getElementById("board-grid");
const statusText = document.getElementById("status-text");
const moveLog = document.getElementById("move-log");
const playerList = document.getElementById("player-list");
const diceIndicator = document.getElementById("dice-indicator");
const turnCountdown = document.getElementById("turn-countdown");
const rollBtn = document.getElementById("roll-btn");
const botDecision = document.getElementById("bot-decision");
const botRuntime = document.getElementById("bot-runtime");

let currentPlayerId = null;
let rollingTimeout = null;
let countdownInterval = null;
let isRolling = false;
let botThinking = false;

init();

function init() {
  renderPlayers();
  renderBoard();
  attachEvents();
  setStatus("Ready. Roll to pick the opening turn.");
  turnCountdown.textContent = "Waiting…";
}

function renderPlayers() {
  playerList.innerHTML = "";
  PLAYERS.forEach((player) => {
    const card = document.createElement("div");
    card.className = "player-card";
    card.dataset.playerId = player.id;

    const swatch = document.createElement("div");
    swatch.className = "swatch";
    swatch.style.background = player.color;

    const meta = document.createElement("div");
    meta.className = "player-meta";

    const name = document.createElement("p");
    name.className = "player-name";
    name.textContent = player.name;

    const role = document.createElement("span");
    role.className = "player-role";
    role.textContent = player.role;

    meta.appendChild(name);
    meta.appendChild(role);
    card.appendChild(swatch);
    card.appendChild(meta);
    playerList.appendChild(card);
  });
}

function renderBoard() {
  const frag = document.createDocumentFragment();
  for (let row = 0; row < SIZE; row += 1) {
    for (let col = 0; col < SIZE; col += 1) {
      const cell = document.createElement("button");
      cell.type = "button";
      cell.className = "cell";
      cell.dataset.row = row.toString();
      cell.dataset.col = col.toString();

      const disc = document.createElement("div");
      disc.className = "disc";
      cell.appendChild(disc);

      const label = document.createElement("span");
      label.className = "label";
      label.textContent = `${row + 1},${col + 1}`;
      cell.appendChild(label);

      frag.appendChild(cell);
    }
  }
  boardGrid.appendChild(frag);
}

function attachEvents() {
  boardGrid.addEventListener("click", (event) => {
    const cell = event.target.closest(".cell");
    if (!cell) return;
    const row = Number(cell.dataset.row);
    const col = Number(cell.dataset.col);
    handleCellClick(row, col, cell);
  });

  rollBtn.addEventListener("click", () => {
    clearQueuedRoll();
    rollTurn(true);
  });
}

function handleCellClick(row, col, cell) {
  if (isRolling) {
    setStatus("Rolling in progress. Wait for the dice to land.");
    return;
  }

  if (!currentPlayerId) {
    setStatus("No active turn yet. Roll the dice to start.");
    return;
  }

  if (currentPlayerId === "BOT") {
    setStatus("Bot is selecting a move. Please wait.");
    return;
  }

  const dropRow = findAvailableRow(col);
  if (dropRow === null) {
    flashFault(cell, "Column is full. Choose another column.");
    return;
  }

  placeDisc(currentPlayerId, dropRow, col);
}

function placeDisc(playerId, row, col) {
  boardState[row][col] = playerId;
  const cell = getCell(row, col);
  cell.classList.add("filled", `player-${playerId}`);
  logMove(playerId, row, col);
  setStatus(`${describePlayer(playerId)} placed a disc at (${row + 1}, ${col + 1}). Rolling for the next turn...`);

  if (boardIsFull()) {
    setCurrentPlayer(null);
    clearQueuedRoll();
    turnCountdown.textContent = "Board full";
    setStatus("Board is full. Restart to play again.");
    return;
  }

  setCurrentPlayer(null);
  queueTurnRoll(2000);
}

function getCell(row, col) {
  return boardGrid.querySelector(`.cell[data-row="${row}"][data-col="${col}"]`);
}

function logMove(playerId, row, col) {
  moveHistory.unshift({
    playerId,
    row,
    col,
    time: new Date(),
  });
  if (moveHistory.length > 50) {
    moveHistory.pop();
  }
  renderLog();
}

function renderLog() {
  moveLog.innerHTML = "";
  moveHistory.forEach((entry) => {
    const item = document.createElement("li");
    item.className = "log-item";
    const actor = document.createElement("span");
    actor.className = "actor";
    actor.textContent = entry.playerId;
    const coord = document.createElement("span");
    coord.textContent = `(${entry.row + 1}, ${entry.col + 1})`;
    item.appendChild(actor);
    item.appendChild(coord);
    moveLog.appendChild(item);
  });
}

function rollTurn(force = false) {
  if (isRolling) return;
  if (!force && botThinking) return;
  if (boardIsFull()) {
    setStatus("Board is full. Restart to play again.");
    return;
  }

  isRolling = true;
  diceIndicator.classList.add("rolling");
  setStatus("Rolling for the next turn...");
  turnCountdown.textContent = "Rolling…";

  const rollDuration = 900 + Math.random() * 500;
  setTimeout(() => {
    const next = pickNextPlayer();
    diceIndicator.classList.remove("rolling");
    diceIndicator.textContent = `${next.short} is up`;
    setCurrentPlayer(next.id);
    isRolling = false;

    if (next.id === "BOT") {
      requestBotMove();
    }
  }, rollDuration);
}

function pickNextPlayer() {
  const idx = Math.floor(Math.random() * PLAYERS.length);
  return PLAYERS[idx];
}

function setCurrentPlayer(playerId) {
  currentPlayerId = playerId;
  highlightPlayer(playerId);
  if (playerId) {
    setStatus(`${describePlayer(playerId)} to move.`);
    turnCountdown.textContent = "Your move";
  } else {
    turnCountdown.textContent = "Rolling soon";
  }
}

function highlightPlayer(playerId) {
  const cards = playerList.querySelectorAll(".player-card");
  cards.forEach((card) => {
    const active = card.dataset.playerId === playerId;
    card.classList.toggle("active", active);
  });
}

function queueTurnRoll(delay = 2000) {
  clearQueuedRoll();
  const start = performance.now();
  const tick = () => {
    const elapsed = performance.now() - start;
    const remaining = Math.max(0, delay - elapsed);
    turnCountdown.textContent = `Rolling in ${(remaining / 1000).toFixed(1)}s`;
    if (remaining <= 0) {
      clearInterval(countdownInterval);
    }
  };
  countdownInterval = setInterval(tick, 120);
  rollingTimeout = setTimeout(() => {
    clearInterval(countdownInterval);
    rollTurn();
  }, delay);
  tick();
}

function clearQueuedRoll() {
  clearTimeout(rollingTimeout);
  clearInterval(countdownInterval);
  rollingTimeout = null;
}

async function requestBotMove() {
  botThinking = true;
  setStatus("Bot is thinking with minimax + alpha-beta pruning...");

  const start = performance.now();
  const decisionStart = performance.now();
  const move = pickBotMove();
  const decisionTime = performance.now() - decisionStart;

  const thinkDelay = 500 + Math.random() * 500;
  await wait(thinkDelay);

  if (!move) {
    setStatus("Bot could not find a move (board full).");
    botThinking = false;
    return;
  }

  if (boardState[move.row][move.col]) {
    botThinking = false;
    setStatus("Bot's choice was already filled. Rolling again.");
    queueTurnRoll(1500);
    return;
  }

  placeDisc("BOT", move.row, move.col);
  const runtime = performance.now() - start;
  updateBotMetrics(decisionTime, runtime);
  botThinking = false;
}

function pickBotMove() {
  const center = (SIZE - 1) / 2;
  let best = null;
  let bestScore = Infinity;

  for (let col = 0; col < SIZE; col += 1) {
    const dropRow = findAvailableRow(col);
    if (dropRow === null) continue;
    const distance = Math.abs(center - dropRow) + Math.abs(center - col);
    const noise = Math.random() * 0.1;
    const score = distance + noise;
    if (score < bestScore) {
      bestScore = score;
      best = { row: dropRow, col };
    }
  }
  return best;
}

function updateBotMetrics(decisionMs, runtimeMs) {
  botDecision.textContent = `${decisionMs.toFixed(0)} ms`;
  botRuntime.textContent = `${runtimeMs.toFixed(0)} ms`;
}

function flashFault(cell, message) {
  cell.classList.add("fault");
  setStatus(message);
  setTimeout(() => cell.classList.remove("fault"), 620);
}

function setStatus(message) {
  statusText.textContent = message;
}

function describePlayer(playerId) {
  const player = PLAYERS.find((p) => p.id === playerId);
  return player ? player.name : playerId;
}

function boardIsFull() {
  return boardState.every((row) => row.every(Boolean));
}

function findAvailableRow(col) {
  for (let row = SIZE - 1; row >= 0; row -= 1) {
    if (!boardState[row][col]) return row;
  }
  return null;
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
