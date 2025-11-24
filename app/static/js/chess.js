class ChessGame {
    constructor(options) {
        this.gameId = options.gameId;
        this.playerColor = options.playerColor;
        this.boardTheme = options.boardTheme || 'classic';
        this.isMultiplayer = options.isMultiplayer || false;
        this.currentStatus = options.initialStatus || 'active';

        this.canvas = document.getElementById('chessboard');
        this.ctx = this.canvas.getContext('2d');
        this.audio = new AudioManager();
        this.notification = NotificationManager;

        this.squareSize = this.canvas.width / 8;
        this.setThemeColors(this.boardTheme);

        this.state = {
            fen: '',
            legal_moves: [],
            moves_san: [],
            captured_pieces: { white: [], black: [] },
            white_score: 0,
            black_score: 0
        };

        this.squareMap = {};
        this.selectedSquare = null;
        this.availableMovesFromSelection = [];
        this.pendingLocalMove = null;
        this.showMoves = true;

        this.whiteTimeLeft = null;
        this.blackTimeLeft = null;
        this.whiteTimeSpent = 0;
        this.blackTimeSpent = 0;
        this.durationSeconds = 0;
        this.timerInterval = null;
        this.durationInterval = null;
        this.isUnlimited = false;
        this.currentTurnColor = 'white';

        this.piecesLayer = null;
        this.isSubmittingMove = false;
        this.resizeTimeout = null;

        this.initialize();
    }

    initialize() {
        this.setupPiecesLayer();
        this.resizeBoard();
        this.bindCanvasEvents();
        this.bindResizeEvents();
        this.displayStartTime();
        this.toggleBoardInteractivity();
        this.loadBoard();
    }

    bindResizeEvents() {
        window.addEventListener('resize', () => {
            clearTimeout(this.resizeTimeout);
            this.resizeTimeout = setTimeout(() => {
                this.resizeBoard();
                this.render();
            }, 150);
        });
    }

    resizeBoard() {
        const wrapper = this.canvas.parentElement;
        if (!wrapper) return;
        const maxSize = 640;
        const size = Math.min(maxSize, wrapper.clientWidth || maxSize);
        this.canvas.width = size;
        this.canvas.height = size;
        this.canvas.style.width = `${size}px`;
        this.canvas.style.height = `${size}px`;
        this.squareSize = size / 8;
        this.syncPiecesLayer();
    }

    setThemeColors(theme) {
        if (theme === 'green') {
            this.lightSquare = '#EEEED2';
            this.darkSquare = '#769656';
        } else if (theme === 'blackwhite') {
            this.lightSquare = '#FFFFFF';
            this.darkSquare = '#000000';
        } else {
            this.lightSquare = '#F0D9B5';
            this.darkSquare = '#B58863';
        }
    }

    setupPiecesLayer() {
        const wrapper = this.canvas.parentElement;
        if (wrapper && getComputedStyle(wrapper).position === 'static') {
            wrapper.style.position = 'relative';
        }

        let layer = document.getElementById('pieces-layer');
        if (!layer) {
            layer = document.createElement('div');
            layer.id = 'pieces-layer';
            layer.style.position = 'absolute';
            layer.style.pointerEvents = 'none';
            layer.style.top = '0';
            layer.style.left = '0';
            layer.style.width = `${this.canvas.width}px`;
            layer.style.height = `${this.canvas.height}px`;
            this.canvas.parentNode.insertBefore(layer, this.canvas.nextSibling);
        }
        this.piecesLayer = layer;
        this.syncPiecesLayer();
    }

    syncPiecesLayer() {
        if (!this.piecesLayer) return;
        const rect = this.canvas.getBoundingClientRect();
        const parentRect = this.canvas.parentElement.getBoundingClientRect();
        this.piecesLayer.style.left = `${rect.left - parentRect.left}px`;
        this.piecesLayer.style.top = `${rect.top - parentRect.top}px`;
        this.piecesLayer.style.width = `${this.canvas.width}px`;
        this.piecesLayer.style.height = `${this.canvas.height}px`;
    }

    bindCanvasEvents() {
        this.canvas.addEventListener('click', (event) => {
            if (!this.isGameActive() || this.isSubmittingMove) return;
            const rect = this.canvas.getBoundingClientRect();
            const x = event.clientX - rect.left;
            const y = event.clientY - rect.top;
            const col = Math.min(7, Math.max(0, Math.floor((x / this.canvas.width) * 8)));
            const row = Math.min(7, Math.max(0, Math.floor((y / this.canvas.height) * 8)));
            const square = this.coordsToSquare(col, row);
            this.handleSquareSelection(square);
        });
    }

    displayStartTime() {
        const slot = document.getElementById('gameStart');
        if (slot) {
            slot.textContent = new Date().toLocaleTimeString('bg-BG');
        }
    }

    loadBoard() {
        fetch(`/game/${this.gameId}/board`)
            .then((res) => res.json())
            .then((data) => this.applyServerPayload(data))
            .catch((err) => console.error('Board load failed', err));
    }

    applyServerPayload(data) {
        if (data.error) {
            this.showError(data.error);
            return;
        }

        this.state = {
            ...data,
            legal_moves: data.legal_moves || [],
            moves_san: data.moves_san || []
        };
        this.buildSquareMap();
        this.selectedSquare = null;
        this.availableMovesFromSelection = [];
        this.pendingLocalMove = null;
        this.currentTurnColor = data.fen.split(' ')[1] === 'w' ? 'white' : 'black';

        this.applyTimeTracking(data.time_tracking || {});
        this.updateCapturedPanels(data);
        this.updateMoveList(this.state.moves_san);
        this.updateGameStatus(data.status);
        this.updateRedoButton(data.redo_available);
        this.render();
        this.resetTimers();
    }

    buildSquareMap() {
        const map = {};
        const fenBoard = (this.state.fen || '').split(' ')[0];
        const rows = fenBoard.split('/');
        for (let rowIndex = 0; rowIndex < 8; rowIndex += 1) {
            const fenRow = rows[rowIndex] || '';
            let col = 0;
            for (const char of fenRow) {
                if (Number.isNaN(Number(char))) {
                    const square = this.coordsToSquare(col, rowIndex);
                    map[square] = char;
                    col += 1;
                } else {
                    col += parseInt(char, 10);
                }
            }
        }
        this.squareMap = map;
    }

    render() {
        if (!this.canvas) return;
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.drawSquares();
        this.drawHighlights();
        this.drawPieces();
    }

    drawSquares() {
        for (let row = 0; row < 8; row += 1) {
            for (let col = 0; col < 8; col += 1) {
                const isLight = (row + col) % 2 === 0;
                this.ctx.fillStyle = isLight ? this.lightSquare : this.darkSquare;
                this.ctx.fillRect(
                    col * this.squareSize,
                    row * this.squareSize,
                    this.squareSize,
                    this.squareSize
                );
            }
        }
    }

    drawHighlights() {
        if (!this.selectedSquare) return;
        const [selCol, selRow] = this.squareToCoords(this.selectedSquare);
        this.ctx.fillStyle = 'rgba(255, 193, 7, 0.45)';
        this.ctx.fillRect(selCol * this.squareSize, selRow * this.squareSize, this.squareSize, this.squareSize);

        if (!this.showMoves) return;
        this.ctx.fillStyle = 'rgba(76, 175, 80, 0.45)';
        this.availableMovesFromSelection.forEach((move) => {
            const target = move.substring(2, 4);
            const [col, row] = this.squareToCoords(target);
            this.ctx.beginPath();
            this.ctx.arc(
                col * this.squareSize + this.squareSize / 2,
                row * this.squareSize + this.squareSize / 2,
                this.squareSize / 6,
                0,
                Math.PI * 2
            );
            this.ctx.fill();
        });
    }

    drawPieces() {
        if (!this.piecesLayer) return;
        this.piecesLayer.innerHTML = '';
        Object.entries(this.squareMap).forEach(([square, piece]) => {
            const [col, row] = this.squareToCoords(square);
            const size = this.squareSize * 0.9;
            const offset = (this.squareSize - size) / 2;
            const isWhite = piece === piece.toUpperCase();
            const img = document.createElement('img');
            img.src = `/static/img/pieces/${isWhite ? 'w' : 'b'}${piece.toLowerCase()}.svg`;
            img.alt = piece;
            img.style.position = 'absolute';
            img.style.left = `${col * this.squareSize + offset}px`;
            img.style.top = `${row * this.squareSize + offset}px`;
            img.style.width = `${size}px`;
            img.style.height = `${size}px`;
            img.draggable = false;
            img.onerror = () => {
                img.remove();
                const fallback = document.createElement('span');
                fallback.textContent = this.getUnicodePiece(piece);
                fallback.style.position = 'absolute';
                fallback.style.left = `${col * this.squareSize}px`;
                fallback.style.top = `${row * this.squareSize}px`;
                fallback.style.width = `${this.squareSize}px`;
                fallback.style.height = `${this.squareSize}px`;
                fallback.style.fontSize = `${this.squareSize * 0.8}px`;
                fallback.style.lineHeight = `${this.squareSize}px`;
                fallback.style.textAlign = 'center';
                fallback.style.pointerEvents = 'none';
                fallback.style.color = isWhite ? '#fff' : '#000';
                fallback.style.textShadow = isWhite ? '1px 1px 3px #000' : '1px 1px 2px #fff';
                this.piecesLayer.appendChild(fallback);
            };
            this.piecesLayer.appendChild(img);
        });
    }

    handleSquareSelection(square) {
        if (!square) return;
        const movesFromSquare = (this.state.legal_moves || []).filter((move) => move.startsWith(square));

        if (!this.selectedSquare) {
            if (movesFromSquare.length === 0) return;
            this.selectedSquare = square;
            this.availableMovesFromSelection = movesFromSquare;
            this.render();
            return;
        }

        if (square === this.selectedSquare) {
            this.selectedSquare = null;
            this.availableMovesFromSelection = [];
            this.render();
            return;
        }

        const move = this.preparePromotionIfNeeded(this.selectedSquare, square);
        if (!this.state.legal_moves.includes(move)) {
            this.notification?.warning('Ходът не е разрешен.');
            this.selectedSquare = null;
            this.availableMovesFromSelection = [];
            this.render();
            return;
        }

        this.selectedSquare = null;
        this.availableMovesFromSelection = [];
        this.makeMove(move);
    }

    preparePromotionIfNeeded(from, to) {
        const piece = this.squareMap[from];
        if (!piece) return from + to;
        const rank = parseInt(to[1], 10);
        const isWhitePawn = piece === 'P' && rank === 8;
        const isBlackPawn = piece === 'p' && rank === 1;
        if (isWhitePawn || isBlackPawn) {
            return `${from}${to}q`;
        }
        return from + to;
    }

    makeMove(moveUci) {
        if (this.isSubmittingMove || !this.isGameActive()) return;
        const applied = this.applyLocalMove(moveUci);
        if (!applied) {
            this.notification?.error('Ходът не можа да бъде визуализиран.');
            return;
        }

        this.isSubmittingMove = true;
        this.showThinkingIndicator(true, 'Изчакваме потвърждение...');

        const payload = {
            move: moveUci,
            time_snapshot: this.buildTimeSnapshot()
        };

        fetch(`/game/${this.gameId}/move`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
            .then((res) => res.json())
            .then((data) => {
                if (data.error) {
                    this.showError(data.error);
                    this.loadBoard();
                    return;
                }

                const delay = (!this.isMultiplayer && data.ai_delay_ms) ? data.ai_delay_ms : 0;
                const finalize = () => {
                    this.applyServerPayload(data);
                    this.playMoveAudio(data.moves_san);
                };

                if (delay > 0) {
                    this.showThinkingIndicator(true, 'Ботът мисли...');
                    setTimeout(finalize, delay);
                } else {
                    finalize();
                }
            })
            .catch((err) => {
                this.showError(err.message || 'Грешка при изпращане на хода.');
                this.loadBoard();
            })
            .finally(() => {
                this.isSubmittingMove = false;
                this.showThinkingIndicator(false);
            });
    }

    applyLocalMove(moveUci) {
        const from = moveUci.substring(0, 2);
        const to = moveUci.substring(2, 4);
        const promotion = moveUci.length === 5 ? moveUci[4] : null;
        const piece = this.squareMap[from];
        if (!piece) return false;

        const isWhite = piece === piece.toUpperCase();
        const isPawn = piece.toLowerCase() === 'p';
        const isKing = piece.toLowerCase() === 'k';
        const fromFile = from.charCodeAt(0);
        const toFile = to.charCodeAt(0);
        const fromRank = parseInt(from[1], 10);
        const toRank = parseInt(to[1], 10);

        let capturedPiece = this.squareMap[to] || null;

        // En passant
        if (isPawn && !capturedPiece && fromFile !== toFile) {
            const direction = isWhite ? 1 : -1;
            const capturedSquare = `${to[0]}${toRank - direction}`;
            capturedPiece = this.squareMap[capturedSquare] || null;
            if (capturedPiece) {
                delete this.squareMap[capturedSquare];
            }
        }

        // Castling
        if (isKing && Math.abs(toFile - fromFile) === 2) {
            const rookFrom = toFile > fromFile ? 'h' : 'a';
            const rookTo = toFile > fromFile ? 'f' : 'd';
            const rookSquareFrom = `${rookFrom}${fromRank}`;
            const rookSquareTo = `${rookTo}${fromRank}`;
            if (this.squareMap[rookSquareFrom]) {
                this.squareMap[rookSquareTo] = this.squareMap[rookSquareFrom];
                delete this.squareMap[rookSquareFrom];
            }
        }

        delete this.squareMap[from];
        let updatedPiece = piece;
        if (promotion) {
            updatedPiece = isWhite ? promotion.toUpperCase() : promotion.toLowerCase();
        }
        this.squareMap[to] = updatedPiece;
        this.pendingLocalMove = { from, to, capturedPiece };
        this.currentTurnColor = this.currentTurnColor === 'white' ? 'black' : 'white';
        this.render();
        this.updateMoveIndicator();
        return true;
    }

    playMoveAudio(movesSan = []) {
        if (!movesSan.length) return;
        const lastMove = movesSan[movesSan.length - 1] || '';
        if (lastMove.includes('x')) {
            this.audio.captureSound();
        } else {
            this.audio.moveSound();
        }
    }

    requestUndo() {
        if (!this.isGameActive() || this.isMultiplayer) return;
        fetch(`/game/${this.gameId}/undo`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ time_snapshot: this.buildTimeSnapshot() })
        })
            .then((res) => res.json())
            .then((data) => this.applyServerPayload(data))
            .catch((err) => this.showError(err.message || 'Неуспешно връщане назад.'));
    }

    requestRedo() {
        if (!this.isGameActive() || this.isMultiplayer) return;
        fetch(`/game/${this.gameId}/redo`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ time_snapshot: this.buildTimeSnapshot() })
        })
            .then((res) => res.json())
            .then((data) => this.applyServerPayload(data))
            .catch((err) => this.showError(err.message || 'Неуспешно връщане напред.'));
    }

    resign() {
        if (!confirm('Сигурни ли сте, че искате да се предадете?')) {
            return;
        }
        fetch(`/game/${this.gameId}/resign`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ time_snapshot: this.buildTimeSnapshot() })
        })
            .then((res) => res.json())
            .then((data) => {
                this.currentStatus = data.game_status;
                this.notification?.info('Играта е отбелязана като загубена.');
                this.loadBoard();
            })
            .catch((err) => this.showError(err.message || 'Грешка при предаване.'));
    }

    resumeGame() {
        return fetch(`/game/${this.gameId}/resume`, { method: 'POST' })
            .then((res) => res.json())
            .then((data) => {
                this.applyServerPayload(data);
                this.notification?.success('Играта е възобновена.');
            })
            .catch((err) => this.showError(err.message || 'Грешка при възобновяване.'));
    }

    leaveGame() {
        return fetch(`/game/${this.gameId}/leave`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ time_snapshot: this.buildTimeSnapshot() })
        })
            .then((res) => res.json())
            .then((data) => {
                this.currentStatus = data.game_status;
                this.toggleBoardInteractivity();
            });
    }

    startNewGame() {
        window.location.href = '/game/new';
    }

    updateMoveList(movesSan) {
        const list = document.getElementById('moveList');
        if (!list) return;
        list.innerHTML = '';
        for (let i = 0; i < movesSan.length; i += 2) {
            const row = document.createElement('div');
            row.className = 'move-item';
            const moveNumber = (i / 2) + 1;
            const white = movesSan[i] || '';
            const black = movesSan[i + 1] || '';
            row.textContent = `${moveNumber}. ${white} ${black}`.trim();
            list.appendChild(row);
        }
    }

    updateCapturedPanels(data) {
        const yourCaptured = document.getElementById('yourCaptured');
        const opponentCaptured = document.getElementById('opponentCaptured');
        const scoreAdvantage = document.getElementById('scoreAdvantage');
        const playerIsWhite = this.playerColor === 'white';
        const yourPieces = playerIsWhite ? data.captured_pieces.white : data.captured_pieces.black;
        const opponentPieces = playerIsWhite ? data.captured_pieces.black : data.captured_pieces.white;

        if (yourCaptured) yourCaptured.textContent = this.formatCapturedPieces(yourPieces);
        if (opponentCaptured) opponentCaptured.textContent = this.formatCapturedPieces(opponentPieces);
        if (scoreAdvantage) {
            const diff = (data.white_score || 0) - (data.black_score || 0);
            const perspective = playerIsWhite ? diff : -diff;
            scoreAdvantage.textContent = perspective > 0 ? `+${perspective}` : perspective;
        }
    }

    updateGameStatus(status) {
        this.currentStatus = status;
        const labels = {
            active: 'Статус: активна',
            won: 'Статус: победа',
            lost: 'Статус: загуба',
            draw: 'Статус: реми',
            finished: 'Статус: запазена'
        };
        const slot = document.getElementById('gameStatus');
        if (slot) slot.textContent = labels[status] || 'Статус: активна';
        if (status !== 'active') {
            this.stopTimers();
        }
        this.updateMoveIndicator();
        this.toggleBoardInteractivity();
        this.updateResumeButton();
    }

    updateResumeButton() {
        const btn = document.getElementById('resumeBtn');
        if (!btn) return;
        if (this.currentStatus === 'finished') {
            btn.classList.remove('hidden');
            btn.disabled = false;
        } else {
            btn.classList.add('hidden');
            btn.disabled = true;
        }
    }

    updateMoveIndicator() {
        const indicator = document.getElementById('moveIndicator');
        if (!indicator) return;
        if (this.currentStatus !== 'active') {
            const endTexts = {
                won: 'Браво! Спечели играта.',
                lost: 'Играта е загубена.',
                draw: 'Играта приключи с реми.',
                finished: 'Играта е запазена и може да се възобнови.'
            };
            indicator.textContent = endTexts[this.currentStatus] || 'Играта е приключила.';
            indicator.classList.remove('thinking');
            return;
        }
        const myTurn = this.currentTurnColor === this.playerColor;
        indicator.textContent = myTurn ? 'Твой ред е.' : 'Изчаквай хода на противника.';
        indicator.classList.toggle('thinking', false);
    }

    showThinkingIndicator(show, text) {
        const indicator = document.getElementById('moveIndicator');
        if (!indicator) return;
        if (show) {
            indicator.textContent = text || 'Изчакваме...';
            indicator.classList.add('thinking');
        } else {
            indicator.classList.remove('thinking');
            this.updateMoveIndicator();
        }
    }

    toggleMoveHints(show) {
        this.showMoves = show;
        this.render();
    }

    toggleSound(enabled) {
        this.audio.enabled = enabled;
        localStorage.setItem('soundEnabled', enabled);
    }

    applyTimeTracking(snapshot) {
        if (!snapshot) return;
        if (snapshot.white_left !== undefined) this.whiteTimeLeft = snapshot.white_left;
        if (snapshot.black_left !== undefined) this.blackTimeLeft = snapshot.black_left;
        if (snapshot.white_spent !== undefined) this.whiteTimeSpent = snapshot.white_spent;
        if (snapshot.black_spent !== undefined) this.blackTimeSpent = snapshot.black_spent;
        if (snapshot.duration !== undefined) this.durationSeconds = snapshot.duration;
        this.isUnlimited = (this.whiteTimeLeft === null && this.blackTimeLeft === null);
    }

    resetTimers() {
        this.stopTimers(false);
        this.updateTimerDisplay();

        if (!this.isGameActive()) {
            this.updateDurationDisplay();
            return;
        }

        this.durationInterval = setInterval(() => {
            this.durationSeconds += 1;
            this.updateDurationDisplay();
        }, 1000);

        if (this.isUnlimited) return;

        this.timerInterval = setInterval(() => {
            if (this.currentTurnColor === 'white') {
                this.whiteTimeLeft = Math.max(0, (this.whiteTimeLeft || 0) - 1);
                this.whiteTimeSpent += 1;
                if (this.whiteTimeLeft === 0) {
                    this.handleTimeExpired();
                }
            } else {
                this.blackTimeLeft = Math.max(0, (this.blackTimeLeft || 0) - 1);
                this.blackTimeSpent += 1;
                if (this.blackTimeLeft === 0) {
                    this.handleOpponentTimeExpired();
                }
            }
            this.updateTimerDisplay();
        }, 1000);
    }

    stopTimers(resetDuration = true) {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
        if (this.durationInterval) {
            clearInterval(this.durationInterval);
            this.durationInterval = null;
        }
        if (resetDuration) {
            this.updateTimerDisplay();
        }
    }

    updateTimerDisplay() {
        const playerTimer = document.getElementById('playerTimer');
        const opponentTimer = document.getElementById('opponentTimer');
        const playerTotal = document.getElementById('playerTotalTime');
        const opponentTotal = document.getElementById('opponentTotalTime');
        const playerIsWhite = this.playerColor === 'white';

        const playerLeft = playerIsWhite ? this.whiteTimeLeft : this.blackTimeLeft;
        const opponentLeft = playerIsWhite ? this.blackTimeLeft : this.whiteTimeLeft;
        const playerSpent = playerIsWhite ? this.whiteTimeSpent : this.blackTimeSpent;
        const opponentSpent = playerIsWhite ? this.blackTimeSpent : this.whiteTimeSpent;

        if (playerTimer) playerTimer.textContent = this.formatClock(playerLeft);
        if (opponentTimer) opponentTimer.textContent = this.formatClock(opponentLeft);
        if (playerTotal) playerTotal.textContent = `Общо време: ${this.formatClock(playerSpent, true)}`;
        if (opponentTotal) opponentTotal.textContent = `Общо време: ${this.formatClock(opponentSpent, true)}`;
        this.updateDurationDisplay();
    }

    updateDurationDisplay() {
        const slot = document.getElementById('gameDuration');
        if (slot) slot.textContent = this.formatClock(this.durationSeconds, true);
    }

    handleTimeExpired() {
        this.notification?.error('Времето ти изтече.');
        this.audio.timeWarningSound();
    }

    handleOpponentTimeExpired() {
        this.notification?.info('Противникът мисли твърде дълго.');
    }

    buildTimeSnapshot() {
        const playerIsWhite = this.playerColor === 'white';
        return {
            player_spent: playerIsWhite ? this.whiteTimeSpent : this.blackTimeSpent,
            opponent_spent: playerIsWhite ? this.blackTimeSpent : this.whiteTimeSpent,
            player_left: this.isUnlimited ? null : (playerIsWhite ? this.whiteTimeLeft : this.blackTimeLeft),
            opponent_left: this.isUnlimited ? null : (playerIsWhite ? this.blackTimeLeft : this.whiteTimeLeft),
            duration: this.durationSeconds
        };
    }

    updateRedoButton(isAvailable) {
        const redoBtn = document.getElementById('redoBtn');
        if (redoBtn) redoBtn.disabled = !isAvailable;
    }

    coordsToSquare(col, row) {
        const file = String.fromCharCode(97 + col);
        const rank = 8 - row;
        return `${file}${rank}`;
    }

    squareToCoords(square) {
        if (!square) return [0, 0];
        const file = square.charCodeAt(0) - 97;
        const rank = parseInt(square[1], 10);
        return [file, 8 - rank];
    }

    getUnicodePiece(piece) {
        const map = {
            K: '?', Q: '?', R: '?', B: '?', N: '?', P: '?',
            k: '?', q: '?', r: '?', b: '?', n: '?', p: '?'
        };
        return map[piece] || '?';
    }

    formatCapturedPieces(pieces = []) {
        if (!pieces.length) return '—';
        const counts = {};
        pieces.forEach((p) => {
            counts[p] = (counts[p] || 0) + 1;
        });
        return Object.entries(counts)
            .map(([piece, count]) => `${this.getUnicodePiece(piece)}${count > 1 ? `x${count}` : ''}`)
            .join(' ');
    }

    formatClock(value, isElapsed = false) {
        if (value === null || value === undefined) {
            return isElapsed ? '00:00' : '?';
        }
        const total = Math.max(0, parseInt(value, 10));
        const hours = Math.floor(total / 3600);
        const minutes = Math.floor((total % 3600) / 60);
        const seconds = total % 60;
        if (hours) {
            return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }
        return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }

    showError(message) {
        if (this.notification) this.notification.error(message);
        console.error(message);
    }

    isGameActive() {
        return this.currentStatus === 'active';
    }

    toggleBoardInteractivity() {
        if (!this.canvas) return;
        const isActive = this.isGameActive();
        this.canvas.style.pointerEvents = isActive ? 'auto' : 'none';
        this.canvas.classList.toggle('board-disabled', !isActive);
    }
}

window.ChessGame = ChessGame;

